"""Draft-owned artifacts. Every write is fenced to its active job attempt."""
from datetime import datetime
from sqlalchemy import exists, update
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from app.db import models


class WorkflowRecoveryService:
    def __init__(self, db, draft_id, job_id):
        self.sessions = sessionmaker(bind=db.get_bind())
        self.draft_id = draft_id
        self.job_id = job_id

    def _live_job(self):
        return exists().where(models.Job.id == self.job_id).where(models.Job.status.in_(['queued', 'running']))

    def check_active(self):
        with self.sessions() as db:
            row = db.get(models.WorkflowRecovery, self.draft_id)
            job = db.get(models.Job, self.job_id)
            if not row or row.active_job_id != self.job_id or not job or job.status not in {'queued', 'running'}:
                raise InterruptedError('Workflow attempt cancelled or replaced')

    def cancelled(self):
        try:
            self.check_active()
            return False
        except InterruptedError:
            return True

    def claim(self, manifest):
        with self.sessions() as db:
            row = db.get(models.WorkflowRecovery, self.draft_id)
            if row is None:
                db.add(models.WorkflowRecovery(draft_id=self.draft_id, active_job_id=self.job_id, manifest=manifest, artifacts={}, revision=0))
                try:
                    db.commit()
                    return manifest
                except IntegrityError:
                    db.rollback()
                    row = db.get(models.WorkflowRecovery, self.draft_id)
            if row.active_job_id != self.job_id:
                old = db.get(models.Job, row.active_job_id)
                if old and old.status in {'queued', 'running'}:
                    raise ValueError('This draft already has an active attempt')
            original = dict(row.manifest or {})
            # Existing settings are frozen. Credentials may be repaired on the same account.
            if (original.get('text_model') != manifest.get('text_model') or original.get('prompt_version') != manifest.get('prompt_version')) and not (row.artifacts or {}).get('assembled'):
                raise ValueError('AI model or prompt version changed; start a fresh run to avoid mixing translations')
            owner = row.active_job_id
            result = db.execute(update(models.WorkflowRecovery).where(
                models.WorkflowRecovery.draft_id == self.draft_id,
                models.WorkflowRecovery.active_job_id == owner,
                models.WorkflowRecovery.revision == row.revision,
            ).values(active_job_id=self.job_id, revision=row.revision + 1))
            if result.rowcount != 1:
                raise ValueError('Another retry is already active')
            db.commit()
            return original

    def get(self, stage, default=None):
        with self.sessions() as db:
            row = db.get(models.WorkflowRecovery, self.draft_id)
            return (row.artifacts or {}).get(stage, default) if row else default

    def save(self, stage, value):
        # Optimistic revision prevents completed parallel chunks from losing one another.
        for _ in range(30):
            with self.sessions() as db:
                row = db.get(models.WorkflowRecovery, self.draft_id)
                if not row or row.active_job_id != self.job_id:
                    raise InterruptedError('Workflow attempt replaced')
                artifacts = dict(row.artifacts or {})
                artifacts[stage] = value
                revision = row.revision
                result = db.execute(update(models.WorkflowRecovery).where(
                    models.WorkflowRecovery.draft_id == self.draft_id,
                    models.WorkflowRecovery.active_job_id == self.job_id,
                    models.WorkflowRecovery.revision == revision,
                    self._live_job(),
                ).values(artifacts=artifacts, revision=revision + 1, updated_at=datetime.utcnow()))
                if result.rowcount == 1:
                    db.commit()
                    return value
            self.check_active()
        raise RuntimeError('Recovery checkpoint changed too often; retry this stage')

    def save_receipt(self, channel, value):
        # Only confirmed external receipts may be saved after cancellation. This
        # does not grant the old worker permission to mutate content or status.
        if channel not in {"facebook", "telegram"} or not value:
            raise ValueError("A confirmed delivery receipt is required")
        for _ in range(30):
            with self.sessions() as db:
                row = db.get(models.WorkflowRecovery, self.draft_id)
                if not row:
                    raise InterruptedError("Recovery record removed")
                artifacts = dict(row.artifacts or {})
                if artifacts.get(channel) and artifacts[channel] != value:
                    raise ValueError("A different delivery receipt is already saved")
                artifacts[channel] = value
                artifacts[channel + "_pending"] = False
                result = db.execute(update(models.WorkflowRecovery).where(
                    models.WorkflowRecovery.draft_id == self.draft_id,
                    models.WorkflowRecovery.revision == row.revision,
                ).values(artifacts=artifacts, revision=row.revision + 1))
                if result.rowcount == 1:
                    db.commit()
                    return
        raise RuntimeError("Could not save confirmed delivery receipt")

    def finish_cancelled(self):
        with self.sessions() as db:
            ownership = exists().where(models.WorkflowRecovery.draft_id == self.draft_id).where(models.WorkflowRecovery.active_job_id == self.job_id)
            cancelled_job = exists().where(models.Job.id == self.job_id).where(models.Job.status == "cancelled")
            db.execute(update(models.ContentDraft).where(models.ContentDraft.id == self.draft_id,
                models.ContentDraft.state == "generating", ownership, cancelled_job).values(
                    state="generation_failed", error="Generation was cancelled"))
            db.commit()

    def save_draft(self, **values):
        with self.sessions() as db:
            ownership = exists().where(models.WorkflowRecovery.draft_id == self.draft_id).where(models.WorkflowRecovery.active_job_id == self.job_id)
            result = db.execute(update(models.ContentDraft).where(models.ContentDraft.id == self.draft_id, ownership, self._live_job()).values(**values))
            if result.rowcount != 1:
                raise InterruptedError('Workflow attempt cancelled or replaced')
            db.commit()
