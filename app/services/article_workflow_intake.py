"""Durable input boundary for article workflows; execution stays in the shared service."""
import hashlib
from datetime import datetime

from sqlalchemy.orm import Session

from app.db import models
from app.domain.settings_manager import SettingsManager
from app.domain.translation_prompts import TRANSLATION_PROMPT_VERSION
from app.domain.translation_settings import resolve_translation_chunk_size


def build_article_manifest(db: Session, draft: models.ContentDraft, *, mode: str,
                           source_kind: str = 'url', use_proxy: bool = False,
                           use_enrichment: bool = False, app_config=None, frozen=None) -> dict:
    pipeline = db.get(models.Pipeline, draft.pipeline_id)
    accounts = dict((frozen or {}).get('step_accounts', pipeline.step_accounts or {}))
    account = db.get(models.Account, accounts.get('ai')) if accounts.get('ai') else None
    config = SettingsManager().config if app_config is None else app_config
    return {
        'source_kind': source_kind, 'source_url': draft.source_url,
        'mode': mode, 'language': pipeline.language, 'step_accounts': accounts,
        'category_id': draft.category_id, 'use_proxy': use_proxy, 'use_enrichment': use_enrichment,
        'text_model': (account.config or {}).get('text_model') if account else None,
        'chunk_size': resolve_translation_chunk_size(account.config if account else {}, config),
        'translation_mode': config.get('translation_mode', 'sequential'),
        'prompt_version': TRANSLATION_PROMPT_VERSION,
    }


def create_manual_article_attempt(db: Session, *, pipeline_id: str, mode: str,
                                  title: str, content: str, image_kind=None, image_source=None):
    if mode not in {'v1', 'v2'} or not title.strip() or not content.strip():
        raise ValueError('A title, content and valid V1/V2 mode are required')
    pipeline = db.get(models.Pipeline, pipeline_id)
    if not pipeline or not pipeline.is_active:
        raise LookupError('Active pipeline not found')
    for role, label in [('ai', 'AI'), ('wp', 'WordPress')]:
        account_id = (pipeline.step_accounts or {}).get(role)
        account = db.get(models.Account, account_id) if account_id else None
        if not account or account.type != role:
            raise ValueError(f'Selected pipeline has no valid {label} account')
    draft = models.ContentDraft(
        kind=f'article_{mode}', pipeline_id=pipeline.id,
        wp_account_id=pipeline.step_accounts['wp'], source_url=None,
        language=pipeline.language, category_id=(pipeline.settings or {}).get('wp_category_id'),
        wp_status='publish', state='generating', image_kind=image_kind, image_source=image_source,
    )
    db.add(draft)
    db.flush()
    job = models.Job(pipeline_id=pipeline.id, draft_id=draft.id, workflow_type=f'article_{mode}',
                     status='queued', progress=0, input_type='prompt', input_text=title, logs=[], outputs={})
    db.add(job)
    db.flush()
    source = {'title': title, 'content': content, 'image_url': image_source if image_kind == 'url' else '',
              'source_url': None, 'image_kind': image_kind, 'image_source': image_source}
    manifest = build_article_manifest(db, draft, mode=mode, source_kind='manual')
    db.add(models.WorkflowRecovery(draft_id=draft.id, active_job_id=job.id, manifest=manifest,
        artifacts={'source': source, 'source_hash': hashlib.sha256(content.encode()).hexdigest()}, revision=0))
    db.commit()
    return job, draft


def create_article_retry(db: Session, old_job: models.Job, draft: models.ContentDraft, *, mode: str):
    """Claim retry and insert its job in one transaction, leaving saved input untouched."""
    job_id = models.generate_uuid()
    claimed = db.query(models.Job).filter(models.Job.id == old_job.id,
        models.Job.rerun_job_id.is_(None), models.Job.status.in_(['failed', 'cancelled'])).update(
            {'rerun_at': datetime.utcnow(), 'rerun_job_id': job_id}, synchronize_session=False)
    if claimed != 1:
        db.rollback()
        raise ValueError('This job already has a retry')
    active = db.query(models.Job.id).filter(models.Job.draft_id == draft.id,
                                           models.Job.status.in_(['queued', 'running'])).first()
    if active:
        db.rollback()
        raise ValueError('This draft already has an active attempt')
    job = models.Job(id=job_id, pipeline_id=old_job.pipeline_id, workflow_type=f'article_{mode}',
                     draft_id=draft.id, input_text=old_job.input_text, input_type=old_job.input_type,
                     status='queued', progress=0, logs=[], outputs={})
    db.add(job)
    db.commit()
    return job
