# Telegram /run + Config Scheduler Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Telegram `/run ...` command that accepts CLI-like options and execute jobs through a background queue, plus an internal config-driven scheduler (fixed time + random jitter jobs) with global/per-job enable toggles.

**Architecture:** Introduce a shared `RunOptions` parser/validator used by CLI, Telegram command handling, and scheduler job definitions. Add a small job runner service with queue + single-run lock and a scheduler loop that reads `config.yaml`, supports `fixed` and `random_window` modes, and submits jobs into the same queue. Keep Telegram layer thin: parse command -> enqueue -> immediate ack.

**Tech Stack:** Python, argparse-style option parsing, threading/queue, datetime, pytest, unittest.mock, existing Orchestrator + ConfigManager + Telegram utility.

---

## File Structure and Responsibilities

- **Create** `core/run_options.py`
  - Define `RunOptions` dataclass and shared parsing/validation logic.
  - Parse CLI-like tokens for Telegram (`/run --limit 2 --with-image`).
  - Resolve image-toggle precedence (`with_image` vs `no_image`).

- **Create** `core/job_runner.py`
  - Background worker queue + lock (no overlapping runs).
  - Unified method to execute one story run using existing Orchestrator.
  - Entrypoints: `submit_manual_run(options)` and `submit_scheduled_run(job_name, options)`.

- **Create** `core/scheduler.py`
  - Config-based schedule evaluator for daily jobs.
  - Support `mode: fixed` and `mode: random_window`.
  - Per-day random trigger minute generation for jitter mode.

- **Create** `core/telegram_commands.py`
  - Handle incoming Telegram text updates.
  - Parse `/run ...` via shared parser; submit to job runner.
  - Return success/error text only; no orchestration logic here.

- **Modify** `main.py`
  - Reuse shared `RunOptions` resolution instead of inline image-flag logic.
  - Optional: start scheduler/bot loops from main if config enables them.

- **Modify** `core/config_manager.py`
  - Add onboarding fields for scheduler and Telegram command listener config.
  - Persist default scheduler schema in `config.yaml`.

- **Modify** `utils/helpers.py`
  - Add lightweight Telegram update fetch helper (long-polling).

- **Create** tests:
  - `tests/test_run_options.py`
  - `tests/test_telegram_commands.py`
  - `tests/test_scheduler.py`
  - `tests/test_job_runner.py`
  - plus minimal updates in `tests/test_main.py`/`tests/test_config_manager.py`

---

### Task 1: Build shared RunOptions parser (test-first)

**Files:**
- Create: `core/run_options.py`
- Create: `tests/test_run_options.py`

- [ ] **Step 1: Write failing tests for option parsing and validation**

```python
# tests/test_run_options.py
import pytest
from core.run_options import RunOptions, parse_run_tokens


def test_parse_tokens_with_limit_and_with_image():
    opts = parse_run_tokens(["--limit", "3", "--with-image"])
    assert opts.limit == 3
    assert opts.with_image is True
    assert opts.no_image is False


def test_parse_tokens_with_no_image():
    opts = parse_run_tokens(["--no-image"])
    assert opts.no_image is True
    assert opts.with_image is False


def test_parse_conflicting_image_flags_raises():
    with pytest.raises(ValueError):
        parse_run_tokens(["--with-image", "--no-image"])


def test_effective_enable_image_from_flags_and_default():
    opts = RunOptions(limit=None, threads=5, language="uk", debug=False, with_image=False, no_image=True)
    assert opts.resolve_enable_image(default_from_config=True) is False
```

- [ ] **Step 2: Run tests to verify RED**

Run: `pytest tests/test_run_options.py -v`

Expected: FAIL because `core/run_options.py` does not exist yet.

- [ ] **Step 3: Implement minimal RunOptions parser**

```python
# core/run_options.py
from dataclasses import dataclass
import argparse


@dataclass
class RunOptions:
    limit: int | None
    threads: int
    language: str
    debug: bool
    with_image: bool
    no_image: bool

    def resolve_enable_image(self, default_from_config: bool) -> bool:
        if self.with_image and self.no_image:
            raise ValueError("--with-image and --no-image cannot be used together")
        if self.no_image:
            return False
        if self.with_image:
            return True
        return bool(default_from_config)


def parse_run_tokens(tokens: list[str]) -> RunOptions:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--threads", type=int, default=5)
    parser.add_argument("--language", type=str, default="Ukraina")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--with-image", action="store_true")
    parser.add_argument("--no-image", action="store_true")
    ns = parser.parse_args(tokens)
    return RunOptions(
        limit=ns.limit,
        threads=ns.threads,
        language=ns.language,
        debug=ns.debug,
        with_image=ns.with_image,
        no_image=ns.no_image,
    )
```

- [ ] **Step 4: Run tests to verify GREEN**

Run: `pytest tests/test_run_options.py -v`

Expected: PASS.

- [ ] **Step 5: Commit Task 1**

```bash
git add core/run_options.py tests/test_run_options.py
git commit -m "feat: add shared RunOptions parser for CLI-like run commands"
```

---

### Task 2: Add Telegram `/run ...` command parser/handler (test-first)

**Files:**
- Create: `core/telegram_commands.py`
- Create: `tests/test_telegram_commands.py`
- Modify: `utils/helpers.py`

- [ ] **Step 1: Write failing tests for `/run` command handling**

```python
# tests/test_telegram_commands.py
from unittest.mock import MagicMock
from core.telegram_commands import handle_telegram_message


def test_handle_run_command_submits_job():
    runner = MagicMock()
    config = {"enable_image_generation": False}

    reply = handle_telegram_message(
        text="/run --limit 2 --with-image",
        config=config,
        job_runner=runner,
    )

    assert "queued" in reply.lower()
    submitted = runner.submit_manual_run.call_args.kwargs["options"]
    assert submitted.limit == 2
    assert submitted.with_image is True


def test_handle_run_command_returns_parse_error():
    runner = MagicMock()
    reply = handle_telegram_message(
        text="/run --with-image --no-image",
        config={"enable_image_generation": True},
        job_runner=runner,
    )
    assert "error" in reply.lower()
    runner.submit_manual_run.assert_not_called()
```

- [ ] **Step 2: Run tests to verify RED**

Run: `pytest tests/test_telegram_commands.py -v`

Expected: FAIL because handler does not exist yet.

- [ ] **Step 3: Implement minimal command handler**

```python
# core/telegram_commands.py
from core.run_options import parse_run_tokens


def handle_telegram_message(text: str, config: dict, job_runner) -> str:
    msg = (text or "").strip()
    if not msg.startswith("/run"):
        return "Unsupported command. Use /run ..."

    tokens = msg.split()[1:]
    try:
        options = parse_run_tokens(tokens)
        options.resolve_enable_image(config.get("enable_image_generation", True))
    except Exception as e:
        return f"Error: {e}"

    job_runner.submit_manual_run(options=options)
    return "Run queued successfully."
```

- [ ] **Step 4: Add Telegram update fetch helper**

```python
# utils/helpers.py
def fetch_telegram_updates(token, offset=None, timeout=30):
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    payload = {"timeout": timeout}
    if offset is not None:
        payload["offset"] = offset
    response = requests.get(url, params=payload, timeout=timeout + 5)
    response.raise_for_status()
    return response.json()
```

- [ ] **Step 5: Run tests to verify GREEN**

Run: `pytest tests/test_telegram_commands.py -v`

Expected: PASS.

- [ ] **Step 6: Commit Task 2**

```bash
git add core/telegram_commands.py utils/helpers.py tests/test_telegram_commands.py
git commit -m "feat: add telegram /run command parsing and queue submission"
```

---

### Task 3: Implement background job runner queue (test-first)

**Files:**
- Create: `core/job_runner.py`
- Create: `tests/test_job_runner.py`
- Modify: `core/orchestrator.py` (only if tiny hook needed)

- [ ] **Step 1: Write failing tests for queued execution and lock behavior**

```python
# tests/test_job_runner.py
from unittest.mock import MagicMock, patch
from core.run_options import RunOptions
from core.job_runner import JobRunner


def test_submit_manual_run_enqueues_job():
    runner = JobRunner(config={})
    opts = RunOptions(limit=1, threads=1, language="en", debug=False, with_image=False, no_image=False)

    runner.submit_manual_run(options=opts)

    assert runner.queue.qsize() == 1


@patch("core.job_runner.Orchestrator")
def test_worker_executes_orchestrator_with_resolved_image_toggle(mock_orch_cls):
    config = {"enable_image_generation": False}
    runner = JobRunner(config=config)
    opts = RunOptions(limit=1, threads=1, language="en", debug=False, with_image=True, no_image=False)

    runner._execute_once(options=opts)

    assert mock_orch_cls.call_args.kwargs["enable_image_generation"] is True
```

- [ ] **Step 2: Run tests to verify RED**

Run: `pytest tests/test_job_runner.py -v`

Expected: FAIL because runner does not exist yet.

- [ ] **Step 3: Implement minimal queue runner**

```python
# core/job_runner.py
from queue import Queue
from threading import Lock
from core.orchestrator import Orchestrator
from main import normalize_language


class JobRunner:
    def __init__(self, config: dict):
        self.config = config
        self.queue = Queue()
        self._run_lock = Lock()

    def submit_manual_run(self, options):
        self.queue.put({"type": "manual", "options": options})

    def submit_scheduled_run(self, job_name: str, options):
        self.queue.put({"type": "scheduled", "job_name": job_name, "options": options})

    def _execute_once(self, options):
        with self._run_lock:
            language = normalize_language(options.language)
            enable_image = options.resolve_enable_image(self.config.get("enable_image_generation", True))
            orch = Orchestrator(
                config=self.config,
                num_threads=options.threads,
                limit=options.limit,
                language=language,
                debug=options.debug,
                enable_image_generation=enable_image,
            )
            orch.run("prompts.txt")
```

- [ ] **Step 4: Run tests to verify GREEN**

Run: `pytest tests/test_job_runner.py -v`

Expected: PASS.

- [ ] **Step 5: Commit Task 3**

```bash
git add core/job_runner.py tests/test_job_runner.py
git commit -m "feat: add background queue runner for manual and scheduled runs"
```

---

### Task 4: Add config-driven scheduler with fixed + random_window modes (test-first)

**Files:**
- Create: `core/scheduler.py`
- Create: `tests/test_scheduler.py`
- Modify: `core/config_manager.py`
- Modify: `tests/test_config_manager.py`

- [ ] **Step 1: Write failing scheduler tests**

```python
# tests/test_scheduler.py
from datetime import datetime
from core.scheduler import should_run_job_now, pick_random_minute_for_day


def test_fixed_job_runs_at_exact_time():
    job = {"enabled": True, "mode": "fixed", "time": "08:15"}
    now = datetime(2026, 5, 3, 8, 15)
    assert should_run_job_now(job, now, state={}) is True


def test_random_window_job_uses_daily_selected_minute():
    job = {
        "enabled": True,
        "mode": "random_window",
        "base_time": "08:00",
        "jitter_min": 5,
        "jitter_max": 10,
    }
    minute = pick_random_minute_for_day(job_name="daily", day_key="2026-05-03", job=job)
    assert minute in {5, 6, 7, 8, 9, 10}
```

- [ ] **Step 2: Run tests to verify RED**

Run: `pytest tests/test_scheduler.py -v`

Expected: FAIL because scheduler module missing.

- [ ] **Step 3: Implement minimal scheduler logic**

```python
# core/scheduler.py
import random
from datetime import datetime


def pick_random_minute_for_day(job_name: str, day_key: str, job: dict) -> int:
    rnd = random.Random(f"{job_name}:{day_key}")
    return rnd.randint(int(job["jitter_min"]), int(job["jitter_max"]))


def should_run_job_now(job: dict, now: datetime, state: dict) -> bool:
    if not job.get("enabled", True):
        return False

    mode = job.get("mode")
    hh, mm = map(int, (job.get("time") or job.get("base_time")).split(":"))

    if mode == "fixed":
        key = f"{job.get('name','job')}:{now.date()}"
        if state.get(key):
            return False
        return now.hour == hh and now.minute == mm

    if mode == "random_window":
        day_key = str(now.date())
        seed_key = f"{job.get('name','job')}:{day_key}:target"
        if seed_key not in state:
            offset = pick_random_minute_for_day(job.get("name","job"), day_key, job)
            state[seed_key] = offset
        target_minute = mm + state[seed_key]
        key = f"{job.get('name','job')}:{day_key}"
        if state.get(key):
            return False
        return now.hour == hh and now.minute == target_minute

    return False
```

- [ ] **Step 4: Extend onboarding config with scheduler defaults**

Add defaults into `core/config_manager.py` after existing fields:

```python
if "scheduler" not in self.config:
    self.config["scheduler"] = {
        "enabled": False,
        "jobs": [
            {
                "name": "daily-fixed",
                "enabled": True,
                "mode": "fixed",
                "time": "08:00",
                "run_options": {"limit": 1, "with_image": False, "no_image": True, "language": "uk", "threads": 5, "debug": False},
            },
            {
                "name": "daily-jitter",
                "enabled": False,
                "mode": "random_window",
                "base_time": "08:00",
                "jitter_min": 5,
                "jitter_max": 10,
                "run_options": {"limit": 1, "with_image": True, "no_image": False, "language": "uk", "threads": 5, "debug": False},
            },
        ],
    }
```

- [ ] **Step 5: Add/update config manager tests**

```python
assert "scheduler" in manager.config
assert "jobs" in manager.config["scheduler"]
```

- [ ] **Step 6: Run tests to verify GREEN**

Run: `pytest tests/test_scheduler.py tests/test_config_manager.py::test_run_onboarding -v`

Expected: PASS.

- [ ] **Step 7: Commit Task 4**

```bash
git add core/scheduler.py core/config_manager.py tests/test_scheduler.py tests/test_config_manager.py
git commit -m "feat: add config-driven scheduler with fixed and jitter modes"
```

---

### Task 5: Wire CLI + runner + scheduler bootstrap (test-first)

**Files:**
- Modify: `main.py`
- Modify: `tests/test_main.py`
- Modify/Create: scheduler loop startup location (likely `main.py`)

- [ ] **Step 1: Write failing tests for shared options usage in main**

```python
# tests/test_main.py
@patch("main.parse_run_tokens")
@patch("main.Orchestrator")
@patch("main.ConfigManager")
@patch("main.os.path.exists")
def test_main_uses_shared_run_options_parser(mock_exists, mock_cfg_cls, mock_orch_cls, mock_parse):
    mock_exists.return_value = True
    mock_cfg_cls.return_value.config = {"enable_image_generation": True}

    from core.run_options import RunOptions
    mock_parse.return_value = RunOptions(limit=2, threads=5, language="en", debug=False, with_image=False, no_image=False)
    mock_orch_cls.return_value.run.return_value = []

    from main import main
    main()

    assert mock_orch_cls.call_args.kwargs["limit"] == 2
```

- [ ] **Step 2: Run tests to verify RED**

Run: `pytest tests/test_main.py::test_main_uses_shared_run_options_parser -v`

Expected: FAIL until main is refactored.

- [ ] **Step 3: Refactor main to use shared `RunOptions`**

Core shape:

```python
# in main.py
from core.run_options import parse_run_tokens

tokens = sys.argv[1:]
options = parse_run_tokens(tokens)
enable_image = options.resolve_enable_image(config.get("enable_image_generation", True))
```

Use parsed options for Orchestrator constructor.

- [ ] **Step 4: Add scheduler bootstrap gating (minimal)**

Add config-based startup switch:

```python
if config.get("scheduler", {}).get("enabled", False):
    # start scheduler loop in daemon thread
```

- [ ] **Step 5: Run tests to verify GREEN**

Run: `pytest tests/test_main.py -v`

Expected: PASS.

- [ ] **Step 6: Commit Task 5**

```bash
git add main.py tests/test_main.py
git commit -m "refactor: unify CLI run options and scheduler bootstrap"
```

---

### Task 6: End-to-end scheduler/Telegram integration tests (focused)

**Files:**
- Modify: `tests/test_integrations.py`
- Optional: add small helper fixtures

- [ ] **Step 1: Write failing integration tests**

```python
# tests/test_integrations.py
from unittest.mock import MagicMock
from core.telegram_commands import handle_telegram_message
from core.run_options import RunOptions


def test_telegram_run_command_to_runner_pipeline():
    runner = MagicMock()
    cfg = {"enable_image_generation": False}

    msg = handle_telegram_message("/run --limit 1 --with-image", cfg, runner)

    assert "queued" in msg.lower()
    opts = runner.submit_manual_run.call_args.kwargs["options"]
    assert isinstance(opts, RunOptions)
```

- [ ] **Step 2: Run tests to verify RED**

Run: `pytest tests/test_integrations.py::test_telegram_run_command_to_runner_pipeline -v`

Expected: FAIL if pipeline not fully wired.

- [ ] **Step 3: Implement minimal missing glue (if any)**

Only add what failing test requires (imports/wiring/return messages), no extra features.

- [ ] **Step 4: Run tests to verify GREEN**

Run: `pytest tests/test_integrations.py::test_telegram_run_command_to_runner_pipeline -v`

Expected: PASS.

- [ ] **Step 5: Commit Task 6**

```bash
git add tests/test_integrations.py core/telegram_commands.py core/job_runner.py
# (include only files changed in this task)
git commit -m "test: verify telegram /run to queue pipeline"
```

---

### Task 7: Final verification

**Files:**
- Modify: none unless test failures require fixes

- [ ] **Step 1: Run targeted new modules**

Run: `pytest tests/test_run_options.py tests/test_telegram_commands.py tests/test_job_runner.py tests/test_scheduler.py -v`

Expected: PASS.

- [ ] **Step 2: Run full suite**

Run: `pytest -v`

Expected: PASS with no regressions.

- [ ] **Step 3: Manual smoke test for Telegram command text parsing**

Run (direct function smoke in REPL or small script):

```python
from core.telegram_commands import handle_telegram_message
from core.job_runner import JobRunner

cfg = {"enable_image_generation": False}
runner = JobRunner(cfg)
print(handle_telegram_message("/run --limit 1 --with-image", cfg, runner))
```

Expected: returns queued response and queue size increments.

- [ ] **Step 4: Manual scheduler smoke test with config jobs**

Set one fixed job to next minute, start tool, verify one queue submission and one run.

Expected: job runs once for the day, respects per-job image options.

- [ ] **Step 5: Commit verification fixes (if any)**

```bash
git add <files-fixed-during-verification>
git commit -m "test: finalize telegram and scheduler run orchestration"
```

---

## Spec Coverage Check

- Telegram supports `/run --limit --with-image/--no-image`: covered by Tasks 1, 2, 6.
- Future CLI parity for Telegram command growth: covered by shared `RunOptions` parser in Task 1 + main refactor in Task 5.
- Internal scheduler in tool (not Claude schedule): covered by Task 4 and bootstrap in Task 5.
- Scheduler supports fixed and jitter jobs with toggles: covered by Task 4.
- Job execution path unified across manual/scheduled/CLI: covered by Task 3 + Task 5.

## Placeholder/Consistency Check

- No TODO/TBD placeholders.
- Shared option names are consistent: `with_image`, `no_image`, `enable_image_generation`.
- Single precedence rule is centralized in `RunOptions.resolve_enable_image()`.
