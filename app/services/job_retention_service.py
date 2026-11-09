from app.db import models


MAX_STORED_JOBS = 500
MAX_FULL_SUCCESSFUL_DRAFTS = 100
ACTIVE_STATUSES = {"queued", "running"}


class JobRetentionService:
    def __init__(self, db):
        self.db = db

    def prune(self, limit=MAX_STORED_JOBS):
        self._compact_old_successful_drafts()
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

    def _compact_old_successful_drafts(self, limit=MAX_FULL_SUCCESSFUL_DRAFTS):
        """Keep recent published output, but remove large old draft bodies.

        The row and WordPress metadata remain available for history/recovery.
        Source articles are intentionally not touched because they are the
        reusable creative archive.
        """
        successful_states = {"wordpress_created", "published"}
        drafts = self.db.query(models.ContentDraft).filter(
            models.ContentDraft.state.in_(successful_states),
            models.ContentDraft.content != "",
        ).order_by(models.ContentDraft.updated_at.desc(), models.ContentDraft.id.desc()).all()
        compacted = 0
        for draft in drafts[limit:]:
            recovery = self.db.get(models.WorkflowRecovery, draft.id)
            if recovery and not (recovery.artifacts or {}).get("complete"):
                continue
            if recovery:
                recovery.artifacts = {"complete": True}
            draft.content = ""
            draft.caption = None
            compacted += 1
        if compacted:
            self.db.commit()
        return compacted
