from queue import Queue
from threading import Lock
from uuid import uuid4

from core.orchestrator import Orchestrator
from core.language import normalize_language
from core.article_crawler import extract_article_from_url


IMAGE_STEP_ID = "ai_image_generation"


def _normalize_disabled_steps(value):
    if not isinstance(value, list):
        return []
    normalized = []
    seen = set()
    for item in value:
        if not isinstance(item, str):
            continue
        step = item.strip()
        if not step or step in seen:
            continue
        seen.add(step)
        normalized.append(step)
    return normalized


def _effective_disabled_steps_from_config(config: dict) -> list[str]:
    if "disabled_steps" in config:
        return _normalize_disabled_steps(config.get("disabled_steps"))
    if bool(config.get("enable_image_generation", True)):
        return []
    return [IMAGE_STEP_ID]


def _resolve_disabled_steps(options, config: dict) -> list[str]:
    disabled_steps = _effective_disabled_steps_from_config(config)

    if options.with_image and options.no_image:
        raise ValueError("--with-image and --no-image cannot be used together")

    if options.no_image and IMAGE_STEP_ID not in disabled_steps:
        disabled_steps.append(IMAGE_STEP_ID)
    if options.with_image:
        disabled_steps = [step for step in disabled_steps if step != IMAGE_STEP_ID]

    return disabled_steps


def _language_name_from_code(language_code: str) -> str:
    if language_code == "uk":
        return "Ukrainian"
    if language_code == "en":
        return "English"
    if language_code == "vi":
        return "Vietnamese"
    return language_code


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
            disabled_steps = _resolve_disabled_steps(options, self.config)
            orchestrator = Orchestrator(
                config=self.config,
                num_threads=options.threads,
                limit=options.limit,
                language=language,
                debug=options.debug,
                disabled_steps=disabled_steps,
                progress_callback=_progress_callback,
            )
            try:
                if options.crawl_url:
                    article_data = extract_article_from_url(options.crawl_url, orchestrator.ai, language=_language_name_from_code(language))
                    orchestrator.process_article_data(article_data)
                else:
                    orchestrator.run("prompts.txt")
                if job_id:
                    self._update_job_progress(job_id, status="success", step_progress=100, detail="done")
            except Exception as e:
                if job_id:
                    self._update_job_progress(job_id, status="error", detail=str(e))
                raise
