import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from app.db import models
from app.db.session import SessionLocal
from app.services.ai_client_factory import create_ai_client
from app.services.error_sanitizer import sanitize_error
from app.services.workflow_job_service import WorkflowJobService


class ArticleEnrichmentService:
    _executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="article-enrichment")

    @classmethod
    def enqueue(cls, article_id, pipeline_id=None, parent_job_id=None, ai_account_id=None, step="summary"):
        with SessionLocal() as db:
            article = db.query(models.Article).filter(models.Article.id == article_id).first()
            if not article:
                return None
            enrichment = db.query(models.ArticleEnrichment).filter(models.ArticleEnrichment.article_id == article_id).first()
            if not enrichment:
                enrichment = models.ArticleEnrichment(article_id=article_id)
                db.add(enrichment)
                db.commit()
            if step == "dna" and (
                enrichment.summary_status != "completed"
                or enrichment.analysis_status != "completed"
            ):
                raise ValueError("Summary and Story Analysis must be completed before Creative DNA")
            status = getattr(enrichment, f"{step}_status")
            if status == "completed" or status == "processing":
                return None
            job = WorkflowJobService(db).create(
                pipeline_id, f"article_enrichment_{step}", parent_job_id=parent_job_id, input_text=article.source_url
            )
            setattr(enrichment, f"{step}_status", "queued")
            enrichment.ai_account_id = ai_account_id
            db.commit()
            runner = {"summary": cls._run_summary, "analysis": cls._run_analysis, "dna": cls._run_dna}[step]
            cls._executor.submit(runner, job.id, article_id, pipeline_id, ai_account_id)
            return job

    @classmethod
    def _run_summary(cls, job_id, article_id, pipeline_id, ai_account_id):
        cls._run_step(job_id, article_id, pipeline_id, ai_account_id, "summary", cls._summary_prompt)

    @classmethod
    def _run_analysis(cls, job_id, article_id, pipeline_id, ai_account_id):
        cls._run_step(job_id, article_id, pipeline_id, ai_account_id, "analysis", cls._analysis_prompt)

    @classmethod
    def _run_dna(cls, job_id, article_id, pipeline_id, ai_account_id):
        cls._run_step(job_id, article_id, pipeline_id, ai_account_id, "dna", cls._dna_prompt)

    @classmethod
    def _run_step(cls, job_id, article_id, pipeline_id, ai_account_id, step, prompt_builder):
        with SessionLocal() as db:
            jobs = WorkflowJobService(db)
            article = db.query(models.Article).filter(models.Article.id == article_id).first()
            account = db.query(models.Account).filter(models.Account.id == ai_account_id, models.Account.type == "ai").first()
            enrichment = db.query(models.ArticleEnrichment).filter(models.ArticleEnrichment.article_id == article_id).first()
            if not article or not account or not enrichment:
                jobs.fail(job_id, "Enrichment article or AI account is unavailable")
                return
            status_field = f"{step}_status"
            error_field = f"{step}_error"
            setattr(enrichment, status_field, "processing")
            enrichment.ai_account_id = account.id
            db.commit()
            jobs.progress(job_id, step, 10, f"Generating {step}")
            try:
                result = cls._parse_json(create_ai_client(account).chat(
                    [{"role": "system", "content": prompt_builder("system")},
                     {"role": "user", "content": prompt_builder("user", article, enrichment)}],
                    priority="background", temperature=0.2,
                ).get("content"))
                if step == "summary":
                    enrichment.summary = result.get("summary", "")
                elif step == "analysis":
                    for key in ("plot_beats", "characters", "setting", "conflict", "emotional_arc"):
                        setattr(enrichment, key, result.get(key))
                else:
                    enrichment.creative_dna = result
                setattr(enrichment, status_field, "completed")
                setattr(enrichment, error_field, None)
                enrichment.updated_at = datetime.utcnow()
                db.commit()
                jobs.complete(job_id, {"article_id": article_id, "step": step})
                cls._enqueue_next(db, article, pipeline_id, job_id, ai_account_id, step)
            except Exception as exc:
                setattr(enrichment, status_field, "failed")
                setattr(enrichment, error_field, sanitize_error(str(exc))[:500])
                enrichment.updated_at = datetime.utcnow()
                db.commit()
                jobs.fail(job_id, exc)

    @classmethod
    def _enqueue_next(cls, db, article, pipeline_id, parent_job_id, ai_account_id, step):
        next_step = {"summary": "analysis", "analysis": "dna"}.get(step)
        if not next_step:
            return
        jobs = WorkflowJobService(db)
        job = jobs.create(pipeline_id, f"article_enrichment_{next_step}", parent_job_id=parent_job_id, input_text=article.source_url)
        runner = cls._run_analysis if next_step == "analysis" else cls._run_dna
        cls._executor.submit(runner, job.id, article.id, pipeline_id, ai_account_id)

    @staticmethod
    def _parse_json(value):
        text = (value or "").strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        result = json.loads(text)
        if not isinstance(result, dict):
            raise ValueError("Enrichment response must be a JSON object")
        return result

    @staticmethod
    def _summary_prompt(kind, article=None, enrichment=None):
        if kind == "system":
            return "Summarize the source article in neutral, concise prose. Return JSON only with key summary. Do not invent facts."
        return f"Title: {article.source_title or article.original_title}\n\nArticle:\n{article.source_content}"

    @staticmethod
    def _analysis_prompt(kind, article=None, enrichment=None):
        if kind == "system":
            return "Analyze narrative structure. Return JSON only with plot_beats array, characters array, setting object, conflict object, and emotional_arc array. Do not rewrite the article."
        return f"Title: {article.source_title or article.original_title}\n\nArticle:\n{article.source_content}"

    @staticmethod
    def _dna_prompt(kind, article=None, enrichment=None):
        if kind == "system":
            return "Create abstract Creative DNA for future original fiction. Return JSON only with themes, emotional_core, generalized_conflict, twist_style, and novelty_guidance. Remove names, exact places, exact dates, and specific event sequences."
        return json.dumps({"summary": enrichment.summary, "analysis": {"plot_beats": enrichment.plot_beats, "characters": enrichment.characters, "setting": enrichment.setting, "conflict": enrichment.conflict, "emotional_arc": enrichment.emotional_arc}}, ensure_ascii=False)
