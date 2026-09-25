from datetime import datetime
from math import ceil
from typing import Optional

from sqlalchemy.orm import Session

from app.domain.job_runner import job_runner
from app.domain.workflow_runner import workflow_runner
from app.db import models
from app.services.job_retention_service import JobRetentionService


class JobService:
    def __init__(self, db: Session):
        self.db = db

    def list_jobs(self, page: int = 1, page_size: int = 10, workflow_type: Optional[str] = None, status_group: Optional[str] = None, status: Optional[str] = None):
        jobs_query = self.db.query(models.Job)
        if not workflow_type or workflow_type == "all":
            # Enrichment jobs are monitored from Pattern Library and should
            # not pollute the main Dashboard activity feed.
            jobs_query = jobs_query.filter(~models.Job.workflow_type.like("article_enrichment_%"))
        else:
            if workflow_type == "legacy":
                jobs_query = jobs_query.filter(models.Job.workflow_type.in_(["legacy", "article_v1"]))
            elif workflow_type == "rewrite":
                jobs_query = jobs_query.filter(models.Job.workflow_type.in_(["rewrite", "article_v2"]))
            elif workflow_type == "article_enrichment":
                jobs_query = jobs_query.filter(models.Job.workflow_type.like("article_enrichment_%"))
            else:
                jobs_query = jobs_query.filter(models.Job.workflow_type == workflow_type)
        if status_group == "active":
            jobs_query = jobs_query.filter(models.Job.status.in_(("queued", "running")))
        elif status_group == "history":
            jobs_query = jobs_query.filter(~models.Job.status.in_(("queued", "running")))
        if status and status != "all":
            jobs_query = jobs_query.filter(models.Job.status == status)

        total = jobs_query.count()
        results = jobs_query.with_entities(models.Job, models.Pipeline.name).outerjoin(
            models.Pipeline, models.Job.pipeline_id == models.Pipeline.id
        ).order_by(models.Job.start_time.desc(), models.Job.id.desc()).offset((page - 1) * page_size).limit(page_size).all()

        jobs = []
        for job, pipeline_name in results:
            job.pipeline_name = pipeline_name or (
                "AI Enrichment" if (job.workflow_type or "").startswith("article_enrichment_") else None
            )
            self._decorate(job)
            jobs.append(job)
        return {
            "items": jobs,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": ceil(total / page_size) if total else 0,
        }

    def get_job(self, job_id: str):
        result = self.db.query(models.Job, models.Pipeline.name).outerjoin(
            models.Pipeline, models.Job.pipeline_id == models.Pipeline.id
        ).filter(models.Job.id == job_id).first()

        if not result:
            return None

        job, pipeline_name = result
        job.pipeline_name = pipeline_name or (
            "AI Enrichment" if (job.workflow_type or "").startswith("article_enrichment_") else None
        )
        self._decorate(job)
        return job

    def _decorate(self, job):
        outputs = dict(job.outputs or {})
        if not outputs.get("wp_url"):
            for log in reversed(list(job.logs or [])):
                detail = log.get("detail") if isinstance(log, dict) else None
                marker = "WP Success: "
                if isinstance(detail, str) and marker in detail:
                    candidate = detail.split(marker, 1)[1].strip().split()[0]
                    if candidate.startswith(("http://", "https://")):
                        outputs["wp_url"] = candidate
                        break
        job.outputs = outputs
        job.capabilities = {
            "can_cancel": job.status in {"queued", "running"},
            "can_rerun": (job.workflow_type or "legacy") in {"legacy", "rewrite", "article_v1", "article_v2", "article_workflow"} and job.status in {"failed", "cancelled"} and not job.rerun_job_id,
            "can_open_draft": bool(job.draft_id),
            "can_copy_link": bool(outputs.get("wp_url")),
        }

    def sync_job_status(self, job_id: str):
        job = self.db.query(models.Job).filter(models.Job.id == job_id).first()
        if not job:
            return None

        if job.status == "running":
            logs = list(job.logs or [])
            if job.progress == 100 and len(logs) > 0:
                last_log = logs[-1]
                if "Completed" in last_log.get("step_name", "") or last_log.get("progress") == 100:
                    job.status = "success"
                    job.end_time = datetime.utcnow()
                    self.db.commit()
                    JobRetentionService(self.db).prune()
                    return {"status": "updated", "new_status": "success"}

        return {"status": "checked", "current_status": job.status}

    async def cancel_job(self, job_id: str):
        job = self.db.query(models.Job).filter(models.Job.id == job_id).first()
        if not job:
            return await job_runner.cancel_job(job_id)
        if (job.workflow_type or "legacy") != "legacy":
            if job.status not in {"queued", "running"}:
                return {"status": "not_cancelled", "current_status": job.status}
            result = await workflow_runner.cancel(job_id)
            if result is None:
                outputs = dict(job.outputs or {})
                if job.current_step:
                    outputs["cancelled_step"] = job.current_step
                job.status = "cancelled"
                job.current_step = "Cancelled"
                job.outputs = outputs
                job.end_time = datetime.utcnow()
                if job.draft_id:
                    draft = self.db.query(models.ContentDraft).filter(models.ContentDraft.id == job.draft_id).first()
                    if draft and draft.state == "generating":
                        draft.state = "generation_failed"
                        draft.error = "Generation was cancelled"
                self.db.commit()
                JobRetentionService(self.db).prune()
                return {"status": "cancelled"}
            return result
        return await job_runner.cancel_job(job_id)
