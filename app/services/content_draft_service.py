from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.db import models


EDITABLE_STATES = {"generating", "ready_for_review", "generation_failed", "publish_failed", "publish_unknown"}


class DraftConflictError(ValueError):
    pass


class ContentDraftService:
    def __init__(self, db: Session):
        self.db = db

    def list(self, kind=None, pipeline_id=None):
        query = self.db.query(models.ContentDraft)
        if kind:
            query = query.filter(models.ContentDraft.kind == kind)
        if pipeline_id:
            query = query.filter(models.ContentDraft.pipeline_id == pipeline_id)
        return query.order_by(models.ContentDraft.updated_at.desc()).all()

    def get(self, draft_id):
        return self.db.query(models.ContentDraft).filter(models.ContentDraft.id == draft_id).first()

    def create(self, data, state=None):
        values = data.model_dump(exclude={"version"}) if hasattr(data, "model_dump") else dict(data)
        pipeline_id = values.get("pipeline_id")
        profile = self.db.query(models.Pipeline).filter(models.Pipeline.id == pipeline_id).first() if pipeline_id else None
        expected_type = {"manual": "wp_publish", "rewrite": "rewrite", "generated": "generate_story"}.get(values.get("kind"))
        if not profile or profile.type != expected_type:
            raise ValueError("Draft requires a matching workflow profile")
        draft = models.ContentDraft(**values, state=state or ("ready_for_review" if values.get("kind") == "manual" else "generating"))
        self.db.add(draft)
        self.db.commit()
        self.db.refresh(draft)
        return draft

    def update(self, draft_id, data):
        draft = self.get(draft_id)
        if not draft:
            return None
        if draft.state not in EDITABLE_STATES:
            raise ValueError(f"Draft cannot be edited while state is {draft.state}")
        if draft.version != data.version:
            raise DraftConflictError("Draft has changed; reload before saving")
        previous_upload = draft.image_source if draft.image_kind == "upload" else None
        values = data.model_dump(exclude={"version", "kind", "pipeline_id", "source_url", "language"})
        for name, value in values.items():
            setattr(draft, name, value)
        draft.version += 1
        draft.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(draft)
        if previous_upload and (draft.image_kind != "upload" or draft.image_source != previous_upload):
            path = Path(previous_upload)
            if path.is_file() and "var/uploads" in path.as_posix():
                path.unlink(missing_ok=True)
        return draft

    def delete(self, draft_id):
        draft = self.get(draft_id)
        if not draft:
            return False
        if draft.state in {"publishing", "wordpress_created"}:
            raise ValueError("Publishing or published drafts cannot be deleted")
        upload = draft.image_source if draft.image_kind == "upload" else None
        self.db.delete(draft)
        self.db.commit()
        if upload:
            path = Path(upload)
            if path.is_file() and "var/uploads" in path.as_posix():
                path.unlink(missing_ok=True)
        return True

    def transition(self, draft_id, allowed_from, state, error=None, **updates):
        draft = self.get(draft_id)
        if not draft:
            return None
        if draft.state not in set(allowed_from):
            raise DraftConflictError(f"Cannot move draft from {draft.state} to {state}")
        draft.state = state
        draft.error = error
        draft.version += 1
        draft.updated_at = datetime.utcnow()
        for name, value in updates.items():
            setattr(draft, name, value)
        self.db.commit()
        self.db.refresh(draft)
        return draft
