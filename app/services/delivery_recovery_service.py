"""Operator reconciliation of an uncertain external delivery, without resending it."""
from datetime import datetime
from app.db import models
from app.services.wordpress_publishing_service import _draft_locks


def resolve_delivery(db, draft_id, channel, outcome, external_id=None, url=None, confirmed=False):
    if not confirmed:
        raise ValueError('Verify the external service and explicitly confirm the result first')
    lock = _draft_locks[draft_id]
    if not lock.acquire(blocking=False):
        raise ValueError('An external publication is still in progress; wait for it to finish')
    try:
        if db.query(models.Job.id).filter(models.Job.draft_id == draft_id, models.Job.status.in_(['queued','running'])).first():
            raise ValueError('Wait for the active attempt to finish before resolving delivery')
        draft = db.get(models.ContentDraft, draft_id)
        if not draft:
            raise ValueError('Draft not found')
        record = db.get(models.WorkflowRecovery, draft_id)
        artifacts = dict(record.artifacts or {}) if record else {}
        pending = channel + '_pending'
        if channel == 'wordpress':
            if draft.state not in {'publish_unknown', 'publishing'}:
                raise ValueError('WordPress delivery is not uncertain')
            if outcome == 'sent':
                if not external_id or not url or not url.startswith(('https://','http://')):
                    raise ValueError('Confirmed WordPress delivery requires its post ID and URL')
                if draft.wp_post_id and str(draft.wp_post_id) != str(external_id):
                    raise ValueError('A different WordPress post is already recorded')
                draft.wp_post_id, draft.wp_url = external_id, url
                draft.state = 'wordpress_created'
                draft.wordpress_created_at = datetime.utcnow()
                artifacts['wordpress'] = {'wp_post_id': external_id, 'wp_url':url, 'wp_status':draft.wp_status,'error':None}
            else:
                if draft.wp_post_id:
                    raise ValueError('A confirmed WordPress post cannot be cleared')
                draft.state = 'ready_for_review'
                artifacts.pop('wordpress', None)
        else:
            if not artifacts.get(pending):
                raise ValueError('This delivery is not uncertain')
            if outcome == 'sent':
                if channel == 'facebook' and not external_id:
                    raise ValueError('Confirmed Facebook delivery requires its post ID')
                artifacts[channel] = external_id if channel == 'facebook' else 'sent'
            else:
                if artifacts.get(channel):
                    raise ValueError('A confirmed delivery cannot be cleared')
            artifacts[pending] = False
        if record:
            record.artifacts = artifacts
            record.revision += 1
        draft.error = None
        draft.version += 1
        db.commit()
        return {'status':'resolved', 'draft_id': draft_id}
    finally:
        lock.release()
