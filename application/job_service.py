from datetime import datetime

from sqlalchemy.orm import Session

from infrastructure.db import models


class JobService:
    def __init__(self, db: Session):
        self.db = db

    def list_jobs(self, limit: int = 20):
        results = self.db.query(models.Job, models.Pipeline.name).join(
            models.Pipeline, models.Job.pipeline_id == models.Pipeline.id
        ).order_by(models.Job.start_time.desc()).limit(limit).all()

        jobs = []
        for job, pipeline_name in results:
            job.pipeline_name = pipeline_name
            jobs.append(job)
        return jobs

    def get_job(self, job_id: str):
        result = self.db.query(models.Job, models.Pipeline.name).join(
            models.Pipeline, models.Job.pipeline_id == models.Pipeline.id
        ).filter(models.Job.id == job_id).first()

        if not result:
            return None

        job, pipeline_name = result
        job.pipeline_name = pipeline_name
        return job

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
                    return {"status": "updated", "new_status": "success"}

        return {"status": "checked", "current_status": job.status}
