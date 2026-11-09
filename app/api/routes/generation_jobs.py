from app.domain.workflow_threads import run_workflow_blocking
import asyncio

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.workflow_schemas import GenerationJobInput, WorkflowJobCreated
from app.db import models
from app.db.session import get_db
from app.domain.workflow_runner import workflow_runner
from app.services.generate_story_workflow_service import GenerateStoryWorkflowService
from app.services.workflow_job_service import WorkflowJobService


router = APIRouter(prefix="/generation-jobs", tags=["generate story"])


@router.post("", response_model=WorkflowJobCreated)
async def start_generation(data: GenerationJobInput, db: Session = Depends(get_db)):
    pipeline = db.query(models.Pipeline).filter(models.Pipeline.id == data.pipeline_id, models.Pipeline.is_active.is_(True)).first()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Active pipeline not found")
    if not (pipeline.step_accounts or {}).get("ai"):
        raise HTTPException(status_code=400, detail="Selected pipeline has no AI account")
    draft = models.ContentDraft(
        kind="generated",
        pipeline_id=pipeline.id,
        language=pipeline.language,
        category_id=(pipeline.settings or {}).get("wp_category_id"),
        state="generating",
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)
    job = WorkflowJobService(db).create(pipeline.id, "generate_story", draft.id)

    async def operation():
        await run_workflow_blocking(GenerateStoryWorkflowService.execute, job.id, draft.id)

    workflow_runner.start(job.id, operation)
    return {"job_id": job.id, "draft_id": draft.id, "status": job.status}
