from datetime import datetime

from core.scheduler import should_run_job_now, pick_random_minute_for_day


def test_fixed_job_runs_at_exact_time():
    job = {"name": "fixed-job", "enabled": True, "mode": "fixed", "time": "08:15"}
    now = datetime(2026, 5, 3, 8, 15)
    assert should_run_job_now(job, now, state={}) is True


def test_random_window_job_uses_daily_selected_minute_in_range():
    job = {
        "name": "daily",
        "enabled": True,
        "mode": "random_window",
        "base_time": "08:00",
        "jitter_min": 5,
        "jitter_max": 10,
    }
    minute = pick_random_minute_for_day(job_name="daily", day_key="2026-05-03", job=job)
    assert minute in {5, 6, 7, 8, 9, 10}
