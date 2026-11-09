"""Run fixed translation requests sequentially and retain timing metadata only."""

import time
from datetime import datetime

import requests

from app.db import models
from app.db.session import SessionLocal
from app.domain.model_benchmark_sample import build_messages
from app.services.ai_client_factory import create_ai_client


def _safe_error(exc):
    if isinstance(exc, requests.Timeout):
        return "Timed out"
    if isinstance(exc, requests.HTTPError):
        code = exc.response.status_code if exc.response is not None else None
        return f"API returned HTTP {code}" if code else "API request failed"
    if isinstance(exc, ValueError) and "empty" in str(exc).lower():
        return "API returned empty text"
    return "API request failed"


def _lock_job(db, job_id, statuses=('queued', 'running')):
    # Acquire the database write lock before reading mutable job state. A
    # cancellation that already committed must win over a stale worker session.
    matched = db.query(models.Job).filter(models.Job.id == job_id,
        models.Job.status.in_(statuses)).update({'status': models.Job.status}, synchronize_session=False)
    if not matched:
        db.rollback()
        return None
    job = db.get(models.Job, job_id)
    db.refresh(job)
    return job


class ModelBenchmarkService:
    @staticmethod
    def execute(job_id: str) -> None:
        with SessionLocal() as db:
            job = _lock_job(db, job_id)
            if not job:
                return
            outputs = dict(job.outputs or {})
            account = db.get(models.Account, outputs.get("account_id"))
            if not account or account.type != "ai":
                job.status = "failed"
                job.current_step = "AI account unavailable"
                job.outputs = {**outputs, "results": [
                    {**row, "status": "error", "error": "AI account unavailable"} for row in outputs.get("results", [])
                ]}
                job.end_time = datetime.utcnow()
                db.commit()
                return
            db.commit()

            messages = build_messages()
            model_ids = outputs["model_ids"]
            rows = list(outputs["results"])
            for index, model_id in enumerate(model_ids):
                job = _lock_job(db, job_id)
                if not job:
                    break
                rows[index] = {"model_id": model_id, "status": "running", "elapsed_seconds": None}
                outputs["results"] = list(rows)
                job.outputs = dict(outputs)
                job.status = "running"
                job.current_step = f"Model {index + 1}/{len(model_ids)}"
                db.commit()

                started = time.monotonic()
                try:
                    client = create_ai_client(account)
                    client.text_model = model_id
                    result = client.chat_with_meta(messages)
                    if not isinstance(result.content, str) or not result.content.strip():
                        raise ValueError("AI returned an empty message")
                    row = {"model_id": model_id, "status": "success", "elapsed_seconds": round(time.monotonic() - started, 2)}
                except Exception as exc:
                    row = {"model_id": model_id, "status": "error", "elapsed_seconds": round(time.monotonic() - started, 2), "error": _safe_error(exc)}

                job = _lock_job(db, job_id)
                if not job:
                    break
                rows[index] = row
                outputs["results"] = list(rows)
                job.outputs = dict(outputs)
                job.progress = round((index + 1) * 100 / len(model_ids))
                db.commit()

            job = _lock_job(db, job_id)
            if not job:
                job = _lock_job(db, job_id, statuses=('cancelled',))
                if not job:
                    return
                rows = list((job.outputs or {}).get("results", rows))
                rows = [{**row, "status": "cancelled"} if row["status"] in {"waiting", "running"} else row for row in rows]
                job.outputs = {**(job.outputs or {}), "results": rows}
                db.commit()
                return
            successes = sum(row["status"] == "success" for row in rows)
            job.status = "success" if successes == len(rows) else "partial_success" if successes else "failed"
            job.current_step = "Completed"
            job.progress = 100
            job.end_time = datetime.utcnow()
            db.commit()
