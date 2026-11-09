from app.domain.workflow_threads import run_workflow_blocking
from pathlib import Path
from typing import Literal, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, HttpUrl, TypeAdapter, ValidationError
from sqlalchemy.orm import Session

from app.api.workflow_schemas import ArticleWorkflowRunInput, WorkflowJobCreated
from app.db import models
from app.db.session import get_db
from app.domain.workflow_runner import workflow_runner
from app.services.article_service import normalize_source_url
from app.services.article_workflow_service import ArticleWorkflowService
from app.services.workflow_job_service import WorkflowJobService
from app.services.article_workflow_intake import create_article_retry, create_manual_article_attempt
from app.services.draft_image_storage import store_draft_image

router = APIRouter(prefix="/article-workflows", tags=["article_workflows"])


def _schedule_article(job_id, draft_id, *, mode, use_proxy=False, use_enrichment=False):
    async def operation():
        await run_workflow_blocking(ArticleWorkflowService.execute, job_id, draft_id,
                                   mode=mode, use_proxy=use_proxy, use_enrichment=use_enrichment)
    workflow_runner.start(job_id, operation)


@router.post('/run-text', response_model=WorkflowJobCreated)
async def run_manual_article_workflow(
    pipeline_id: str = Form(...), mode: Literal['v1', 'v2'] = Form('v2'),
    title: str = Form(...), content: str = Form(...), image_url: str = Form(''),
    image: Optional[UploadFile] = File(None), db: Session = Depends(get_db),
):
    if not title.strip() or not content.strip():
        raise HTTPException(status_code=400, detail='Title and content are required')
    image_url = image_url.strip()
    if image_url and image is not None:
        raise HTTPException(status_code=400, detail='Choose either an image URL or an upload')
    if image_url:
        try:
            TypeAdapter(HttpUrl).validate_python(image_url)
        except ValidationError as exc:
            raise HTTPException(status_code=400, detail='Image URL must use HTTP or HTTPS') from exc
    uploaded_path = None
    try:
        if image is not None:
            uploaded_path = await store_draft_image(image)
        job, draft = create_manual_article_attempt(db, pipeline_id=pipeline_id, mode=mode,
            title=title, content=content,
            image_kind='upload' if uploaded_path else 'url' if image_url else None,
            image_source=uploaded_path or image_url or None)
    except Exception as exc:
        db.rollback()
        if uploaded_path:
            Path(uploaded_path).unlink(missing_ok=True)
        if isinstance(exc, LookupError):
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        if isinstance(exc, ValueError):
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        raise
    try:
        _schedule_article(job.id, draft.id, mode=mode)
    except Exception as exc:
        WorkflowJobService(db).fail(job.id, 'Workflow dispatch failed; retry this saved attempt')
        raise HTTPException(status_code=503, detail='Could not start workflow; the saved attempt can be resumed from Dashboard') from exc
    return {'job_id': job.id, 'draft_id': draft.id, 'status': 'queued'}


def _extract_mode_from_job(job: models.Job) -> str:
    wf = (job.workflow_type or "").lower()
    if "v1" in wf or wf == "legacy":
        return "v1"
    return "v2"


@router.post("/run", response_model=WorkflowJobCreated)
async def run_article_workflow(data: ArticleWorkflowRunInput, db: Session = Depends(get_db)):
    pipeline = (
        db.query(models.Pipeline)
        .filter(models.Pipeline.id == data.pipeline_id, models.Pipeline.is_active.is_(True))
        .first()
    )
    if not pipeline:
        raise HTTPException(status_code=404, detail="Active pipeline not found")
    if (pipeline.language or "").strip() and not (pipeline.step_accounts or {}).get("ai"):
        raise HTTPException(status_code=400, detail="Selected pipeline has no AI account")
    if not (pipeline.step_accounts or {}).get("wp"):
        raise HTTPException(status_code=400, detail="Selected pipeline has no WordPress account")

    previous_job = None
    if data.rerun_from_job_id:
        previous_job = (
            db.query(models.Job)
            .filter(
                models.Job.id == data.rerun_from_job_id,
                models.Job.pipeline_id == pipeline.id,
                models.Job.status.in_(["failed", "cancelled"]),
            )
            .first()
        )
        if not previous_job:
            raise HTTPException(status_code=400, detail="Only a failed or cancelled job can be retried")
        if previous_job.rerun_job_id:
            raise HTTPException(status_code=400, detail="This job has already been retried")

    try:
        source_url = normalize_source_url(data.source_url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    mode = data.mode if data.mode in {"v1", "v2"} else "v2"

    draft = db.get(models.ContentDraft, previous_job.draft_id) if previous_job and previous_job.draft_id else None
    if draft:
        if normalize_source_url(draft.source_url) != source_url:
            raise HTTPException(status_code=400, detail="Resume must use the original source URL; start a fresh run for a different source")
        active = db.query(models.Job.id).filter(models.Job.draft_id == draft.id, models.Job.status.in_(["queued", "running"])).first()
        if active:
            raise HTTPException(status_code=409, detail="This draft already has an active attempt")
    else:
        draft = models.ContentDraft(
            kind=f"article_{mode}",
            pipeline_id=pipeline.id,
            source_url=source_url,
            language=pipeline.language,
            category_id=(pipeline.settings or {}).get("wp_category_id"),
            wp_status="publish",
            state="generating",
        )
    db.add(draft)
    db.commit()
    db.refresh(draft)

    if previous_job:
        try:
            job = create_article_retry(db, previous_job, draft, mode=mode)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    else:
        job = WorkflowJobService(db).create(pipeline.id, f"article_{mode}", draft.id, input_text=source_url)

    _schedule_article(job.id, draft.id, mode=mode, use_proxy=data.use_proxy, use_enrichment=data.use_enrichment)
    return {"job_id": job.id, "draft_id": draft.id, "status": job.status}


@router.post("/{job_id}/retry", response_model=WorkflowJobCreated)
async def retry_article_workflow(job_id: str, db: Session = Depends(get_db)):
    old_job = (
        db.query(models.Job)
        .filter(models.Job.id == job_id, models.Job.status.in_(["failed", "cancelled"]))
        .first()
    )
    if not old_job:
        raise HTTPException(status_code=404, detail="Retryable job not found")
    if old_job.rerun_job_id:
        raise HTTPException(status_code=400, detail="This job has already been retried")

    pipeline = (
        db.query(models.Pipeline)
        .filter(models.Pipeline.id == old_job.pipeline_id, models.Pipeline.is_active.is_(True))
        .first()
    )
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline for this job no longer exists or is inactive")

    mode = _extract_mode_from_job(old_job)
    recovery = db.get(models.WorkflowRecovery, old_job.draft_id) if old_job.draft_id else None
    if recovery and (recovery.manifest or {}).get('source_kind') == 'manual':
        draft = db.get(models.ContentDraft, old_job.draft_id)
        if not draft or not (recovery.artifacts or {}).get('source'):
            raise HTTPException(status_code=400, detail='Saved manual source is unavailable; start a new run')
        mode = recovery.manifest['mode']
        try:
            job = create_article_retry(db, old_job, draft, mode=mode)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        try:
            _schedule_article(job.id, draft.id, mode=mode)
        except Exception as exc:
            WorkflowJobService(db).fail(job.id, 'Workflow dispatch failed; retry this saved attempt')
            raise HTTPException(status_code=503, detail='Could not start workflow; resume the saved attempt from Dashboard') from exc
        return {'job_id': job.id, 'draft_id': draft.id, 'status': 'queued'}
    source_url = old_job.input_text
    if not source_url:
        raise HTTPException(status_code=400, detail="Source URL not found on old job")

    run_input = ArticleWorkflowRunInput(
        pipeline_id=pipeline.id,
        source_url=source_url,
        mode=mode,
        rerun_from_job_id=old_job.id,
    )
    return await run_article_workflow(run_input, db)


class DeliveryResolution(BaseModel):
    channel: Literal["wordpress", "facebook", "telegram"]
    outcome: Literal["sent", "not_sent"]
    external_id: Optional[str] = None
    url: Optional[str] = None
    confirmed: bool = False


@router.post("/{job_id}/resolve-delivery")
def resolve_uncertain_delivery(job_id: str, data: DeliveryResolution, db: Session = Depends(get_db)):
    from app.services.delivery_recovery_service import resolve_delivery
    job = db.get(models.Job, job_id)
    if not job or not job.draft_id:
        raise HTTPException(status_code=404, detail="Recoverable job not found")
    try:
        return resolve_delivery(db, job.draft_id, **data.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
