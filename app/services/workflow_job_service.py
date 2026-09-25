from datetime import datetime

from sqlalchemy.orm import Session

from app.db import models
from app.services.job_retention_service import JobRetentionService


class WorkflowJobService:
    def __init__(self, db: Session):
        self.db = db

    def create(self, pipeline_id, workflow_type, draft_id=None, parent_job_id=None, input_text=None):
        job = models.Job(
            pipeline_id=pipeline_id,
            workflow_type=workflow_type,
            draft_id=draft_id,
            parent_job_id=parent_job_id,
            input_text=input_text,
            input_type="url" if input_text and input_text.startswith(("http://", "https://")) else None,
            status="queued",
            progress=0,
            logs=[],
            outputs={},
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        JobRetentionService(self.db).prune()
        return job

    def progress(self, job_id, step, progress, detail=None):
        job = self.db.query(models.Job).filter(models.Job.id == job_id).first()
        if not job:
            return None
        if job.status not in {"queued", "running"}:
            return job
        job.status = "running"
        job.current_step = step
        job.progress = progress
        if detail:
            logs = list(job.logs or [])
            logs.append({"timestamp": datetime.utcnow().isoformat(), "step_name": step, "progress": progress, "detail": detail, "event": "info"})
            job.logs = logs[-120:]
        self.db.commit()
        return job

    def complete(self, job_id, outputs=None):
        job = self.db.query(models.Job).filter(models.Job.id == job_id).first()
        if not job:
            return None
        if job.status not in {"queued", "running"}:
            return job
        job.status = "success"
        job.progress = 100
        job.current_step = "Completed"
        job.outputs = outputs or {}
        job.end_time = datetime.utcnow()
        self.db.commit()
        JobRetentionService(self.db).prune()
        return job

    def fail(self, job_id, error):
        job = self.db.query(models.Job).filter(models.Job.id == job_id).first()
        if not job:
            return None
        if job.status not in {"queued", "running"}:
            return job
        outputs = dict(job.outputs or {})
        if job.current_step:
            outputs["failed_step"] = job.current_step
        job.status = "failed"
        job.current_step = "Failed"
        job.end_time = datetime.utcnow()
        job.outputs = outputs
        logs = list(job.logs or [])
        logs.append({"timestamp": datetime.utcnow().isoformat(), "step_name": "Failed", "progress": job.progress, "detail": str(error)[:500], "event": "failed"})
        job.logs = logs[-120:]
        self.db.commit()
        JobRetentionService(self.db).prune()
        return job

    def recover_interrupted(self):
        jobs = self.db.query(models.Job).filter(
            models.Job.workflow_type != "legacy",
            models.Job.status.in_(("queued", "running")),
        ).all()
        for job in jobs:
            outputs = dict(job.outputs or {})
            if job.current_step:
                outputs["failed_step"] = job.current_step
            job.status = "failed"
            job.current_step = "Interrupted by restart"
            job.outputs = outputs
            job.end_time = datetime.utcnow()
            logs = list(job.logs or [])
            logs.append({"timestamp": datetime.utcnow().isoformat(), "step_name": "Interrupted by restart", "progress": job.progress, "detail": "The local app restarted before this workflow finished. Open its workflow screen to recover.", "event": "failed"})
            job.logs = logs[-120:]
        generating = self.db.query(models.ContentDraft).filter(models.ContentDraft.state == "generating").all()
        for draft in generating:
            draft.state = "generation_failed"
            draft.error = "Generation was interrupted by an app restart"
        publishing = self.db.query(models.ContentDraft).filter(models.ContentDraft.state == "publishing").all()
        for draft in publishing:
            draft.state = "publish_unknown"
            draft.error = "Publishing was interrupted; verify WordPress before retrying"
        analyzing = self.db.query(models.Article).filter(models.Article.analysis_status == "processing").all()
        for article in analyzing:
            article.analysis_status = "failed"
            article.analysis_error = "Analysis was interrupted by an app restart"
        enrichments = self.db.query(models.ArticleEnrichment).all()
        for enrichment in enrichments:
            for step in ("summary", "analysis", "dna"):
                if getattr(enrichment, f"{step}_status") == "processing":
                    setattr(enrichment, f"{step}_status", "failed")
                    setattr(enrichment, f"{step}_error", "Enrichment was interrupted by an app restart")
        if jobs or generating or publishing or analyzing:
            self.db.commit()
        return len(jobs)
