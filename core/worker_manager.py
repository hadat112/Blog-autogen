import asyncio
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from infrastructure.db.models import Job, Pipeline
from core.account_resolver import resolve_accounts_for_pipeline
from core.orchestrator import Orchestrator
from infrastructure.db.session import SessionLocal

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
        initial_logs = []
        if prompt:
            initial_logs.append({
                "timestamp": datetime.utcnow().isoformat(),
                "step_name": "Input",
                "detail": prompt,
                "event": "input",
                "url": prompt if isinstance(prompt, str) and prompt.startswith("http") else None,
            })

        job = Job(
            pipeline_id=pipeline_id,
            status="running",
            start_time=datetime.utcnow(),
            progress=0,
            logs=initial_logs
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        job_id = job.id

        # 2. Resolve Accounts
        account_configs = resolve_accounts_for_pipeline(db, pipeline.step_accounts)

        # 3. Auto-detect disabled steps based on missing accounts
        disabled_steps = []
        if not account_configs.get("ai"):
            disabled_steps.extend(["ai_text_generation", "ai_image_generation"])
        if not account_configs.get("wp"):
            disabled_steps.append("wordpress_publish")
        if not account_configs.get("fb"):
            disabled_steps.append("facebook_publish")
        if not account_configs.get("gs"):
            disabled_steps.append("google_sheets_log")
        if not account_configs.get("tg"):
            disabled_steps.append("telegram_notify")

        # 4. Define progress_callback
        def progress_callback(step_index, step_name, step_progress, detail="", task_id=None):
            with SessionLocal() as update_db:
                db_job = update_db.query(Job).filter(Job.id == job_id).first()
                if db_job:
                    # Update global progress/step if it's not a multi-task run,
                    # or update based on the latest task update.
                    db_job.current_step = step_name
                    db_job.progress = step_progress

                    logs = list(db_job.logs or [])
                    logs.append({
                        "timestamp": datetime.utcnow().isoformat(),
                        "task_id": task_id,
                        "step_index": step_index,
                        "step_name": step_name,
                        "progress": step_progress,
                        "detail": detail,
                        "event": "info" if "error" not in step_name.lower() else "failed"
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
            disabled_steps=disabled_steps,
            progress_callback=progress_callback
        )

        # 5. Run in background
        asyncio.create_task(self._run_job_task(job_id, orchestrator, pipeline.type, prompts_file, prompt))

        return job_id

    async def _run_job_task(self, job_id: str, orchestrator: Orchestrator, pipeline_type: str, prompts_file: str, prompt: str = None):
        final_status = "success"
        try:
            if prompt:
                # Quick run for a single prompt/url
                if pipeline_type == "crawl" or (isinstance(prompt, str) and prompt.startswith("http")):
                    result = await asyncio.to_thread(orchestrator.process_crawl, prompt)
                else:
                    result = await asyncio.to_thread(orchestrator.process_prompt, prompt)

                res_status = result.get("status", "info")
                if res_status == "error":
                    final_status = "failed"

                self._add_log_event(job_id, "Completed", f"Processed {pipeline_type}: {prompt[:50]}...", res_status)
            else:
                # Full run from prompts file
                results = await asyncio.to_thread(orchestrator.run, prompts_file)

                # Check if all items failed
                if results and all(r.get("status") == "error" for r in results):
                    final_status = "failed"
                elif any(r.get("status") == "error" for r in results):
                    final_status = "partial_success"

                self._add_log_event(job_id, "Completed", f"Processed batch. {len(results)} items handled.", final_status)

            with SessionLocal() as db:
                job = db.query(Job).filter(Job.id == job_id).first()
                if job:
                    job.status = final_status
                    job.progress = 100
                    job.end_time = datetime.utcnow()
                    db.commit()
        except Exception as e:
            logger.exception(f"Job {job_id} failed")
            self._add_log_event(job_id, "Critical Error", str(e), "failed")
            with SessionLocal() as db:
                job = db.query(Job).filter(Job.id == job_id).first()
                if job:
                    job.status = "failed"
                    job.end_time = datetime.utcnow()
                    db.commit()

    def _add_log_event(self, job_id: str, event_name: str, detail: str, status: str = "info"):
        with SessionLocal() as db:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                logs = list(job.logs or [])
                logs.append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "step_name": event_name,
                    "detail": detail,
                    "event": status
                })
                job.logs = logs
                db.commit()

worker_manager = WorkerManager()
