import random
from datetime import datetime


def pick_random_minute_for_day(job_name: str, day_key: str, job: dict) -> int:
    rnd = random.Random(f"{job_name}:{day_key}")
    return rnd.randint(int(job["jitter_min"]), int(job["jitter_max"]))


def should_run_job_now(job: dict, now: datetime, state: dict) -> bool:
    if not job.get("enabled", True):
        return False

    mode = job.get("mode")

    if mode == "fixed":
        hh, mm = map(int, job["time"].split(":"))
        key = f"{job.get('name', 'job')}:{now.date()}"
        if state.get(key):
            return False
        return now.hour == hh and now.minute == mm

    if mode == "random_window":
        hh, base_mm = map(int, job["base_time"].split(":"))
        day_key = str(now.date())
        seed_key = f"{job.get('name', 'job')}:{day_key}:target"
        if seed_key not in state:
            offset = pick_random_minute_for_day(job.get("name", "job"), day_key, job)
            state[seed_key] = offset

        target_minute = base_mm + state[seed_key]
        key = f"{job.get('name', 'job')}:{day_key}"
        if state.get(key):
            return False
        return now.hour == hh and now.minute == target_minute

    return False
