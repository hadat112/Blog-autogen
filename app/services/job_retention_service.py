from app.db import models


MAX_STORED_JOBS = 500
ACTIVE_STATUSES = {"queued", "running"}


class JobRetentionService:
    def __init__(self, db):
        self.db = db

    def prune(self, limit=MAX_STORED_JOBS):
        jobs = self.db.query(models.Job).order_by(
            models.Job.start_time.desc(), models.Job.id.desc()
        ).all()
        excess = max(0, len(jobs) - limit)
        if not excess:
            return 0

        deleted = 0
        for job in reversed(jobs):
            if deleted >= excess:
                break
            if job.status in ACTIVE_STATUSES:
                continue
            self.db.query(models.Job).filter(
                models.Job.parent_job_id == job.id
            ).update({models.Job.parent_job_id: None}, synchronize_session=False)
            self.db.delete(job)
            deleted += 1
        if deleted:
            self.db.commit()
        return deleted
