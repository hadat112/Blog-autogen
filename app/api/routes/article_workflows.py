import asyncio
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.workflow_schemas import ArticleWorkflowRunInput, WorkflowJobCreated
from app.db import models
from app.db.session import get_db
from app.domain.workflow_runner import workflow_runner
from app.services.article_service import normalize_source_url
from app.services.article_workflow_service import ArticleWorkflowService
from app.services.workflow_job_service import WorkflowJobService

router = APIRouter(prefix="/article-workflows", tags=["article_workflows"])


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
    if not (pipeline.step_accounts or {}).get("ai"):
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

    job = WorkflowJobService(db).create(pipeline.id, f"article_{mode}", draft.id, input_text=source_url)
    if previous_job:
        previous_job.rerun_at = datetime.utcnow()
        previous_job.rerun_job_id = job.id
        db.commit()

    async def operation():
        await asyncio.to_thread(
            ArticleWorkflowService.execute,
            job.id,
            draft.id,
            mode=mode,
            use_proxy=data.use_proxy,
        )

    workflow_runner.start(job.id, operation)
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
