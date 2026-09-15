from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api import schemas
from app.services.job_service import JobService
from app.db.session import get_db


router = APIRouter()


@router.get("/jobs", response_model=schemas.JobPageResponse)
def get_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    workflow_type: Optional[str] = None,
    status_group: Optional[str] = Query(None, pattern="^(active|history)$"),
    db: Session = Depends(get_db),
):
    return JobService(db).list_jobs(page=page, page_size=page_size, workflow_type=workflow_type, status_group=status_group)


@router.get("/jobs/{id}", response_model=schemas.JobResponse)
def get_job(id: str, db: Session = Depends(get_db)):
    job = JobService(db).get_job(id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/jobs/{id}/sync")
def sync_job_status(id: str, db: Session = Depends(get_db)):
    result = JobService(db).sync_job_status(id)
    if result is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return result


@router.post("/jobs/{id}/cancel")
async def cancel_job(id: str, db: Session = Depends(get_db)):
    result = await JobService(db).cancel_job(id)
    if result is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if result.get("status") == "not_cancelled":
        raise HTTPException(status_code=400, detail=f"Job is already {result.get('current_status')}")
    return result
