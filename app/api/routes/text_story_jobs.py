"""Start, inspect and retry text story composition."""

import asyncio

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.workflow_schemas import TextStoryJobInput, WorkflowJobCreated
from app.db import models
from app.db.session import get_db
from app.domain.text_story_prompts import PROMPT_VERSION
from app.domain.workflow_runner import workflow_runner
from app.services.text_story_workflow_service import TextStoryWorkflowService
from app.services.workflow_job_service import WorkflowJobService


router = APIRouter(prefix="/text-story-jobs", tags=["text story"])
STAGES = ("rewrite", "title", "image_prompt", "enhance")
_retry_lock = asyncio.Lock()


def _check_pipeline(db, pipeline_id, source_text=""):
    pipeline = db.query(models.Pipeline).filter_by(id=pipeline_id, is_active=True).first()
    if not pipeline:
        raise HTTPException(404, "Active pipeline not found")
    if not (pipeline.language or "").strip():
        raise HTTPException(400, "Selected pipeline has no target language")
    for role, label in (("ai", "AI"), ("wp", "WordPress")):
        account_id = (pipeline.step_accounts or {}).get(role)
        account = db.get(models.Account, account_id) if account_id else None
        if not account or account.type != role:
            raise HTTPException(400, f"Selected pipeline has no {label} account")
        if role == "ai":
            config = account.config or {}
            context = config.get("context_length")
            output = config.get("max_output_tokens")
            if output and int(output) < 4500:
                raise HTTPException(400, "AI output limit cannot fit the required continuation")
            if context and len(source_text.split()) + 4500 > int(context):
                raise HTTPException(400, "Source story exceeds the configured AI context capacity")
    return pipeline


def _schedule(job_id, draft_id):
    async def operation():
        await asyncio.to_thread(TextStoryWorkflowService.execute, job_id, draft_id)
    workflow_runner.start(job_id, operation)


@router.post("", response_model=WorkflowJobCreated)
async def start_text_story(data: TextStoryJobInput, db: Session = Depends(get_db)):
    source = data.source_text.strip()
    pipeline = _check_pipeline(db, data.pipeline_id, source)
    draft = models.ContentDraft(
        kind="text_story", pipeline_id=pipeline.id, language=pipeline.language,
        wp_account_id=(pipeline.step_accounts or {}).get("wp"),
        category_id=(pipeline.settings or {}).get("wp_category_id"),
        wp_status="draft", state="generating",
    )
    db.add(draft)
    db.flush()
    db.add(models.TextStoryComposition(
        draft_id=draft.id, source_text=source, prompt_version=PROMPT_VERSION,
        stage_status=dict.fromkeys(STAGES, "pending"),
    ))
    db.commit()
    job = WorkflowJobService(db).create(pipeline.id, "text_story", draft.id)
    _schedule(job.id, draft.id)
    return {"job_id": job.id, "draft_id": draft.id, "status": job.status}


@router.get("/{draft_id}/artifacts")
def get_artifacts(draft_id: str, db: Session = Depends(get_db)):
    item = db.query(models.TextStoryComposition).filter_by(draft_id=draft_id).first()
    if not item:
        raise HTTPException(404, "Text story artifacts not found")
    return {"source_text": item.source_text, "rewrite_text": item.rewrite_text,
            "continuation_text": item.continuation_text, "image_prompt": item.image_prompt,
            "prompt_version": item.prompt_version, "stage_status": item.stage_status}


@router.post("/{draft_id}/retry", response_model=WorkflowJobCreated)
async def retry_text_story(draft_id: str, db: Session = Depends(get_db)):
    async with _retry_lock:
        draft = db.get(models.ContentDraft, draft_id)
        item = db.query(models.TextStoryComposition).filter_by(draft_id=draft_id).first()
        if not draft or draft.kind != "text_story" or not item:
            raise HTTPException(404, "Text story draft not found")
        active = db.query(models.Job).filter(
            models.Job.draft_id == draft_id, models.Job.workflow_type == "text_story",
            models.Job.status.in_(("queued", "running")),
        ).first()
        if active:
            raise HTTPException(409, "Text story generation is already active")
        if draft.state != "generation_failed":
            raise HTTPException(409, "Only a failed text story can be retried")
        _check_pipeline(db, draft.pipeline_id, item.source_text)
        draft.state, draft.error = "generating", None
        db.commit()
        job = WorkflowJobService(db).create(draft.pipeline_id, "text_story", draft.id)
        _schedule(job.id, draft.id)
        return {"job_id": job.id, "draft_id": draft.id, "status": job.status}
