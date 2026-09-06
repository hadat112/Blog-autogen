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
    profile = db.query(models.Pipeline).filter(
        models.Pipeline.id == data.profile_id,
        models.Pipeline.type == "generate_story",
        models.Pipeline.is_active.is_(True),
    ).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Active Generate Story profile not found")
    draft = models.ContentDraft(
        kind="generated",
        pipeline_id=profile.id,
        language=profile.language,
        category_id=(profile.settings or {}).get("wp_category_id"),
        state="generating",
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)
    job = WorkflowJobService(db).create(profile.id, "generate_story", draft.id)

    async def operation():
        await asyncio.to_thread(GenerateStoryWorkflowService.execute, job.id, draft.id)

    workflow_runner.start(job.id, operation)
    return {"job_id": job.id, "draft_id": draft.id, "status": job.status}
