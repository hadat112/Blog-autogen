# Telegram Run Step Progress Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `/run` Telegram progress updates that edit one message continuously, with per-step local progress ticks `0,20,40,60,80,100`.

**Architecture:** Extend `JobRunner` to return a `job_id` and store in-memory progress state. `Orchestrator` reports progress through callback events. `TelegramService` sends one initial message then polls job state and edits that same message until done/error.

**Tech Stack:** Python, python-telegram-bot, pytest, unittest.mock

---

### Task 1: Job state model in JobRunner

**Files:**
- Modify: `core/job_runner.py`
- Test: `tests/test_job_runner.py`

- [ ] **Step 1: Write the failing test**

```python
def test_submit_manual_run_returns_job_id_and_tracks_queued_state():
    runner = JobRunner(config={})
    opts = RunOptions(limit=1, threads=1, language="en", debug=False, update=False, with_image=False, no_image=False)

    job_id = runner.submit_manual_run(options=opts)
    state = runner.get_job_status(job_id)

    assert isinstance(job_id, str)
    assert state["status"] == "queued"
    assert state["step_progress"] == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_job_runner.py::test_submit_manual_run_returns_job_id_and_tracks_queued_state -v`
Expected: FAIL (`submit_manual_run` returns None or `get_job_status` missing)

- [ ] **Step 3: Write minimal implementation**

```python
# in JobRunner.__init__
self._jobs = {}

# new
def get_job_status(self, job_id):
    return self._jobs.get(job_id)

# update submit_manual_run
def submit_manual_run(self, options):
    job_id = uuid4().hex
    self._jobs[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "step_index": None,
        "step_name": None,
        "step_progress": 0,
        "detail": "queued",
    }
    self.queue.put({"type": "manual", "job_id": job_id, "options": options})
    return job_id
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_job_runner.py::test_submit_manual_run_returns_job_id_and_tracks_queued_state -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/job_runner.py tests/test_job_runner.py
git commit -m "feat: add queued job state and job id tracking"
```

### Task 2: Progress callback wiring from JobRunner to Orchestrator

**Files:**
- Modify: `core/job_runner.py`
- Modify: `core/orchestrator.py`
- Test: `tests/test_job_runner.py`

- [ ] **Step 1: Write the failing test**

```python
@patch("core.job_runner.Orchestrator")
def test_execute_once_updates_running_and_success_states(mock_orch_cls):
    runner = JobRunner(config={"enable_image_generation": True})
    opts = RunOptions(limit=1, threads=1, language="en", debug=False, update=False, with_image=False, no_image=False)
    job_id = runner.submit_manual_run(options=opts)

    progress_cb = None
    def _capture(**kwargs):
        nonlocal progress_cb
        progress_cb = kwargs["progress_callback"]
        class _O:
            def run(self, _):
                progress_cb(step_index=1, step_name="Generate story text", step_progress=20, detail="working")
                progress_cb(step_index=1, step_name="Generate story text", step_progress=100, detail="done")
                return []
        return _O()
    mock_orch_cls.side_effect = _capture

    runner._execute_once(options=opts, job_id=job_id)
    state = runner.get_job_status(job_id)
    assert state["status"] == "success"
    assert state["step_progress"] == 100
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_job_runner.py::test_execute_once_updates_running_and_success_states -v`
Expected: FAIL (`_execute_once` signature or missing callback wiring)

- [ ] **Step 3: Write minimal implementation**

```python
# job_runner.py

def _update_job_progress(self, job_id, *, status=None, step_index=None, step_name=None, step_progress=None, detail=None):
    ...

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

        orchestrator = Orchestrator(..., progress_callback=_progress_callback)
        orchestrator.run("prompts.txt")

        if job_id:
            self._update_job_progress(job_id, status="success", step_progress=100, detail="done")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_job_runner.py::test_execute_once_updates_running_and_success_states -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/job_runner.py core/orchestrator.py tests/test_job_runner.py
git commit -m "feat: wire orchestrator progress callback into job state"
```

### Task 3: Per-step progress emission in Orchestrator

**Files:**
- Modify: `core/orchestrator.py`
- Test: `tests/test_job_runner.py`

- [ ] **Step 1: Write the failing test**

```python
@patch("core.job_runner.Orchestrator")
def test_execute_once_reports_step_local_progress_ticks(mock_orch_cls):
    runner = JobRunner(config={"enable_image_generation": True})
    opts = RunOptions(limit=1, threads=1, language="en", debug=False, update=False, with_image=False, no_image=False)
    job_id = runner.submit_manual_run(options=opts)

    def _factory(**kwargs):
        cb = kwargs["progress_callback"]
        class _O:
            def run(self, _):
                for p in (0, 20, 40, 60, 80, 100):
                    cb(step_index=1, step_name="Generate story text", step_progress=p, detail="tick")
                return []
        return _O()
    mock_orch_cls.side_effect = _factory

    runner._execute_once(options=opts, job_id=job_id)
    state = runner.get_job_status(job_id)
    assert state["step_name"] == "Generate story text"
    assert state["step_progress"] == 100
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_job_runner.py::test_execute_once_reports_step_local_progress_ticks -v`
Expected: FAIL until callback flow supports expected fields/ticks

- [ ] **Step 3: Write minimal implementation**

```python
# orchestrator.py __init__
def __init__(..., progress_callback=None):
    ...
    self.progress_callback = progress_callback

# helper
def _emit_progress(self, step_index, step_name, step_progress, detail=""):
    if self.progress_callback:
        self.progress_callback(
            step_index=step_index,
            step_name=step_name,
            step_progress=step_progress,
            detail=detail,
        )

# inside each main step
for p in (0, 20, 40, 60, 80, 100):
    self._emit_progress(1, "Generate story text", p, "working")
# ... similarly for steps 2-5
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_job_runner.py::test_execute_once_reports_step_local_progress_ticks -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/orchestrator.py tests/test_job_runner.py
git commit -m "feat: emit step-local progress ticks for run pipeline"
```

### Task 4: Telegram single-message progress editing loop

**Files:**
- Modify: `core/telegram_commands.py`
- Modify: `core/telegram_service.py`
- Test: `tests/test_telegram_service.py`
- Test: `tests/test_telegram_commands.py`

- [ ] **Step 1: Write the failing test**

```python
@patch("core.telegram_service.TelegramService._build_reply", return_value="Run queued successfully.")
def test_on_run_edits_single_message_until_done(_mock_build):
    config = {"telegram_bot_token": "tkn", "telegram_commands": {"enabled": True}}
    runner = MagicMock()
    runner.get_job_status.side_effect = [
        {"status": "running", "step_index": 1, "step_name": "Generate story text", "step_progress": 20, "detail": "working"},
        {"status": "running", "step_index": 1, "step_name": "Generate story text", "step_progress": 100, "detail": "done"},
        {"status": "success", "step_index": 5, "step_name": "Publish to Facebook", "step_progress": 100, "detail": "done"},
    ]
    runner.submit_manual_run.return_value = "job-1"
    service = TelegramService(config=config, job_runner=runner)

    message = MagicMock()
    message.text = "/run --limit 1"
    message.reply_text = AsyncMock()
    progress_msg = MagicMock()
    progress_msg.edit_text = AsyncMock()
    message.reply_text.return_value = progress_msg

    update = MagicMock()
    update.effective_message = message
    update.effective_chat.id = 123

    asyncio.run(service._on_run(update, MagicMock()))

    progress_msg.edit_text.assert_awaited()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_telegram_service.py::test_on_run_edits_single_message_until_done -v`
Expected: FAIL (no polling/edit loop)

- [ ] **Step 3: Write minimal implementation**

```python
# telegram_commands.py
# keep parse validation, but no longer submit there

def handle_telegram_message(...):
    ...
    return "Run accepted. Starting..."

# telegram_service.py
async def _on_run(self, update, context):
    ...
    options = parse_run_tokens(tokens)
    job_id = self.job_runner.submit_manual_run(options=options)
    progress_msg = await message.reply_text("Run started\nStep 1 ... 0%")

    last_text = ""
    while True:
        state = self.job_runner.get_job_status(job_id)
        rendered = self._render_progress_text(state)
        if rendered != last_text:
            await progress_msg.edit_text(rendered)
            last_text = rendered
        if state and state.get("status") in {"success", "error"}:
            break
        await asyncio.sleep(1)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_telegram_service.py::test_on_run_edits_single_message_until_done -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/telegram_service.py core/telegram_commands.py tests/test_telegram_service.py tests/test_telegram_commands.py
git commit -m "feat: add single-message telegram progress updates for run"
```

### Task 5: Full regression verification

**Files:**
- Test: `tests/test_telegram_service.py`
- Test: `tests/test_telegram_commands.py`
- Test: `tests/test_job_runner.py`
- Test: `tests/test_main.py`

- [ ] **Step 1: Run focused suites**

Run: `pytest tests/test_telegram_service.py tests/test_telegram_commands.py tests/test_job_runner.py -v`
Expected: PASS

- [ ] **Step 2: Run listener/daemon regression**

Run: `pytest tests/test_main.py -v`
Expected: PASS

- [ ] **Step 3: Commit final stabilization**

```bash
git add tests/test_telegram_service.py tests/test_telegram_commands.py tests/test_job_runner.py tests/test_main.py core/telegram_service.py core/telegram_commands.py core/job_runner.py core/orchestrator.py
git commit -m "test: stabilize telegram progress and daemon listener regressions"
```

## Self-review checklist
- Spec coverage: includes single-message edit loop, per-step local progress ticks, done/error final states, compatibility constraints.
- Placeholder scan: no TBD/TODO placeholders.
- Type consistency: `step_progress` and `get_job_status(job_id)` names are consistent across tasks.
