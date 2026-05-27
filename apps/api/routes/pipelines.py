from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from apps.api import schemas
from application.pipeline_service import PipelineService
from infrastructure.db.session import get_db


router = APIRouter()


@router.get("/pipelines", response_model=List[schemas.PipelineResponse])
def get_pipelines(db: Session = Depends(get_db)):
    return PipelineService(db).list_pipelines()


@router.get("/pipelines/{id}", response_model=schemas.PipelineResponse)
def get_pipeline(id: str, db: Session = Depends(get_db)):
    pipeline = PipelineService(db).get_pipeline(id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return pipeline


@router.post("/pipelines", response_model=schemas.PipelineResponse)
def create_pipeline(pipeline: schemas.PipelineCreate, db: Session = Depends(get_db)):
    return PipelineService(db).create_pipeline(pipeline)


@router.put("/pipelines/{id}", response_model=schemas.PipelineResponse)
def update_pipeline(id: str, pipeline: schemas.PipelineCreate, db: Session = Depends(get_db)):
    updated = PipelineService(db).update_pipeline(id, pipeline)
    if not updated:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return updated


@router.delete("/pipelines/{id}")
def delete_pipeline(id: str, db: Session = Depends(get_db)):
    deleted = PipelineService(db).delete_pipeline(id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return {"status": "ok"}


@router.post("/pipelines/{id}/run")
async def run_pipeline(id: str, prompt_data: Optional[schemas.QuickRunInput] = None, db: Session = Depends(get_db)):
    service = PipelineService(db)
    try:
        job_id = await service.start_pipeline_run(id, prompt_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not job_id:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return {"job_id": job_id, "status": "queued"}
