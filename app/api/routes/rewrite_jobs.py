import asyncio

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.workflow_schemas import RewriteJobInput, WorkflowJobCreated
from app.db import models
from app.db.session import get_db
from app.domain.workflow_runner import workflow_runner
from app.services.article_service import normalize_source_url
from app.services.rewrite_workflow_service import RewriteWorkflowService
from app.services.workflow_job_service import WorkflowJobService


router = APIRouter(prefix="/rewrite-jobs", tags=["rewrite"])


@router.post("", response_model=WorkflowJobCreated)
async def start_rewrite(data: RewriteJobInput, db: Session = Depends(get_db)):
    profile = db.query(models.Pipeline).filter(
        models.Pipeline.id == data.profile_id,
        models.Pipeline.type == "rewrite",
        models.Pipeline.is_active.is_(True),
    ).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Active Rewrite profile not found")
    try:
        source_url = normalize_source_url(data.source_url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    draft = models.ContentDraft(
        kind="rewrite",
        pipeline_id=profile.id,
        source_url=source_url,
        language=profile.language,
        category_id=(profile.settings or {}).get("wp_category_id"),
        state="generating",
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)
    job = WorkflowJobService(db).create(profile.id, "rewrite", draft.id, input_text=source_url)

    async def operation():
        await asyncio.to_thread(RewriteWorkflowService.execute, job.id, draft.id)

    workflow_runner.start(job.id, operation)
    return {"job_id": job.id, "draft_id": draft.id, "status": job.status}
