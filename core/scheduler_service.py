from datetime import datetime
from typing import Optional

from core.run_options import RunOptions
from core.scheduler import should_run_job_now


class SchedulerService:
    def __init__(self, config: dict, job_runner):
        self.config = config
        self.job_runner = job_runner
        self.state = {}

    def tick(self, now: Optional[datetime] = None):
        current = now or datetime.now()
        scheduler_cfg = self.config.get("scheduler", {})
        if not scheduler_cfg.get("enabled", False):
            return

        for job in scheduler_cfg.get("jobs", []):
            if not should_run_job_now(job, current, self.state):
                continue

            run_options = job.get("run_options", {})
            options = RunOptions(
                limit=run_options.get("limit"),
                threads=run_options.get("threads", 5),
                language=run_options.get("language", "Ukraina"),
                debug=run_options.get("debug", False),
                update=run_options.get("update", False),
                with_image=run_options.get("with_image", False),
                no_image=run_options.get("no_image", False),
            )
            self.job_runner.submit_scheduled_run(job_name=job.get("name", "job"), options=options)

            key = f"{job.get('name', 'job')}:{current.date()}"
            self.state[key] = True
