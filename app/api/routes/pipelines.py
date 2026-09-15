from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api import schemas
from app.api.workflow_schemas import CategoryResponse
from app.db import models
from app.services.account_service import fetch_wp_categories
from app.services.pipeline_service import PipelineService
from app.db.session import get_db


router = APIRouter()


@router.get("/pipelines", response_model=List[schemas.PipelineResponse])
def get_pipelines(include_workflows: bool = False, db: Session = Depends(get_db)):
    return PipelineService(db).list_pipelines(include_workflows=include_workflows)


@router.get("/pipelines/{id}", response_model=schemas.PipelineResponse)
def get_pipeline(id: str, db: Session = Depends(get_db)):
    pipeline = PipelineService(db).get_pipeline(id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return pipeline


@router.get("/pipelines/{id}/wp-categories", response_model=List[CategoryResponse])
def get_pipeline_categories(id: str, db: Session = Depends(get_db)):
    pipeline = db.query(models.Pipeline).filter(models.Pipeline.id == id).first()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    account_id = (pipeline.step_accounts or {}).get("wp")
    account = db.query(models.Account).filter(models.Account.id == account_id, models.Account.type == "wp").first()
    if not account:
        raise HTTPException(status_code=400, detail="WordPress account is unavailable")
    try:
        return fetch_wp_categories(account.config or {})
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to fetch WordPress categories: {exc}") from exc


@router.post("/pipelines", response_model=schemas.PipelineResponse)
def create_pipeline(pipeline: schemas.PipelineCreate, db: Session = Depends(get_db)):
    try:
        return PipelineService(db).create_pipeline(pipeline)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/pipelines/{id}", response_model=schemas.PipelineResponse)
def update_pipeline(id: str, pipeline: schemas.PipelineCreate, db: Session = Depends(get_db)):
    try:
        updated = PipelineService(db).update_pipeline(id, pipeline)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
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
    pipeline = service.get_pipeline(id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    response_status = (
        "running"
        if pipeline.type == "crawl" and not (pipeline.language or "").strip()
        else "queued"
    )
    try:
        job_id = await service.start_pipeline_run(id, prompt_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not job_id:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return {"job_id": job_id, "status": response_status}
