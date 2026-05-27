from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from apps.api import schemas
from application.job_service import JobService
from infrastructure.db.session import get_db


router = APIRouter()


@router.get("/jobs", response_model=List[schemas.JobResponse])
def get_jobs(limit: int = 20, db: Session = Depends(get_db)):
    return JobService(db).list_jobs(limit)


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
