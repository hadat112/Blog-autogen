from fastapi.middleware.cors import CORSMiddleware
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

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "ok"}

# Account CRUD Endpoints

@app.post("/accounts/test")
def test_account(test_data: dict, db: Session = Depends(get_db)):
    account_id = test_data.get("id")
    account_type = test_data.get("type")
    config = test_data.get("config")

    # If ID provided, load from DB
    if account_id and not account_type:
        account = db.query(models.Account).filter(models.Account.id == account_id).first()
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        account_type = account.type
        config = account.config

    if not account_type or config is None:
        raise HTTPException(status_code=400, detail="Missing account type or configuration")

    success, message = perform_connection_test(account_type, config)
    if not success:
        raise HTTPException(status_code=400, detail=f"Verification failed: {message}")
    return {"status": "ok", "message": message}

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

def perform_connection_test(account_type: str, config: dict):
    try:
        if account_type == "wp":
            url = f"{config.get('url', '').rstrip('/')}/wp-json/wp/v2/users/me"
            wp_password = config.get("password") or config.get("app_password")
            auth = HTTPBasicAuth(config.get("username"), wp_password)
            resp = requests.get(url, auth=auth, timeout=10)
            resp.raise_for_status()
        elif account_type == "fb":
            page_id = config.get("page_id")
            access_token = config.get("access_token")
            graph_version = config.get("graph_version", "v23.0")
            url = f"https://graph.facebook.com/{graph_version}/{page_id}"
            params = {"access_token": access_token}
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
        elif account_type == "ai":
            base_url = config.get("base_url", "http://localhost:20128/v1").rstrip('/')
            url = f"{base_url}/models"
            headers = {"Authorization": f"Bearer {config.get('api_key')}"}
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
        elif account_type == "gs":
            # Simple check if credentials file exists
            import os
            cred_path = config.get("credentials_path") or config.get("credentials_json") or "credentials.json"
            if not os.path.exists(cred_path):
                raise Exception(f"Credentials file not found at: {cred_path}")
            # Try to initialize gspread if possible to really verify
            try:
                import gspread
                gc = gspread.service_account(filename=cred_path)
                sh_id = config.get("spreadsheet_id") or config.get("sheet_id")
                if sh_id:
                    gc.open_by_key(sh_id)
            except ImportError:
                pass # gspread not installed, skip deep check
            except Exception as ge:
                raise Exception(f"Google Sheets verification failed: {str(ge)}")

        elif account_type == "tg":
            bot_token = config.get("bot_token")
            url = f"https://api.telegram.org/bot{bot_token}/getMe"
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
        else:
            raise Exception(f"Unsupported account type: {account_type}")
        return True, "Credentials verified"
    except Exception as e:
        return False, str(e)

@app.post("/accounts/wp-categories")
def get_wp_categories(config: dict):
    url = config.get("url", "").rstrip('/')
    if not url:
        raise HTTPException(status_code=400, detail="WordPress URL is required")

    username = config.get("username")
    password = config.get("password") or config.get("app_password")

    try:
        api_url = f"{url}/wp-json/wp/v2/categories"
        params = {"per_page": 100}
        auth = HTTPBasicAuth(username, password) if username and password else None

        resp = requests.get(api_url, auth=auth, params=params, timeout=15)
        resp.raise_for_status()

        categories = []
        for cat in resp.json():
            categories.append({
                "id": cat["id"],
                "name": cat["name"],
                "count": cat["count"]
            })
        return categories
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch categories: {str(e)}")

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
    results = db.query(models.Job, models.Pipeline.name).join(
        models.Pipeline, models.Job.pipeline_id == models.Pipeline.id
    ).order_by(models.Job.start_time.desc()).limit(limit).all()

    jobs = []
    for job, pipeline_name in results:
        job.pipeline_name = pipeline_name
        jobs.append(job)
    return jobs

@app.get("/jobs/{id}", response_model=schemas.JobResponse)
def get_job(id: str, db: Session = Depends(get_db)):
    result = db.query(models.Job, models.Pipeline.name).join(
        models.Pipeline, models.Job.pipeline_id == models.Pipeline.id
    ).filter(models.Job.id == id).first()

    if not result:
        raise HTTPException(status_code=404, detail="Job not found")

    job, pipeline_name = result
    job.pipeline_name = pipeline_name
    return job

@app.post("/jobs/{id}/sync")
def sync_job_status(id: str, db: Session = Depends(get_db)):
    job = db.query(models.Job).filter(models.Job.id == id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # If job is running but looks finished (progress 100 and has logs), mark it.
    # This is a safety valve for crashes at the very end of a task.
    if job.status == "running":
        logs = list(job.logs or [])
        if job.progress == 100 and len(logs) > 0:
            # Check if last log was a completion event
            last_log = logs[-1]
            if "Completed" in last_log.get("step_name", "") or last_log.get("progress") == 100:
                job.status = "success"
                job.end_time = datetime.utcnow()
                db.commit()
                return {"status": "updated", "new_status": "success"}

    return {"status": "checked", "current_status": job.status}
