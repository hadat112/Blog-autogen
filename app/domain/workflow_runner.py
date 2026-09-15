import asyncio
from datetime import datetime

from app.db import models
from app.db.session import SessionLocal


class WorkflowRunner:
    def __init__(self):
        self.active_jobs = {}

    def start(self, job_id, operation):
        task = asyncio.create_task(self._run(job_id, operation))
        self.active_jobs[job_id] = task
        return task

    async def _run(self, job_id, operation):
        try:
            await operation()
        except asyncio.CancelledError:
            self._mark_cancelled(job_id)
            raise
        finally:
            self.active_jobs.pop(job_id, None)

    def _mark_cancelled(self, job_id):
        with SessionLocal() as db:
            job = db.query(models.Job).filter(models.Job.id == job_id).first()
            if job and job.status in {"queued", "running"}:
                outputs = dict(job.outputs or {})
                if job.current_step:
                    outputs["cancelled_step"] = job.current_step
                job.status = "cancelled"
                job.current_step = "Cancelled"
                job.outputs = outputs
                job.end_time = datetime.utcnow()
                if job.draft_id:
                    draft = db.query(models.ContentDraft).filter(models.ContentDraft.id == job.draft_id).first()
                    if draft and draft.state == "generating":
                        draft.state = "generation_failed"
                        draft.error = "Generation was cancelled"
                db.commit()

    async def cancel(self, job_id):
        task = self.active_jobs.get(job_id)
        if not task:
            return None
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        self._mark_cancelled(job_id)
        return {"status": "cancelled"}


workflow_runner = WorkflowRunner()
