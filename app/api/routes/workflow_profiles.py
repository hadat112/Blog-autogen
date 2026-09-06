from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.workflow_schemas import CategoryResponse, WorkflowProfileInput, WorkflowProfileResponse
from app.db.session import get_db
from app.services.workflow_profile_service import WorkflowProfileService


router = APIRouter(prefix="/workflow-profiles", tags=["workflow profiles"])


@router.get("", response_model=List[WorkflowProfileResponse])
def list_profiles(type: Optional[str] = None, db: Session = Depends(get_db)):
    try:
        return WorkflowProfileService(db).list(type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("", response_model=WorkflowProfileResponse)
def create_profile(data: WorkflowProfileInput, db: Session = Depends(get_db)):
    try:
        return WorkflowProfileService(db).create(data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{profile_id}", response_model=WorkflowProfileResponse)
def get_profile(profile_id: str, db: Session = Depends(get_db)):
    profile = WorkflowProfileService(db).get(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Workflow profile not found")
    return profile


@router.put("/{profile_id}", response_model=WorkflowProfileResponse)
def update_profile(profile_id: str, data: WorkflowProfileInput, db: Session = Depends(get_db)):
    try:
        profile = WorkflowProfileService(db).update(profile_id, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not profile:
        raise HTTPException(status_code=404, detail="Workflow profile not found")
    return profile


@router.delete("/{profile_id}")
def delete_profile(profile_id: str, db: Session = Depends(get_db)):
    try:
        deleted = WorkflowProfileService(db).delete(profile_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="Workflow profile not found")
    return {"status": "ok"}


@router.get("/{profile_id}/wp-categories", response_model=List[CategoryResponse])
def get_categories(profile_id: str, db: Session = Depends(get_db)):
    try:
        categories = WorkflowProfileService(db).categories(profile_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to fetch WordPress categories: {exc}") from exc
    if categories is None:
        raise HTTPException(status_code=404, detail="Workflow profile not found")
    return categories
