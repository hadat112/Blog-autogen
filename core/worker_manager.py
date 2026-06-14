import asyncio
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from core.config_manager import ConfigManager
from infrastructure.db.models import Job, Pipeline
from core.account_resolver import resolve_accounts_for_pipeline
from core.orchestrator import Orchestrator
from infrastructure.db.session import SessionLocal

logger = logging.getLogger(__name__)

MAX_JOB_LOGS = 120


class WorkerManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(WorkerManager, cls).__new__(cls)
            cls._instance.active_jobs = {}
            cls._instance._run_lock = None
            cls._instance._run_lock_loop = None
        return cls._instance

    def _get_run_lock(self):
        loop = asyncio.get_running_loop()
        if self._run_lock is None or self._run_lock_loop is not loop:
            self._run_lock = asyncio.Lock()
            self._run_lock_loop = loop
        return self._run_lock

    async def start_pipeline_run(self, pipeline_id: str, db: Session, prompts_file: str = "prompts.txt", prompt: str = None):
        pipeline = db.query(Pipeline).filter(Pipeline.id == pipeline_id).first()
        if not pipeline:
            raise ValueError(f"Pipeline {pipeline_id} not found")
        # 1. Setup Job record
        input_text = prompt.strip() if isinstance(prompt, str) else None
        input_type = "url" if input_text and input_text.startswith("http") else "prompt" if input_text else None

        run_without_queue = pipeline.type == "crawl" and not (pipeline.language or "").strip()

        job = Job(
            pipeline_id=pipeline_id,
            input_text=input_text,
            input_type=input_type,
            status="running" if run_without_queue else "queued",
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
        app_config = ConfigManager().config
        ai_config = None
        if account_configs.get("ai"):
            ai_config = dict(account_configs["ai"])
            ai_config["translation_mode"] = app_config.get("translation_mode", "sequential")
            ai_config["translation_max_concurrency"] = app_config.get("translation_max_concurrency", 2)
        wp_config = dict(account_configs.get("wp") or {})
        wp_config.pop("category_id", None)
        pipeline_settings = pipeline.settings if isinstance(pipeline.settings, dict) else {}
        wp_category_id = pipeline_settings.get("wp_category_id")
        if wp_category_id:
            wp_config["category_id"] = wp_category_id

        # 3. Auto-detect disabled steps based on missing accounts
        disabled_steps = []
        if not account_configs.get("ai"):
            disabled_steps.extend(["ai_text_generation", "ai_image_generation"])
        if not wp_config:
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
                    if db_job.status == "cancelled":
                        return
                    # Update global progress/step if it's not a multi-task run,
                    # or update based on the latest task update.
                    db_job.current_step = step_name
                    db_job.progress = step_progress

                    event = "failed" if "error" in step_name.lower() else "info"
                    should_log = (
                        event == "failed"
                        or step_progress == 100
                        or (detail and detail != "working" and ("success" in detail.lower() or "error" in detail.lower() or "failed" in detail.lower()))
                    )
                    if should_log:
                        logs = list(db_job.logs or [])
                        logs.append({
                            "timestamp": datetime.utcnow().isoformat(),
                            "task_id": task_id,
                            "step_index": step_index,
                            "step_name": step_name,
                            "progress": step_progress,
                            "detail": "Step completed" if detail == "working" and step_progress == 100 else detail,
                            "event": event
                        })
                        db_job.logs = logs[-MAX_JOB_LOGS:]
                    update_db.commit()

        # 4. Initialize Orchestrator
        orchestrator = Orchestrator(
            ai_config=ai_config,
            wp_config=wp_config or None,
            fb_config=account_configs.get("fb"),
            gs_config=account_configs.get("gs"),
            tg_config=account_configs.get("tg"),
            num_threads=1,
            language=pipeline.language,
            disabled_steps=disabled_steps,
            progress_callback=progress_callback
        )

        # 5. Run in background. Translated/AI jobs use the lock so only one pipeline
        # runs at a time; original repost jobs can run immediately because they skip AI.
        if run_without_queue:
            task = asyncio.create_task(
                self._run_job_task_unqueued(
                    job_id,
                    orchestrator,
                    pipeline.type,
                    prompts_file,
                    prompt,
                )
            )
        else:
            task = asyncio.create_task(
                self._run_job_task(
                    job_id,
                    orchestrator,
                    pipeline.type,
                    prompts_file,
                    prompt,
                )
            )
        self.active_jobs[job_id] = task

        return job_id

    async def _run_job_task_unqueued(
        self,
        job_id: str,
        orchestrator: Orchestrator,
        pipeline_type: str,
        prompts_file: str,
        prompt: str = None,
    ):
        try:
            await self._execute_job_task(job_id, orchestrator, pipeline_type, prompts_file, prompt)
        except asyncio.CancelledError:
            self._mark_job_cancelled(job_id)
            raise
        finally:
            self.active_jobs.pop(job_id, None)

    async def _run_job_task(self, job_id: str, orchestrator: Orchestrator, pipeline_type: str, prompts_file: str, prompt: str = None):
        try:
            async with self._get_run_lock():
                await self._execute_job_task(job_id, orchestrator, pipeline_type, prompts_file, prompt)
        except asyncio.CancelledError:
            self._mark_job_cancelled(job_id)
            raise
        finally:
            self.active_jobs.pop(job_id, None)

    async def _execute_job_task(self, job_id: str, orchestrator: Orchestrator, pipeline_type: str, prompts_file: str, prompt: str = None):
        final_status = "success"
        try:
            with SessionLocal() as db:
                job = db.query(Job).filter(Job.id == job_id).first()
                if not job or job.status == "cancelled":
                    return
                if job:
                    job.status = "running"
                    job.current_step = "Starting"
                    db.commit()

            if prompt:
                # Quick run for a single prompt/url
                if pipeline_type == "crawl" or (isinstance(prompt, str) and prompt.startswith("http")):
                    result = await asyncio.to_thread(orchestrator.process_crawl, prompt)
                else:
                    result = await asyncio.to_thread(orchestrator.process_prompt, prompt)

                if self._is_job_cancelled(job_id):
                    return

                res_status = result.get("status", "info")
                if res_status == "error":
                    final_status = "failed"
                    self._add_log_event(job_id, "Failed", result.get("error") or f"Processed {pipeline_type} failed.", "failed")
                else:
                    self._add_log_event(job_id, "Completed", f"Processed {pipeline_type}: {prompt[:50]}...", res_status)
            else:
                # Full run from prompts file
                results = await asyncio.to_thread(orchestrator.run, prompts_file)

                if self._is_job_cancelled(job_id):
                    return

                # Check if all items failed
                if results and all(r.get("status") == "error" for r in results):
                    final_status = "failed"
                elif any(r.get("status") == "error" for r in results):
                    final_status = "partial_success"

                if final_status == "failed":
                    first_error = next((r.get("error") for r in results if r.get("status") == "error" and r.get("error")), "")
                    self._add_log_event(job_id, "Failed", first_error or f"Processed batch. {len(results)} items failed.", "failed")
                else:
                    self._add_log_event(job_id, "Completed", f"Processed batch. {len(results)} items handled.", final_status)

            with SessionLocal() as db:
                job = db.query(Job).filter(Job.id == job_id).first()
                if job and job.status != "cancelled":
                    job.status = final_status
                    job.progress = 100
                    job.end_time = datetime.utcnow()
                    db.commit()
        except Exception as e:
            logger.exception(f"Job {job_id} failed")
            self._add_log_event(job_id, "Critical Error", str(e), "failed")
            with SessionLocal() as db:
                job = db.query(Job).filter(Job.id == job_id).first()
                if job and job.status != "cancelled":
                    job.status = "failed"
                    job.end_time = datetime.utcnow()
                    db.commit()

    async def cancel_job(self, job_id: str):
        with SessionLocal() as db:
            job = db.query(Job).filter(Job.id == job_id).first()
            if not job:
                return None
            if job.status not in ("queued", "running"):
                return {"status": "not_cancelled", "current_status": job.status}

        task = self.active_jobs.get(job_id)
        self._mark_job_cancelled(job_id)
        if task and not task.done():
            task.cancel()

        return {"status": "cancelled"}

    def _mark_job_cancelled(self, job_id: str):
        with SessionLocal() as db:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job and job.status in ("queued", "running"):
                logs = list(job.logs or [])
                logs.append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "step_name": "Cancelled",
                    "detail": "Job was cancelled by user.",
                    "event": "cancelled"
                })
                job.logs = logs[-MAX_JOB_LOGS:]
                job.status = "cancelled"
                job.current_step = "Cancelled"
                job.end_time = datetime.utcnow()
                db.commit()

    def _is_job_cancelled(self, job_id: str):
        with SessionLocal() as db:
            job = db.query(Job).filter(Job.id == job_id).first()
            return bool(job and job.status == "cancelled")

    def _add_log_event(self, job_id: str, event_name: str, detail: str, status: str = "info"):
        with SessionLocal() as db:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job and (job.status != "cancelled" or status == "cancelled"):
                logs = list(job.logs or [])
                logs.append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "step_name": event_name,
                    "detail": detail,
                    "event": status
                })
                job.logs = logs[-MAX_JOB_LOGS:]
                db.commit()

worker_manager = WorkerManager()
