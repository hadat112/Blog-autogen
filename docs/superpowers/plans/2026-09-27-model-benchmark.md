# Model Benchmark Implementation Plan

> **For agentic workers:** Implement this plan in the current workspace, task by task. The user explicitly requested no branch, no commits, and backend tests only.

**Goal:** Compare elapsed time and API success for 2–5 saved-account models translating one fixed story excerpt into Polish, sequentially.

**Architecture:** A dedicated benchmark route validates account and model selection, then queues a `model_benchmark` Job. A service runs each request in order and persists only status, elapsed time, and safe errors. A new React page fetches models, starts and polls the job, and displays compact rows.

**Tech Stack:** FastAPI, SQLAlchemy, OpenAI-compatible chat API, React, TypeScript, Vite.

**Spec:** `docs/superpowers/specs/2026-09-27-model-benchmark-design.md`

## Global Constraints

- Keep the sample exactly as provided, with Polish as fixed target.
- Count success only when the API returns without error and response text is nonempty after trimming.
- Run models sequentially, with no retry or fallback.
- Do not persist translation, sample prose, or credentials in Job outputs or logs.
- Test backend behavior; compile and lint frontend, with no frontend tests.
- Do not create a branch or commit.

## Review Focus

- A stale or wrong-type account must be rejected before a Job is created; cover in API tests.
- Duplicate, blank, unknown, or out-of-range model selection must be rejected; cover in API tests.
- One failed or empty response must retain its row and allow later models to run; cover in service tests.
- Cancellation during a blocking request must prevent the next request and preserve completed rows; cover in service tests.
- Errors must not leak API keys, generated text, or raw provider response bodies; cover in service tests.

## Task 1: Backend API and fixed sample

**Files:** Create `app/domain/model_benchmark_sample.py`, `app/api/routes/model_benchmarks.py`, `tests/api/test_model_benchmarks.py`; modify `app/api/main.py`.

**Interfaces:** `GET /model-benchmarks/sample`, `GET /model-benchmarks/accounts/{account_id}/models`, and `POST /model-benchmarks` returning `job_id` and `status`. The sample module exposes `SAMPLE_ID`, `SAMPLE_TEXT`, and `build_messages()`.

- [x] Write failing API tests for exact sample metadata, AI account discovery, invalid account, duplicate/unknown/out-of-range selection, and queued Job creation.
- [x] Run `uv run --extra dev python -m pytest tests/api/test_model_benchmarks.py -q` and observe failures.
- [x] Add fixed sample and route using existing `fetch_ai_models`, `WorkflowJobService.create`, and `workflow_runner.start`.
- [x] Run the same backend tests to green.

## Task 2: Sequential benchmark worker

**Files:** Create `app/services/model_benchmark_service.py`, `tests/services/test_model_benchmark_service.py`; adapt `app/api/routes/model_benchmarks.py` scheduling.

**Interfaces:** `ModelBenchmarkService.execute(job_id: str) -> None` reads account and model IDs from Job outputs and records ordered result rows. Each call uses `create_ai_client(account)` with only `text_model` changed on a local client.

- [x] Write failing backend tests for identical messages and order, independent timing, empty response, error continuation, safe persistence, overall statuses, and cancellation.
- [x] Run `uv run --extra dev python -m pytest tests/services/test_model_benchmark_service.py -q` and observe failures.
- [x] Implement the worker; update Job rows after each request and check cancellation before each next request.
- [x] Run the service and API tests to green.

## Task 3: Model Benchmark page

**Files:** Create `frontend/src/pages/ModelBenchmark.tsx`; modify `frontend/src/api/client.ts`, `frontend/src/App.tsx`, `frontend/src/components/Sidebar.tsx`, `frontend/src/components/Layout.tsx`.

**Interfaces:** The page uses saved AI accounts, benchmark discovery/start endpoints, and existing Job list/detail/cancel endpoints. Results render from `job.outputs.results`.

- [x] Add typed API functions and the page with account picker, Fetch models, ordered 2–5 selection, fixed sample preview, compact results table, recent runs, and cancel action.
- [x] Add route, sidebar entry, and page title.
- [x] Run `pnpm build` and `pnpm lint` with the installed Node 24 binary in PATH; resolve compile and lint errors.

## Task 4: Final verification

- [x] Run the full backend test suite: `uv run --extra dev python -m pytest -q`.
- [x] Run frontend build and lint only; do not run frontend tests.
- [x] Inspect `git diff` and `git status` for accidental changes, credentials, and generated translation content.
- [x] Report results and limitations; leave all files uncommitted on the current branch.
