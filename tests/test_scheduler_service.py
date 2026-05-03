from datetime import datetime
from unittest.mock import MagicMock

from core.scheduler_service import SchedulerService


def test_scheduler_service_enqueues_fixed_job_when_due():
    config = {
        "scheduler": {
            "enabled": True,
            "jobs": [
                {
                    "name": "fixed1",
                    "enabled": True,
                    "mode": "fixed",
                    "time": "08:15",
                    "run_options": {"limit": 1, "threads": 2, "language": "en", "debug": False, "update": False, "with_image": False, "no_image": True},
                }
            ],
        }
    }
    runner = MagicMock()
    service = SchedulerService(config=config, job_runner=runner)

    service.tick(now=datetime(2026, 5, 3, 8, 15))

    runner.submit_scheduled_run.assert_called_once()
