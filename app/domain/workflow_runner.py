import asyncio
from datetime import datetime

from app.db import models
from app.db.session import SessionLocal
from app.services.job_retention_service import JobRetentionService


class WorkflowRunner:
    def __init__(self):
        self.active_jobs = {}
        self.queue = []
        self.worker_task = None
        self._wake = None

    def start(self, job_id, operation):
        self.queue.append((job_id, operation))
        if self.worker_task is None or self.worker_task.done():
            self._wake = asyncio.Event()
            self.worker_task = asyncio.create_task(self._drain_queue())
        self._wake.set()
        return self.worker_task

    async def _drain_queue(self):
        # Account quotas are enforced around HTTP requests, not around whole jobs.
        pending = set()
        while self.queue or pending:
            while self.queue and len(pending) < 8:
                job_id, operation = self.queue.pop(0)
                task = asyncio.create_task(self._run(job_id, operation))
                self.active_jobs[job_id] = task
                pending.add(task)
            if pending:
                self._wake.clear()
                wake_task = asyncio.create_task(self._wake.wait())
                done, _ = await asyncio.wait(pending | {wake_task}, return_when=asyncio.FIRST_COMPLETED)
                if wake_task not in done:
                    wake_task.cancel()
                    try:
                        await wake_task
                    except asyncio.CancelledError:
                        pass
                done.discard(wake_task)
                pending.difference_update(done)
                for task in done:
                    if not task.cancelled():
                        error = task.exception()
                        if error:
                            import logging
                            logging.getLogger(__name__).error("Workflow operation failed", exc_info=(type(error), error, error.__traceback__))

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
                if job.workflow_type == "model_benchmark":
                    outputs["results"] = [
                        {**row, "status": "cancelled"} if row.get("status") in {"waiting", "running"} else row
                        for row in outputs.get("results", [])
                    ]
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
                JobRetentionService(db).prune()

    async def cancel(self, job_id):
        task = self.active_jobs.get(job_id)
        if not task:
            queued = next((item for item in self.queue if item[0] == job_id), None)
            if not queued:
                return None
            self.queue.remove(queued)
            self._mark_cancelled(job_id)
            return {"status": "cancelled"}
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        self._mark_cancelled(job_id)
        return {"status": "cancelled"}


workflow_runner = WorkflowRunner()
