"""Durable, resumable four-request text story composition."""

import time

from app.db import models
from app.db.session import SessionLocal
from app.domain.text_story_prompts import (
    build_enhance_messages, build_image_prompt_messages, build_rewrite_messages,
    build_title_messages,
)
from app.domain.text_story_validation import assemble_story, validate_stage
from app.services.ai_client_factory import create_ai_client
from app.services.workflow_job_service import WorkflowJobService


STAGES = ("rewrite", "title", "image_prompt", "enhance")
STAGE_PROGRESS = {"rewrite": 5, "title": 30, "image_prompt": 45, "enhance": 60}


def check_cancelled(db, job_id):
    db.expire_all()
    job = db.get(models.Job, job_id)
    if not job or job.status == "cancelled":
        raise InterruptedError("Generation cancelled")


def save_stage(db, composition, draft, job, stage, value, result, elapsed):
    if stage == "rewrite":
        composition.rewrite_text = value
    elif stage == "title":
        draft.title = value
    elif stage == "image_prompt":
        composition.image_prompt = value
    elif stage == "enhance":
        composition.continuation_text = value
    composition.stage_status = {**composition.stage_status, stage: "completed"}
    draft.version += 1
    outputs = dict(job.outputs or {})
    outputs[stage] = {
        "model": result.model, "finish_reason": result.finish_reason,
        "usage": result.usage, "elapsed_seconds": round(elapsed, 2),
    }
    job.outputs = outputs
    db.commit()


class TextStoryWorkflowService:
    @staticmethod
    def execute(job_id: str, draft_id: str) -> None:
        with SessionLocal() as db:
            jobs = WorkflowJobService(db)
            draft = db.get(models.ContentDraft, draft_id)
            job = db.get(models.Job, job_id)
            composition = db.query(models.TextStoryComposition).filter_by(draft_id=draft_id).first()
            if not draft or not job or not composition or job.status == "cancelled":
                return
            pipeline = db.get(models.Pipeline, draft.pipeline_id)
            account_id = (pipeline.step_accounts or {}).get("ai") if pipeline else None
            account = db.get(models.Account, account_id) if account_id else None
            if not pipeline or not pipeline.is_active or not account or account.type != "ai":
                draft.state, draft.error = "generation_failed", "Text story pipeline or AI account is unavailable"
                db.commit()
                jobs.fail(job_id, draft.error)
                return
            try:
                ai = create_ai_client(account)
                for stage in STAGES:
                    if composition.stage_status.get(stage) == "completed":
                        continue
                    check_cancelled(db, job_id)
                    jobs.progress(job_id, stage, STAGE_PROGRESS[stage])
                    if stage == "rewrite":
                        messages = build_rewrite_messages(composition.source_text, draft.language)
                    elif stage == "title":
                        messages = build_title_messages(composition.rewrite_text, draft.language)
                    elif stage == "image_prompt":
                        messages = build_image_prompt_messages(composition.rewrite_text, draft.language)
                    else:
                        messages = build_enhance_messages(composition.source_text, composition.rewrite_text, draft.language)
                    started = time.monotonic()
                    result = ai.chat_with_meta(messages)
                    check_cancelled(db, job_id)
                    value = validate_stage(stage, result, composition.rewrite_text)
                    save_stage(db, composition, draft, job, stage, value, result, time.monotonic() - started)
                draft.content, draft.caption = assemble_story(composition.rewrite_text, composition.continuation_text)
                draft.state = "ready_for_review"
                draft.error = None
                draft.version += 1
                db.commit()
                outputs = dict(job.outputs or {})
                outputs["draft_id"] = draft.id
                if len(composition.continuation_text.split()) > 3500:
                    outputs["warnings"] = ["Continuation exceeds 3,500 words; review pacing before publishing"]
                jobs.complete(job_id, outputs)
            except InterruptedError:
                if draft.state == "generating":
                    draft.state, draft.error = "generation_failed", "Generation was cancelled"
                    draft.version += 1
                    db.commit()
            except Exception as exc:
                safe_error = str(exc) if isinstance(exc, ValueError) else "AI request failed; retry this stage"
                stage = job.current_step if job.current_step in STAGES else "rewrite"
                composition.stage_status = {**composition.stage_status, stage: "failed"}
                draft.state, draft.error = "generation_failed", safe_error[:500]
                draft.version += 1
                db.commit()
                jobs.fail(job_id, safe_error)
