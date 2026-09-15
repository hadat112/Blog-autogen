import html
import threading
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.db import models
from app.integrations.wordpress.destination import AmbiguousWordPressResult, WordPressDestinationGateway


_draft_locks = defaultdict(threading.Lock)


def plain_text_to_html(value):
    paragraphs = [part.strip() for part in (value or "").split("\n\n") if part.strip()]
    return "\n".join(f"<p>{html.escape(part).replace(chr(10), '<br>')}</p>" for part in paragraphs)


class WordPressPublishingService:
    def __init__(self, db: Session, gateway_factory=WordPressDestinationGateway):
        self.db = db
        self.gateway_factory = gateway_factory

    def _pipeline_and_account(self, draft):
        if draft.wp_account_id:
            account = self.db.query(models.Account).filter(models.Account.id == draft.wp_account_id, models.Account.type == "wp").first()
            if not account:
                raise ValueError("WordPress account is unavailable")
            return None, account
        pipeline = self.db.query(models.Pipeline).filter(models.Pipeline.id == draft.pipeline_id).first()
        if not pipeline or not pipeline.is_active:
            raise ValueError("Draft pipeline is unavailable")
        account_id = (pipeline.step_accounts or {}).get("wp")
        account = self.db.query(models.Account).filter(models.Account.id == account_id, models.Account.type == "wp").first()
        if not account:
            raise ValueError("WordPress account is unavailable")
        return pipeline, account

    def publish(self, draft_id, confirmed=False):
        lock = _draft_locks[draft_id]
        if not lock.acquire(blocking=False):
            raise ValueError("This draft is already being published")
        try:
            draft = self.db.query(models.ContentDraft).filter(models.ContentDraft.id == draft_id).first()
            if not draft:
                return None
            if draft.wp_post_id or draft.state == "wordpress_created":
                raise ValueError("This draft was already created in WordPress")
            if draft.state == "publish_unknown":
                raise ValueError("Verify the ambiguous WordPress result before retrying")
            if draft.wp_status == "publish" and not confirmed:
                raise ValueError("Publishing now requires explicit confirmation")
            if not draft.title.strip() or not draft.content.strip():
                raise ValueError("Title and content are required")
            _, account = self._pipeline_and_account(draft)
            gateway = self.gateway_factory(account.config or {})
            draft.state = "publishing"
            draft.error = None
            self.db.commit()
            media_id = draft.wp_media_id
            try:
                if draft.image_source and not media_id:
                    if draft.image_kind == "url":
                        media_id = gateway.upload_remote(draft.image_source)
                    elif draft.image_kind == "upload":
                        media_id = gateway.upload_file(draft.image_source)
                    else:
                        raise ValueError("Unsupported image source")
                    draft.wp_media_id = str(media_id)
                    self.db.commit()
                content = draft.content if draft.content_format == "html" else plain_text_to_html(draft.content)
                result = gateway.create_post(
                    draft.title,
                    content,
                    status=draft.wp_status,
                    category_id=draft.category_id,
                    media_id=media_id,
                )
            except AmbiguousWordPressResult as exc:
                draft.state = "publish_unknown"
                draft.error = str(exc)
                self.db.commit()
                raise
            except Exception as exc:
                draft.state = "publish_failed"
                draft.error = str(exc)
                self.db.commit()
                raise
            draft.state = "wordpress_created"
            draft.wp_post_id = result["id"]
            draft.wp_url = result["link"]
            draft.wp_status = result["status"]
            draft.wordpress_created_at = datetime.utcnow()
            draft.version += 1
            self.db.commit()
            self.db.refresh(draft)
            if draft.image_kind == "upload" and draft.image_source:
                path = Path(draft.image_source)
                if path.is_file() and "var/uploads" in path.as_posix():
                    path.unlink(missing_ok=True)
            return draft
        finally:
            lock.release()
