import asyncio
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from core.models import Job, Pipeline
from core.account_resolver import resolve_accounts_for_pipeline
from core.orchestrator import Orchestrator
from core.db import SessionLocal

logger = logging.getLogger(__name__)

class WorkerManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(WorkerManager, cls).__new__(cls)
            cls._instance.active_jobs = {}
        return cls._instance

    async def start_pipeline_run(self, pipeline_id: str, db: Session, prompts_file: str = "prompts.txt", prompt: str = None):
        pipeline = db.query(Pipeline).filter(Pipeline.id == pipeline_id).first()
        if not pipeline:
            raise ValueError(f"Pipeline {pipeline_id} not found")

        # 1. Setup Job record
        job = Job(
            pipeline_id=pipeline_id,
            status="running",
            start_time=datetime.utcnow(),
            progress=0,
            logs=[]
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        job_id = job.id

        # 2. Resolve Accounts
        account_configs = resolve_accounts_for_pipeline(db, pipeline.step_accounts)

        # 3. Define progress_callback
        def progress_callback(step_index, step_name, step_progress, detail=""):
            with SessionLocal() as update_db:
                db_job = update_db.query(Job).filter(Job.id == job_id).first()
                if db_job:
                    db_job.current_step = step_name
                    db_job.progress = step_progress
                    
                    logs = list(db_job.logs or [])
                    logs.append({
                        "timestamp": datetime.utcnow().isoformat(),
                        "step_index": step_index,
                        "step_name": step_name,
                        "progress": step_progress,
                        "detail": detail
                    })
                    db_job.logs = logs
                    update_db.commit()

        # 4. Initialize Orchestrator
        orchestrator = Orchestrator(
            ai_config=account_configs.get("ai"),
            wp_config=account_configs.get("wp"),
            fb_config=account_configs.get("fb"),
            gs_config=account_configs.get("gs"),
            tg_config=account_configs.get("tg"),
            language=pipeline.language,
            progress_callback=progress_callback
        )

        # 5. Run in background
        asyncio.create_task(self._run_job_task(job_id, orchestrator, prompts_file, prompt))
        
        return job_id

    async def _run_job_task(self, job_id: str, orchestrator: Orchestrator, prompts_file: str, prompt: str = None):
        try:
            if prompt:
                # Quick run for a single prompt
                await asyncio.to_thread(orchestrator.process_prompt, prompt)
            else:
                # Full run from prompts file
                await asyncio.to_thread(orchestrator.run, prompts_file)
            
            with SessionLocal() as db:
                job = db.query(Job).filter(Job.id == job_id).first()
                if job:
                    job.status = "success"
                    job.progress = 100
                    job.end_time = datetime.utcnow()
                    db.commit()
        except Exception as e:
            logger.exception(f"Job {job_id} failed")
            with SessionLocal() as db:
                job = db.query(Job).filter(Job.id == job_id).first()
                if job:
                    job.status = "failed"
                    logs = list(job.logs or [])
                    logs.append({
                        "timestamp": datetime.utcnow().isoformat(),
                        "event": "error",
                        "detail": str(e)
                    })
                    job.logs = logs
                    job.end_time = datetime.utcnow()
                    db.commit()

worker_manager = WorkerManager()
