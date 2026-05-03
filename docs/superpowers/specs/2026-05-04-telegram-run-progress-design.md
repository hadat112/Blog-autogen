# Telegram `/run` Step Progress (Single Edited Message) Design

## Goal
When user sends `/run ...` in Telegram, bot immediately confirms start, then continuously edits **one message** to show per-step progress. Each step has its own progress lifecycle (0→20→40→60→80→100), not a global whole-run percentage.

## Scope
In scope:
- Telegram `/run` UX only.
- Single message edited throughout run.
- Per-step progress updates with 5 fixed increments per step.

Out of scope:
- Changes to CLI one-shot run flow.
- Scheduler behavior changes.
- Architectural rewrite of orchestrator internals.

## User Experience
After `/run --limit 1 ...`:
1. Bot sends initial message: run accepted and started.
2. Bot edits that same message repeatedly.
3. For each step:
   - `Step N <name>: 0%`
   - `Step N <name>: 20%`
   - `Step N <name>: 40%`
   - `Step N <name>: 60%`
   - `Step N <name>: 80%`
   - `Step N <name>: 100%`
4. After final step, message becomes `Done` (or `Failed` with failing step + short reason).

## Steps Model
We map existing processing pipeline into named steps:
1. Generate story text
2. Generate image (or mark skipped with successful completion of step)
3. Publish to WordPress
4. Log to Google Sheets
5. Publish to Facebook

Each step emits local progress ticks: `0,20,40,60,80,100`.

## Technical Design

### 1) Job progress state in `JobRunner`
Add in-memory progress state keyed by `job_id`:
- `job_id: str`
- `status: queued | running | success | error`
- `step_index: int | None`
- `step_name: str | None`
- `step_progress: int` (0..100, step-local)
- `detail: str`

Required methods:
- `submit_manual_run(options) -> str` (returns `job_id`)
- `get_job_status(job_id) -> dict | None`
- internal updater helpers for state transitions.

### 2) Progress callback path
`JobRunner` passes a lightweight progress callback into execution path.
The callback updates the current job state with:
- current step index/name
- current step-local percent
- optional short detail

`Orchestrator.process_prompt` emits progress events at step boundaries and 5 fixed ticks per step. If a step has no natural internal sub-progress, ticks are emitted at deterministic checkpoints inside that step logic (minimal overhead).

### 3) Telegram single-message editing
In `TelegramService._on_run`:
- parse and enqueue run -> receive `job_id`
- send initial message (capture message object)
- poll `job_runner.get_job_status(job_id)` every 1s
- build display text from current step + step_progress
- call `edit_text` on same message only when text changes
- stop polling when status in `{success,error}`

### 4) Error handling
- If job errors, final edited message includes failing step and short error reason.
- If edit fails transiently, retry on next poll cycle.
- If status missing unexpectedly, show safe fallback message and stop loop.

### 5) Backward compatibility constraints
- Existing CLI run (`python main.py --limit ...`) unchanged.
- Existing start/stop/restart daemon flows unchanged.
- Scheduler flow unchanged.
- Existing `/start` command unchanged.

## Testing Strategy

### Unit tests
1. `JobRunner`
- returns `job_id` on submit
- state transitions: queued -> running -> success
- error transition includes failing step/detail

2. `TelegramService`
- `/run` sends initial message
- progress polling edits same message multiple times
- final success message is emitted
- final error message is emitted

3. `Orchestrator` (focused)
- invokes progress callback with expected step names
- emits step-local progress ticks ending at 100

### Regression tests
- Existing telegram service tests still pass.
- Existing main daemon/listener tests still pass.

## Non-functional notes
- Poll interval: 1 second to balance responsiveness and Telegram API calls.
- Update deduplication: skip edit if rendered text unchanged.
- In-memory state is acceptable for current daemon model.

## Acceptance Criteria
- Sending `/run ...` always gives immediate feedback that run started.
- User sees one message continuously updated.
- Every step shows its own `0,20,40,60,80,100` progression.
- Final state clearly shows `Done` or `Failed`.
- No regression in CLI/scheduler/start-stop behavior.
