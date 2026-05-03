from queue import Queue
from threading import Lock
from uuid import uuid4

from core.orchestrator import Orchestrator
from core.language import normalize_language


class JobRunner:
    def __init__(self, config: dict):
        self.config = config
        self.queue = Queue()
        self._run_lock = Lock()
        self.jobs = {}

    def submit_manual_run(self, options, enqueue: bool = True):
        job_id = str(uuid4())
        self.jobs[job_id] = {
            "job_id": job_id,
            "status": "queued",
            "step_index": None,
            "step_name": None,
            "step_progress": 0,
            "detail": "queued",
        }
        if enqueue:
            self.queue.put({"type": "manual", "job_id": job_id, "options": options})
        return job_id

    def get_job_status(self, job_id: str):
        return self.jobs.get(job_id)

    def submit_scheduled_run(self, job_name: str, options):
        self.queue.put({"type": "scheduled", "job_name": job_name, "options": options})

    def _update_job_progress(self, job_id: str, *, status=None, step_index=None, step_name=None, step_progress=None, detail=None):
        state = self.jobs.get(job_id)
        if not state:
            return
        if status is not None:
            state["status"] = status
        if step_index is not None:
            state["step_index"] = step_index
        if step_name is not None:
            state["step_name"] = step_name
        if step_progress is not None:
            state["step_progress"] = step_progress
        if detail is not None:
            state["detail"] = detail

    def _execute_once(self, options, job_id=None):
        with self._run_lock:
            if job_id:
                self._update_job_progress(job_id, status="running", detail="started")

            def _progress_callback(step_index, step_name, step_progress, detail=""):
                if job_id:
                    self._update_job_progress(
                        job_id,
                        status="running",
                        step_index=step_index,
                        step_name=step_name,
                        step_progress=step_progress,
                        detail=detail,
                    )

            language = normalize_language(options.language)
            enable_image = options.resolve_enable_image(self.config.get("enable_image_generation", True))
            orchestrator = Orchestrator(
                config=self.config,
                num_threads=options.threads,
                limit=options.limit,
                language=language,
                debug=options.debug,
                enable_image_generation=enable_image,
                progress_callback=_progress_callback,
            )
            try:
                orchestrator.run("prompts.txt")
                if job_id:
                    self._update_job_progress(job_id, status="success", step_progress=100, detail="done")
            except Exception as e:
                if job_id:
                    self._update_job_progress(job_id, status="error", detail=str(e))
                raise
