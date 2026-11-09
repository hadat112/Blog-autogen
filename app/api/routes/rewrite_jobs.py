from app.domain.workflow_threads import run_workflow_blocking
import asyncio
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.workflow_schemas import RewriteJobInput, WorkflowJobCreated
from app.db import models
from app.db.session import get_db
from app.domain.workflow_runner import workflow_runner
from app.services.article_service import normalize_source_url
from app.services.article_workflow_service import ArticleWorkflowService
from app.services.workflow_job_service import WorkflowJobService


router = APIRouter(prefix="/rewrite-jobs", tags=["rewrite"])


@router.post("", response_model=WorkflowJobCreated)
async def start_rewrite(data: RewriteJobInput, db: Session = Depends(get_db)):
    pipeline = db.query(models.Pipeline).filter(models.Pipeline.id == data.pipeline_id, models.Pipeline.is_active.is_(True)).first()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Active pipeline not found")
    if (pipeline.language or "").strip() and not (pipeline.step_accounts or {}).get("ai"):
        raise HTTPException(status_code=400, detail="Selected pipeline has no AI account")
    if not (pipeline.step_accounts or {}).get("wp"):
        raise HTTPException(status_code=400, detail="Selected pipeline has no WordPress account")
    previous_job = None
    if data.rerun_from_job_id:
        previous_job = db.query(models.Job).filter(
            models.Job.id == data.rerun_from_job_id,
            models.Job.pipeline_id == pipeline.id,
            models.Job.workflow_type == "rewrite",
            models.Job.status == "failed",
        ).first()
        if not previous_job:
            raise HTTPException(status_code=400, detail="Only a failed V2 job can be retried")
        if previous_job.rerun_job_id:
            raise HTTPException(status_code=400, detail="This V2 job has already been retried")
    try:
        source_url = normalize_source_url(data.source_url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    draft = db.get(models.ContentDraft, previous_job.draft_id) if previous_job and previous_job.draft_id else None
    if draft:
        if normalize_source_url(draft.source_url) != source_url:
            raise HTTPException(status_code=400, detail="Resume must use the original source URL; start a fresh run for a different source")
        active = db.query(models.Job.id).filter(models.Job.draft_id == draft.id, models.Job.status.in_(["queued", "running"])).first()
        if active:
            raise HTTPException(status_code=409, detail="This draft already has an active attempt")
    else:
        draft = models.ContentDraft(
            kind="rewrite",
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
    job = WorkflowJobService(db).create(pipeline.id, "rewrite", draft.id, input_text=source_url)
    if previous_job:
        claimed = db.query(models.Job).filter(models.Job.id == previous_job.id,
            models.Job.rerun_job_id.is_(None), models.Job.status.in_(["failed", "cancelled"])
        ).update({"rerun_at": datetime.utcnow(), "rerun_job_id": job.id}, synchronize_session=False)
        if claimed != 1:
            db.delete(job)
            db.commit()
            raise HTTPException(status_code=409, detail="This job already has a retry")
        db.commit()

    async def operation():
        await run_workflow_blocking(
            ArticleWorkflowService.execute,
            job.id,
            draft.id,
            mode="v2",
            use_proxy=data.use_proxy,
            use_enrichment=data.use_enrichment,
        )

    workflow_runner.start(job.id, operation)
    return {"job_id": job.id, "draft_id": draft.id, "status": job.status}
