import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from difflib import SequenceMatcher
from typing import Dict, List

from sqlalchemy.orm import Session

from adapters.ai.ninerouter import NineRouterAI, TranslationOutputError
from infrastructure.db.models import Account, TranslationBenchmarkRun
from infrastructure.db.session import SessionLocal


REFUSAL_RE = re.compile(
    r"\b(?:i(?:'m| am)? sorry|i can(?:not|'t)|unable to|copyright|"
    r"policy restriction|cannot provide)\b",
    re.IGNORECASE,
)
PREFIX_RE = re.compile(
    r"^\s*(?:translation|translated text|here(?:'s| is) the translation)\s*:",
    re.IGNORECASE,
)
NUMBER_RE = re.compile(r"(?:[$€£₴]\s*)?\d[\d.,:/%-]*")


STANDARD_CASES = [
    {
        "id": "dialogue_and_relationships",
        "title": "The call that changed the family",
        "content": (
            "Emily stared at her brother Daniel across the kitchen table. "
            "\"You promised Mom you would return before Friday,\" she said.\n\n"
            "Daniel checked the message again. Their aunt Rose had transferred $25,000 "
            "on March 14, but nobody knew why. He lowered his voice and told Emily that "
            "the answer was hidden in a letter their father wrote in 1998."
        ),
    },
    {
        "id": "dates_numbers_and_places",
        "title": "A delayed train exposed the truth",
        "content": (
            "Train 847 left New York at 7:35 p.m. with 216 passengers. By the time it "
            "reached Philadelphia, the temperature had fallen to -4°C.\n\n"
            "Maria opened locker 19 and found three receipts: $84.50, $1,200, and "
            "$9,999. The oldest receipt was dated January 3, 2024."
        ),
    },
    {
        "id": "long_paragraph_continuity",
        "title": "The witness remembered one final detail",
        "content": (
            "For eleven years, Thomas repeated the same version of the accident: the road "
            "was empty, the rain was heavy, and he never saw the blue car approach from "
            "the east. During the hearing, however, the attorney placed a faded photograph "
            "on the desk and asked why the clock above the pharmacy showed 6:42 when Thomas "
            "had always claimed the collision happened after 8:00. Thomas looked at his "
            "daughter, then at the photograph, and admitted that another person had been "
            "in the passenger seat.\n\n"
            "The admission did not end the hearing. It created a new question: why had every "
            "official report omitted that passenger's name?"
        ),
    },
]


def _paragraphs(text: str) -> List[str]:
    return [part.strip() for part in re.split(r"\n{2,}", text or "") if part.strip()]


def _ratio_score(value: float, ideal_min: float, ideal_max: float) -> float:
    if ideal_min <= value <= ideal_max:
        return 1.0
    if value < ideal_min:
        return max(0.0, value / ideal_min)
    return max(0.0, ideal_max / value)


def score_translation(source: str, output: str) -> Dict:
    source = (source or "").strip()
    output = (output or "").strip()
    source_paragraphs = _paragraphs(source)
    output_paragraphs = _paragraphs(output)
    refusal = bool(REFUSAL_RE.search(output))
    prefix = bool(PREFIX_RE.search(output))

    source_numbers = set(NUMBER_RE.findall(source))
    output_numbers = set(NUMBER_RE.findall(output))
    number_score = (
        len(source_numbers & output_numbers) / len(source_numbers)
        if source_numbers
        else 1.0
    )
    paragraph_score = (
        min(len(source_paragraphs), len(output_paragraphs))
        / max(len(source_paragraphs), len(output_paragraphs), 1)
    )
    length_ratio = len(output) / max(len(source), 1)
    length_score = _ratio_score(length_ratio, 0.55, 1.65)

    source_leakage = 0.0
    for paragraph in source_paragraphs:
        if len(paragraph) < 40:
            continue
        for output_paragraph in output_paragraphs:
            source_leakage = max(
                source_leakage,
                SequenceMatcher(
                    None,
                    paragraph.lower(),
                    output_paragraph.lower(),
                ).ratio(),
            )

    score = round(
        100
        * (
            0.25 * (1.0 if output else 0.0)
            + 0.20 * paragraph_score
            + 0.20 * number_score
            + 0.15 * length_score
            + 0.10 * (0.0 if refusal else 1.0)
            + 0.05 * (0.0 if prefix else 1.0)
            + 0.05 * (0.0 if source_leakage >= 0.92 else 1.0)
        ),
        1,
    )

    valid = bool(
        output
        and not refusal
        and length_ratio >= 0.35
        and paragraph_score >= 0.5
        and source_leakage < 0.98
    )
    if not valid:
        score = min(score, 49.0)

    warnings = []
    if refusal:
        warnings.append("Model returned refusal or policy text")
    if prefix:
        warnings.append("Output contains a translation prefix")
    if paragraph_score < 1:
        warnings.append("Paragraph structure changed")
    if number_score < 1:
        warnings.append("One or more numbers, dates, or currency values changed")
    if length_ratio < 0.55:
        warnings.append("Output is unusually short")
    elif length_ratio > 1.65:
        warnings.append("Output is unusually long")
    if source_leakage >= 0.92:
        warnings.append("Output may contain untranslated source text")

    return {
        "score": score,
        "valid": valid,
        "paragraph_score": round(paragraph_score, 3),
        "number_score": round(number_score, 3),
        "length_ratio": round(length_ratio, 3),
        "source_leakage": round(source_leakage, 3),
        "warnings": warnings,
    }


class InstrumentedNineRouterAI(NineRouterAI):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.request_count = 0
        self.input_tokens = 0
        self.output_tokens = 0

    def _post_json(self, url: str, headers: dict, data: dict):
        self.request_count += 1
        response = super()._post_json(url, headers, data)
        try:
            usage = (response.json() or {}).get("usage") or {}
            self.input_tokens += int(usage.get("prompt_tokens") or 0)
            self.output_tokens += int(usage.get("completion_tokens") or 0)
        except Exception:
            pass
        return response


def _cases_from_config(config: Dict) -> List[Dict]:
    if config.get("suite", "standard") == "custom":
        return [{
            "id": "custom",
            "title": (config.get("custom_title") or "Untitled article").strip(),
            "content": (config.get("custom_content") or "").strip(),
        }]
    return list(STANDARD_CASES)


def _run_candidate(
    account: Account,
    target_language: str,
    cases: List[Dict],
    blind_label: str,
) -> Dict:
    config = dict(account.config or {})
    client = InstrumentedNineRouterAI(
        api_key=config.get("api_key"),
        text_model=config.get("text_model"),
        image_model=config.get("image_model"),
        base_url=config.get("base_url", "http://localhost:20128/v1"),
        request_max_attempts=1,
        translation_chunk_size=config.get("translation_chunk_size", 5000),
        translation_context_chars=config.get("translation_context_chars", 400),
    )
    started = time.perf_counter()
    case_results = []

    for case in cases:
        case_started = time.perf_counter()
        try:
            article = client.translate_article_fields(
                case["title"],
                case["content"],
                language=target_language,
            )
            title_metrics = score_translation(case["title"], article["title"])
            content_metrics = score_translation(case["content"], article["content"])
            case_results.append({
                "case_id": case["id"],
                "source_title": case["title"],
                "source_content": case["content"],
                "translated_title": article["title"],
                "translated_content": article["content"],
                "score": round(
                    0.15 * title_metrics["score"] + 0.85 * content_metrics["score"],
                    1,
                ),
                "valid": title_metrics["valid"] and content_metrics["valid"],
                "title_metrics": title_metrics,
                "content_metrics": content_metrics,
                "latency_ms": round((time.perf_counter() - case_started) * 1000),
                "error": None,
            })
        except TranslationOutputError as exc:
            content_metrics = score_translation(case["content"], exc.output)
            case_results.append({
                "case_id": case["id"],
                "source_title": case["title"],
                "source_content": case["content"],
                "translated_title": "",
                "translated_content": exc.output,
                "score": min(content_metrics["score"], 49),
                "valid": False,
                "title_metrics": None,
                "content_metrics": content_metrics,
                "latency_ms": round((time.perf_counter() - case_started) * 1000),
                "error": str(exc),
            })
        except Exception as exc:
            case_results.append({
                "case_id": case["id"],
                "source_title": case["title"],
                "source_content": case["content"],
                "translated_title": "",
                "translated_content": "",
                "score": 0,
                "valid": False,
                "title_metrics": None,
                "content_metrics": None,
                "latency_ms": round((time.perf_counter() - case_started) * 1000),
                "error": str(exc),
            })

    valid_count = sum(1 for case in case_results if case["valid"])
    return {
        "account_id": account.id,
        "account_name": account.name,
        "model": config.get("text_model") or "unknown",
        "blind_label": blind_label,
        "average_score": round(
            sum(case["score"] for case in case_results) / max(len(case_results), 1),
            1,
        ),
        "valid_rate": round(valid_count / max(len(case_results), 1), 3),
        "latency_ms": round((time.perf_counter() - started) * 1000),
        "request_count": client.request_count,
        "input_tokens": client.input_tokens,
        "output_tokens": client.output_tokens,
        "cases": case_results,
    }


class TranslationBenchmarkService:
    def __init__(self, db: Session):
        self.db = db

    def list_runs(self, limit: int = 20):
        return (
            self.db.query(TranslationBenchmarkRun)
            .order_by(TranslationBenchmarkRun.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_run(self, run_id: str):
        return (
            self.db.query(TranslationBenchmarkRun)
            .filter(TranslationBenchmarkRun.id == run_id)
            .first()
        )

    def create_run(self, payload):
        accounts = (
            self.db.query(Account)
            .filter(Account.id.in_(payload.account_ids), Account.type == "ai")
            .all()
        )
        if len(accounts) != len(set(payload.account_ids)):
            raise ValueError("One or more selected AI accounts were not found")
        if payload.suite == "custom" and not (payload.custom_content or "").strip():
            raise ValueError("Custom content is required")

        run = TranslationBenchmarkRun(
            status="queued",
            target_language=payload.target_language,
            suite=payload.suite,
            selected_account_ids=list(payload.account_ids),
            request_config={
                "suite": payload.suite,
                "custom_title": payload.custom_title,
                "custom_content": payload.custom_content,
            },
            results=[],
            manual_ratings={},
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def save_rating(
        self,
        run_id: str,
        account_id: str,
        score: int,
        notes: str = "",
    ):
        run = self.get_run(run_id)
        if not run:
            return None
        if account_id not in set(run.selected_account_ids or []):
            raise ValueError("Candidate does not belong to this benchmark run")
        ratings = dict(run.manual_ratings or {})
        ratings[account_id] = {"score": score, "notes": (notes or "").strip()}
        run.manual_ratings = ratings
        self.db.commit()
        self.db.refresh(run)
        return run


def execute_benchmark_run(run_id: str):
    with SessionLocal() as db:
        run = db.query(TranslationBenchmarkRun).filter(
            TranslationBenchmarkRun.id == run_id
        ).first()
        if not run:
            return
        run.status = "running"
        run.started_at = datetime.utcnow()
        run.current_step = "Preparing benchmark cases"
        run.progress = 5
        db.commit()

        accounts = (
            db.query(Account)
            .filter(Account.id.in_(run.selected_account_ids), Account.type == "ai")
            .all()
        )
        account_order = {
            account_id: index
            for index, account_id in enumerate(run.selected_account_ids)
        }
        accounts.sort(key=lambda account: account_order.get(account.id, 999))
        cases = _cases_from_config(run.request_config or {})
        target_language = run.target_language

    try:
        results = []
        total = max(len(accounts), 1)
        with ThreadPoolExecutor(max_workers=min(len(accounts), 4) or 1) as executor:
            futures = {
                executor.submit(
                    _run_candidate,
                    account,
                    target_language,
                    cases,
                    f"Candidate {chr(65 + index)}",
                ): account
                for index, account in enumerate(accounts)
            }
            for completed, future in enumerate(as_completed(futures), start=1):
                results.append(future.result())
                with SessionLocal() as update_db:
                    run = update_db.query(TranslationBenchmarkRun).filter(
                        TranslationBenchmarkRun.id == run_id
                    ).first()
                    if run:
                        run.results = list(results)
                        run.progress = min(95, round(completed / total * 90) + 5)
                        run.current_step = (
                            f"Completed {completed}/{total} candidates"
                        )
                        update_db.commit()

        results.sort(key=lambda item: (-item["average_score"], item["latency_ms"]))
        with SessionLocal() as db:
            run = db.query(TranslationBenchmarkRun).filter(
                TranslationBenchmarkRun.id == run_id
            ).first()
            if run:
                run.results = results
                run.status = "success"
                run.progress = 100
                run.current_step = "Completed"
                run.completed_at = datetime.utcnow()
                db.commit()
    except Exception as exc:
        with SessionLocal() as db:
            run = db.query(TranslationBenchmarkRun).filter(
                TranslationBenchmarkRun.id == run_id
            ).first()
            if run:
                run.status = "failed"
                run.error = str(exc)
                run.current_step = "Failed"
                run.completed_at = datetime.utcnow()
                db.commit()
