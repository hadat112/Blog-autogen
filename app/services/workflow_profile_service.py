from sqlalchemy.orm import Session

from app.db import models
from app.services.account_service import fetch_wp_categories


WORKFLOW_TYPES = {"rewrite", "generate_story", "wp_publish"}
AI_WORKFLOW_TYPES = {"rewrite", "generate_story"}


class WorkflowProfileService:
    def __init__(self, db: Session):
        self.db = db

    def list(self, workflow_type=None):
        query = self.db.query(models.Pipeline).filter(models.Pipeline.type.in_(WORKFLOW_TYPES))
        if workflow_type:
            if workflow_type not in WORKFLOW_TYPES:
                raise ValueError("Unsupported workflow profile type")
            query = query.filter(models.Pipeline.type == workflow_type)
        return query.order_by(models.Pipeline.created_at.desc()).all()

    def get(self, profile_id):
        return self.db.query(models.Pipeline).filter(
            models.Pipeline.id == profile_id,
            models.Pipeline.type.in_(WORKFLOW_TYPES),
        ).first()

    def _validated_values(self, data):
        workflow_type = data.type
        if workflow_type not in WORKFLOW_TYPES:
            raise ValueError("Unsupported workflow profile type")
        accounts = dict(data.step_accounts or {})
        required = {"wp"}
        if workflow_type in AI_WORKFLOW_TYPES:
            required.add("ai")
            if not (data.language or "").strip():
                raise ValueError("Target language is required")
        for account_type in required:
            account_id = accounts.get(account_type)
            account = self.db.query(models.Account).filter(models.Account.id == account_id).first()
            if not account or account.type != account_type:
                raise ValueError(f"A valid {account_type.upper()} account is required")
        settings = dict(data.settings or {})
        category = data.wp_category_id
        if category is not None:
            settings["wp_category_id"] = str(category)
        if workflow_type == "rewrite":
            settings["collect_patterns"] = bool(settings.get("collect_patterns", False))
        return {
            "name": data.name.strip(),
            "type": workflow_type,
            "language": (data.language or "").strip(),
            "step_accounts": accounts,
            "settings": settings,
            "is_active": data.is_active,
        }

    def create(self, data):
        profile = models.Pipeline(**self._validated_values(data))
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        return profile

    def update(self, profile_id, data):
        profile = self.get(profile_id)
        if not profile:
            return None
        values = self._validated_values(data)
        if values["type"] != profile.type:
            raise ValueError("Workflow profile type cannot be changed")
        for name, value in values.items():
            setattr(profile, name, value)
        self.db.commit()
        self.db.refresh(profile)
        return profile

    def delete(self, profile_id):
        profile = self.get(profile_id)
        if not profile:
            return False
        has_jobs = self.db.query(models.Job).filter(models.Job.pipeline_id == profile_id).first()
        has_drafts = self.db.query(models.ContentDraft).filter(models.ContentDraft.pipeline_id == profile_id).first()
        if has_jobs or has_drafts:
            raise ValueError("Profile is used by jobs or drafts and cannot be deleted")
        self.db.delete(profile)
        self.db.commit()
        return True

    def categories(self, profile_id):
        profile = self.get(profile_id)
        if not profile:
            return None
        account_id = (profile.step_accounts or {}).get("wp")
        account = self.db.query(models.Account).filter(
            models.Account.id == account_id,
            models.Account.type == "wp",
        ).first()
        if not account:
            raise ValueError("WordPress account is unavailable")
        return fetch_wp_categories(account.config or {})
