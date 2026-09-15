from pathlib import Path
from typing import List, Optional, Union
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.workflow_schemas import DraftInput, DraftListResponse, DraftResponse, DraftUpdate, PublishDraftInput
from app.db import models
from app.db.session import get_db
from app.services.content_draft_service import ContentDraftService, DraftConflictError
from app.services.workflow_job_service import WorkflowJobService
from app.services.wordpress_publishing_service import WordPressPublishingService
from app.integrations.wordpress.destination import ALLOWED_IMAGE_MIME, MAX_IMAGE_BYTES, AmbiguousWordPressResult, validate_image_signature
from app.services.account_service import fetch_wp_categories


router = APIRouter(prefix="/content-drafts", tags=["content drafts"])


@router.get("", response_model=Union[List[DraftResponse], DraftListResponse])
def list_drafts(kind: Optional[str] = None, pipeline_id: Optional[str] = None, page: Optional[int] = None, page_size: int = 20, db: Session = Depends(get_db)):
    service = ContentDraftService(db)
    if page is None:
        return service.list(kind=kind, pipeline_id=pipeline_id)
    return service.list_page(kind=kind, pipeline_id=pipeline_id, page=page, page_size=page_size)


@router.post("", response_model=DraftResponse)
def create_draft(data: DraftInput, db: Session = Depends(get_db)):
    if data.kind != "manual":
        raise HTTPException(status_code=400, detail="Only manual drafts can be created directly")
    try:
        return ContentDraftService(db).create(data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{draft_id}", response_model=DraftResponse)
def get_draft(draft_id: str, db: Session = Depends(get_db)):
    draft = ContentDraftService(db).get(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    return draft


@router.get("/{draft_id}/wp-categories")
def get_draft_categories(draft_id: str, db: Session = Depends(get_db)):
    draft = ContentDraftService(db).get(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    account_id = draft.wp_account_id
    if not account_id and draft.pipeline_id:
        pipeline = db.query(models.Pipeline).filter(models.Pipeline.id == draft.pipeline_id).first()
        account_id = (pipeline.step_accounts or {}).get("wp") if pipeline else None
    account = db.query(models.Account).filter(models.Account.id == account_id, models.Account.type == "wp").first()
    if not account:
        raise HTTPException(status_code=400, detail="WordPress account is unavailable")
    try:
        return fetch_wp_categories(account.config or {})
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to fetch WordPress categories: {exc}") from exc


@router.put("/{draft_id}", response_model=DraftResponse)
def update_draft(draft_id: str, data: DraftUpdate, db: Session = Depends(get_db)):
    try:
        draft = ContentDraftService(db).update(draft_id, data)
    except DraftConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    return draft


@router.delete("/{draft_id}")
def delete_draft(draft_id: str, db: Session = Depends(get_db)):
    try:
        deleted = ContentDraftService(db).delete(draft_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="Draft not found")
    return {"status": "ok"}


@router.post("/{draft_id}/image", response_model=DraftResponse)
async def upload_draft_image(draft_id: str, image: UploadFile = File(...), db: Session = Depends(get_db)):
    draft = ContentDraftService(db).get(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    if image.content_type not in ALLOWED_IMAGE_MIME:
        raise HTTPException(status_code=400, detail="Image must be JPEG, PNG, WebP, or GIF")
    suffix = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/gif": ".gif",
    }[image.content_type]
    upload_dir = Path("var/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)
    target = upload_dir / f"{uuid4()}{suffix}"
    size = 0
    header = b""
    try:
        with target.open("wb") as handle:
            while chunk := await image.read(64 * 1024):
                size += len(chunk)
                if len(header) < 16:
                    header = (header + chunk)[:16]
                if size > MAX_IMAGE_BYTES:
                    raise ValueError("Image exceeds the 10 MiB limit")
                handle.write(chunk)
        validate_image_signature(header, image.content_type)
    except Exception as exc:
        target.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    previous = draft.image_source if draft.image_kind == "upload" else None
    draft.image_kind = "upload"
    draft.image_source = str(target)
    draft.version += 1
    db.commit()
    db.refresh(draft)
    if previous:
        Path(previous).unlink(missing_ok=True)
    return draft


@router.post("/{draft_id}/publish", response_model=DraftResponse)
def publish_draft(draft_id: str, data: PublishDraftInput, db: Session = Depends(get_db)):
    draft = ContentDraftService(db).get(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    workflow_type = {
        "manual": "wp_publish",
        "rewrite": "rewrite",
        "generated": "generate_story",
    }[draft.kind]
    job = WorkflowJobService(db).create(draft.pipeline_id, workflow_type, draft_id=draft.id)
    jobs = WorkflowJobService(db)
    jobs.progress(job.id, "Publish to WordPress", 20)
    try:
        published = WordPressPublishingService(db).publish(draft_id, confirmed=data.confirmed)
    except AmbiguousWordPressResult as exc:
        jobs.fail(job.id, exc)
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        jobs.fail(job.id, exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        jobs.fail(job.id, exc)
        raise HTTPException(status_code=502, detail=f"WordPress publication failed: {exc}") from exc
    jobs.complete(job.id, {"wp_post_id": published.wp_post_id, "wp_url": published.wp_url, "wp_status": published.wp_status})
    return published
