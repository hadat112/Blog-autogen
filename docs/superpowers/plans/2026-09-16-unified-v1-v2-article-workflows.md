# Unified V1 & V2 Article Workflows Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Unify the article processing pipelines (V1 translation and V2 rewrite) into a single cohesive service (`ArticleWorkflowService`) where all pre- and post-processing steps (URL validation, source ingestion, pattern collection, draft persistence, multi-channel publishing, cancellation, error sanitization, and retries) are shared, with only Step 3 branching into V1 (Translate) or V2 (Rewrite).

**Architecture:** A unified workflow service `ArticleWorkflowService` executes jobs in 5 standardized steps:
1. Input & Pipeline Account Validation (checking required AI & WP accounts, optional FB & TG accounts).
2. Source Ingestion via `WordPressSourceGateway` and draft record creation with `ContentDraft`.
3. AI Processing (Step 3 branching: Mode V1 uses deterministic translation with sliding context; Mode V2 uses `RewriteEngine` with multi-turn conversation history).
4. Draft Assembly & Quality Validation (length ratio and caption prefix checks).
5. Multi-Channel Publishing Hub (mandatory WordPress publishing, followed by optional Facebook and Telegram notifications).

**Tech Stack:** Python 3.11/FastAPI, SQLAlchemy, SQLite, React/TypeScript, Vite, TanStack Query, TailwindCSS.

## Global Constraints

- Never commit changes to git until user explicitly checks (as instructed by user).
- In the UI, labels must remain simple `V1` and `V2` without verbose descriptions.
- The input field must strictly accept source article URLs (`http://` or `https://`).
- `ContentDraft` must always be created and updated for both V1 and V2.
- WordPress publishing is mandatory; Facebook and Telegram publishing are optional based on pipeline configuration.

---

### Task 1: Unified Service Implementation (`ArticleWorkflowService`)

**Files:**
- Create: `app/services/article_workflow_service.py`
- Modify: `app/domain/story_orchestrator.py`
- Test: `tests/services/test_article_workflow_service.py`

**Interfaces:**
- Consumes:
  - `WordPressSourceGateway.fetch(source_url: str)`
  - `PatternCollectionService(db).collect(...)`
  - `RewriteEngine(ai_client).rewrite(title, content, language, on_progress)`
  - `OpenAICompatibleAIClient.translate_article_fields(title, content, image_url, language, progress_callback)`
  - `WordPressPublishingService(db).publish(draft_id, confirmed=True)`
  - `FacebookPagePublisher(page_id, access_token).publish(...)`
  - `send_telegram_msg(bot_token, chat_id, message)`
  - `sanitize_error(error_str)`
- Produces:
  - `ArticleWorkflowService.execute(job_id: str, draft_id: str, mode: str, source_gateway=None)`

- [ ] **Step 1: Write tests for `ArticleWorkflowService`**
  Write tests in `tests/services/test_article_workflow_service.py` covering:
  - V1 execution with mock AI client and publisher.
  - V2 execution with mock RewriteEngine and publisher.
  - Cancellation mid-flight raising `InterruptedError`.
  - Multi-channel publishing (WP + FB + TG).
  - Sanitized error handling on AI failure.

- [ ] **Step 2: Run test to verify it fails**
  Run `pytest tests/services/test_article_workflow_service.py` to confirm failure (service not yet created).

- [ ] **Step 3: Implement `ArticleWorkflowService`**
  Create `app/services/article_workflow_service.py` containing the 5-step pipeline execution and real-time cancellation check.

- [ ] **Step 4: Run test to verify it passes**
  Run `pytest tests/services/test_article_workflow_service.py` to confirm all tests pass.

---

### Task 2: API Endpoints & Backward Compatibility

**Files:**
- Create: `app/api/routes/article_workflows.py`
- Modify: `app/api/main.py`
- Modify: `app/api/workflow_schemas.py`
- Modify: `app/api/routes/rewrite_jobs.py`
- Modify: `app/api/routes/pipelines.py`
- Test: `tests/api/test_article_workflows.py`

**Interfaces:**
- Consumes:
  - `ArticleWorkflowService`
  - `WorkflowJobService`
- Produces:
  - `POST /article-workflows/run` -> `{ job_id, draft_id, status }`
  - `POST /article-workflows/{id}/retry` -> `{ job_id, draft_id, status }`

- [ ] **Step 1: Write API tests**
  Write tests in `tests/api/test_article_workflows.py` verifying:
  - Starting V1 and V2 runs with a valid pipeline and source URL.
  - Rejecting non-URL inputs or missing accounts.
  - Retrying a failed job.
  - Compatibility with legacy `/rewrite-jobs` endpoint.

- [ ] **Step 2: Implement schemas and routes**
  Implement `ArticleWorkflowRunInput` and route handlers in `app/api/routes/article_workflows.py`.
  Register in `app/api/main.py`.
  Update `/rewrite-jobs` and `/pipelines/{id}/run` to delegate to `ArticleWorkflowService`.

- [ ] **Step 3: Run tests to verify they pass**
  Run `pytest tests/api/test_article_workflows.py` and `pytest tests/api/test_api_workflows.py`.

---

### Task 3: Frontend Client & Dashboard QuickRun Update

**Files:**
- Modify: `frontend/src/api/workflows.ts`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/pages/Dashboard/components/QuickRun.tsx`
- Modify: `frontend/src/pages/Dashboard/components/JobCard.tsx`
- Modify: `frontend/src/pages/Dashboard/components/JobDetailsModal.tsx`
- Modify: `frontend/src/components/ui/ProgressTimeline.tsx`
- Modify: `frontend/src/pages/Dashboard/index.tsx`
- Test: `frontend/e2e/rewrite.spec.ts`

**Interfaces:**
- Consumes:
  - `startArticleWorkflow(pipelineId, sourceUrl, mode, rerunFromJobId)`
- Produces:
  - Unified QuickRun UI with simple `V1` and `V2` toggle buttons.
  - Strict URL validation and helpful URL placeholder.
  - Standardized Timeline display and Retry button for all failed jobs.

- [ ] **Step 1: Update frontend API clients**
  Add `startArticleWorkflow` in `frontend/src/api/workflows.ts`.

- [ ] **Step 2: Update QuickRun component**
  Enforce clean `V1` / `V2` toggle, source URL validation, and call `startArticleWorkflow`.

- [ ] **Step 3: Update JobCard, JobDetailsModal, and ProgressTimeline**
  Support tags `V1` and `V2`, uniform step timeline, and retry action.

- [ ] **Step 4: Verify frontend build and tests**
  Run `pnpm build` in `frontend/` directory to verify TypeScript types and bundle compilation.

---

### Task 4: Full System Verification & Regression Testing

**Files:**
- Run all backend tests: `pytest`
- Run frontend typecheck/build: `pnpm build`

- [ ] **Step 1: Run comprehensive backend test suite**
  Run `pytest tests/` to confirm zero regressions across all services.

- [ ] **Step 2: Run frontend production build**
  Run `pnpm build` in `frontend/` to confirm zero lint/type errors.

- [ ] **Step 3: Audit all requirements**
  Confirm:
  - Only Step 3 branches between V1 and V2.
  - All other steps are completely unified.
  - No new git commits were made.
  - Goal complete.
