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

    def submit_manual_run(self, options):
        job_id = str(uuid4())
        self.jobs[job_id] = {
            "job_id": job_id,
            "status": "queued",
            "step_index": 0,
            "step_name": "queued",
            "step_progress": 0,
            "detail": "",
        }
        self.queue.put({"type": "manual", "job_id": job_id, "options": options})
        return job_id

    def get_job_status(self, job_id: str):
        return self.jobs.get(job_id)

    def submit_scheduled_run(self, job_name: str, options):
        self.queue.put({"type": "scheduled", "job_name": job_name, "options": options})

    def _execute_once(self, options):
        with self._run_lock:
            language = normalize_language(options.language)
            enable_image = options.resolve_enable_image(self.config.get("enable_image_generation", True))
            orchestrator = Orchestrator(
                config=self.config,
                num_threads=options.threads,
                limit=options.limit,
                language=language,
                debug=options.debug,
                enable_image_generation=enable_image,
            )
            orchestrator.run("prompts.txt")
