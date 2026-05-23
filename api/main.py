from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
import requests
from requests.auth import HTTPBasicAuth

from core.db import engine, Base, get_db
from core import models
from api import schemas
from core.worker_manager import worker_manager

# Initialize database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Story Autogen API")

@app.get("/")
def read_root():
    return {"status": "ok"}

# Account CRUD Endpoints

@app.get("/accounts", response_model=List[schemas.AccountResponse])
def get_accounts(db: Session = Depends(get_db)):
    return db.query(models.Account).all()

@app.get("/accounts/{id}", response_model=schemas.AccountResponse)
def get_account(id: str, db: Session = Depends(get_db)):
    account = db.query(models.Account).filter(models.Account.id == id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account

@app.post("/accounts", response_model=schemas.AccountResponse)
def create_account(account: schemas.AccountCreate, db: Session = Depends(get_db)):
    db_account = models.Account(
        name=account.name,
        type=account.type,
        config=account.config
    )
    db.add(db_account)
    db.commit()
    db.refresh(db_account)
    return db_account

@app.put("/accounts/{id}", response_model=schemas.AccountResponse)
def update_account(id: str, account: schemas.AccountCreate, db: Session = Depends(get_db)):
    db_account = db.query(models.Account).filter(models.Account.id == id).first()
    if not db_account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    db_account.name = account.name
    db_account.type = account.type
    db_account.config = account.config
    
    db.commit()
    db.refresh(db_account)
    return db_account

@app.delete("/accounts/{id}")
def delete_account(id: str, db: Session = Depends(get_db)):
    db_account = db.query(models.Account).filter(models.Account.id == id).first()
    if not db_account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    db.delete(db_account)
    db.commit()
    return {"status": "ok"}

@app.post("/accounts/{id}/test")
def test_account(id: str, db: Session = Depends(get_db)):
    account = db.query(models.Account).filter(models.Account.id == id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    config = account.config
    try:
        if account.type == "wp":
            url = f"{config.get('url', '').rstrip('/')}/wp-json/wp/v2/users/me"
            auth = HTTPBasicAuth(config.get("username"), config.get("app_password"))
            resp = requests.get(url, auth=auth, timeout=10)
            resp.raise_for_status()
        elif account.type == "fb":
            page_id = config.get("page_id")
            access_token = config.get("access_token")
            graph_version = config.get("graph_version", "v23.0")
            url = f"https://graph.facebook.com/{graph_version}/{page_id}"
            params = {"access_token": access_token}
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
        elif account.type == "ai":
            base_url = config.get("base_url", "http://localhost:20128/v1").rstrip('/')
            url = f"{base_url}/models"
            headers = {"Authorization": f"Bearer {config.get('api_key')}"}
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported account type: {account.type}")
        
        return {"status": "ok", "message": "Credentials verified"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Verification failed: {str(e)}")

# Pipeline CRUD Endpoints

@app.get("/pipelines", response_model=List[schemas.PipelineResponse])
def get_pipelines(db: Session = Depends(get_db)):
    return db.query(models.Pipeline).all()

@app.get("/pipelines/{id}", response_model=schemas.PipelineResponse)
def get_pipeline(id: str, db: Session = Depends(get_db)):
    pipeline = db.query(models.Pipeline).filter(models.Pipeline.id == id).first()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return pipeline

@app.post("/pipelines", response_model=schemas.PipelineResponse)
def create_pipeline(pipeline: schemas.PipelineCreate, db: Session = Depends(get_db)):
    db_pipeline = models.Pipeline(
        name=pipeline.name,
        type=pipeline.type,
        language=pipeline.language,
        step_accounts=pipeline.step_accounts,
        schedule=pipeline.schedule,
        is_active=pipeline.is_active
    )
    db.add(db_pipeline)
    db.commit()
    db.refresh(db_pipeline)
    return db_pipeline

@app.put("/pipelines/{id}", response_model=schemas.PipelineResponse)
def update_pipeline(id: str, pipeline: schemas.PipelineCreate, db: Session = Depends(get_db)):
    db_pipeline = db.query(models.Pipeline).filter(models.Pipeline.id == id).first()
    if not db_pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    
    db_pipeline.name = pipeline.name
    db_pipeline.type = pipeline.type
    db_pipeline.language = pipeline.language
    db_pipeline.step_accounts = pipeline.step_accounts
    db_pipeline.schedule = pipeline.schedule
    db_pipeline.is_active = pipeline.is_active
    
    db.commit()
    db.refresh(db_pipeline)
    return db_pipeline

@app.delete("/pipelines/{id}")
def delete_pipeline(id: str, db: Session = Depends(get_db)):
    db_pipeline = db.query(models.Pipeline).filter(models.Pipeline.id == id).first()
    if not db_pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    
    db.delete(db_pipeline)
    db.commit()
    return {"status": "ok"}

# Execution Endpoints

@app.post("/pipelines/{id}/run")
async def run_pipeline(id: str, prompt_data: Optional[schemas.QuickRunInput] = None, db: Session = Depends(get_db)):
    pipeline = db.query(models.Pipeline).filter(models.Pipeline.id == id).first()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    
    try:
        job_id = await worker_manager.start_pipeline_run(
            pipeline_id=id,
            db=db,
            prompts_file=prompt_data.prompts_file if prompt_data and prompt_data.prompts_file else "prompts.txt",
            prompt=prompt_data.prompt if prompt_data else None
        )
        return {"job_id": job_id, "status": "queued"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/jobs", response_model=List[schemas.JobResponse])
def get_jobs(limit: int = 20, db: Session = Depends(get_db)):
    return db.query(models.Job).order_by(models.Job.start_time.desc()).limit(limit).all()

@app.get("/jobs/{id}", response_model=schemas.JobResponse)
def get_job(id: str, db: Session = Depends(get_db)):
    job = db.query(models.Job).filter(models.Job.id == id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
