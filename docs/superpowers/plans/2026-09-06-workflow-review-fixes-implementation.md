# Workflow Review Fixes — Implementation Plan

**Date:** 2026-09-06

**Source:** `docs/superpowers/specs/2026-09-06-workflow-review-fixes-design.md`

## Delivery Rules

- Keep caption comparison exact but informational.
- Never spend an additional AI request to repair a caption.
- Preserve the rule that prior original Rewrite chunks are not resent.
- Reuse the current Job cancellation API and terminal-state guards.
- Do not migrate the Pattern worker to another runner in this change.
- Do not add a database migration, Vitest, or React Testing Library.
- Automated tests must mock AI and WordPress.

## Phase 1 — Caption Comparison Becomes Metadata

### Backend

Modify:

- `app/domain/content_validation.py`
- `app/domain/rewrite_engine.py`
- `app/domain/story_agent.py`
- `app/services/rewrite_workflow_service.py`
- `app/services/generate_story_workflow_service.py`
- `app/services/wordpress_publishing_service.py`

Tests:

- `tests/domain/test_rewrite_engine.py`
- `tests/domain/test_story_agent.py`
- `tests/services/test_wordpress_publishing_service.py`

Steps:

1. Replace the throwing prefix helper with a simple boolean comparison helper. Keep empty caption validation separate and blocking.
2. Return `caption_matches_prefix` from Rewrite and Generate validation results.
3. Add a warning when the flag is false; do not mutate content or caption.
4. Persist the flag/warning in the owning Job outputs so it survives refresh.
5. Remove the caption-prefix publication guard because WordPress does not receive caption.
6. Test exact match, mismatch success, empty caption failure, and publication with a mismatched caption.

### Frontend

Modify:

- `frontend/src/api/types.ts`
- `frontend/src/features/workflows/DraftEditor.tsx`

Steps:

1. Keep `content.startsWith(caption)` as a local display calculation.
2. Render `Caption matched` or `Caption differs from story opening` beside the Caption field.
3. Use neutral/success styling for a match and warning styling for a mismatch.
4. Do not disable Save, Publish, or Copy Caption on mismatch.
5. Keep title, content, and caption fully editable.

Gate:

```bash
uv run pytest -q tests/domain/test_rewrite_engine.py tests/domain/test_story_agent.py tests/services/test_wordpress_publishing_service.py
cd frontend && ./node_modules/.bin/tsc --noEmit
cd frontend && pnpm lint
```

Checkpoint commit: `fix: make caption prefix comparison informational`

## Phase 2 — Portable Rewrite Message History

Modify:

- `app/domain/rewrite_engine.py`
- `tests/domain/test_rewrite_engine.py`

Steps:

1. Change `_history_messages` to emit one user prompt before every historical assistant response.
2. Use `Begin the rewritten story.` for the first historical pair and exact `Continue.` placeholders for later pairs.
3. Append the current source-chunk request only after the alternating history.
4. Use the same history builder for the final title/caption request.
5. Assert message roles alternate after system.
6. Assert previous original chunks never appear in later chunk or metadata requests.
7. Assert the current original chunk appears exactly once in its own request.

Gate:

```bash
uv run pytest -q tests/domain/test_rewrite_engine.py tests/integrations/test_openai_compatible.py
```

Checkpoint commit: `fix: alternate rewrite conversation roles`

## Phase 3 — Cancel From Rewrite and Generate Screens

Modify:

- `frontend/src/pages/RewriteArticle/index.tsx`
- `frontend/src/pages/GenerateStory/index.tsx`
- `frontend/e2e/rewrite.spec.ts`
- `frontend/e2e/generate-story.spec.ts`
- `frontend/e2e/helpers/mockApi.ts`

Backend verification:

- `app/domain/workflow_runner.py`
- `app/services/workflow_job_service.py`
- `tests/services/test_workflow_job_service.py`

Steps:

1. Reuse `cancelJob` from the existing API client.
2. Add a cancellation mutation to each workflow page.
3. Show a compact Cancel button for `queued` and `running` jobs only.
4. Disable the button while cancelling and show an inline API error on failure.
5. On success, refetch Job, active draft, and draft history.
6. Display cancelled Job status in the progress card and preserve the recoverable draft.
7. Add Playwright coverage for visible button, API call, terminal UI state, and disappearance of the button.
8. Keep the existing backend late-result guard test green; add a draft-state assertion if coverage is missing.

Gate:

```bash
uv run pytest -q tests/services/test_workflow_job_service.py
cd frontend && pnpm test:e2e -- e2e/rewrite.spec.ts e2e/generate-story.spec.ts
```

Checkpoint commit: `feat(frontend): cancel active content workflows in place`

## Phase 4 — Eligible Pattern Retry Sources

Modify:

- `app/api/routes/pattern_collection_sources.py`
- `app/api/routes/patterns.py`
- `frontend/src/api/patterns.ts`
- `frontend/src/pages/PatternLibrary/index.tsx`
- `tests/api/test_api_workflows.py` or a focused Pattern source API test
- `frontend/e2e/pattern-library.spec.ts`

Steps:

1. Compute `can_analyze` from pipeline active status and a referenced, existing `ai` account.
2. Return only the boolean capability; do not expose the AI account ID or config.
3. Revalidate the same conditions in the retry endpoint, including active pipeline status and account type.
4. Extend the frontend `CollectionSource` type.
5. Derive the selected source from the user's choice or the first eligible source; never default to an ineligible source.
6. Render ineligible options disabled with `AI account required`.
7. Disable Retry when no eligible source exists and show recovery guidance.
8. Add mutation error handling and render the safe backend message inline.
9. Test active/inactive, missing-account, wrong-account-type, default selection, and retry error cases.

Gate:

```bash
uv run pytest -q tests/api/test_api_workflows.py
cd frontend && pnpm test:e2e -- e2e/pattern-library.spec.ts
```

Checkpoint commit: `fix: select eligible pattern analysis sources`

## Phase 5 — Integrated Release Gate

1. Review the final diff for changes outside the approved files.
2. Confirm no new workflow invokes Facebook and no credentials appear in API responses/logs.
3. Confirm caption mismatch is visible but non-blocking after refresh.
4. Confirm cancellation cannot be overwritten by a late worker response.
5. Run all release checks:

```bash
uv run pytest -q
cd frontend && ./node_modules/.bin/tsc --noEmit
cd frontend && pnpm lint
cd frontend && pnpm build
cd frontend && pnpm test:e2e
git diff --check
```

6. Confirm `git status --short` contains only intended changes, then create the final commit if checkpoint commits were not used.

## Completion Checklist

- [ ] Caption mismatch produces a warning, never generation failure.
- [ ] Empty caption still fails validation.
- [ ] Caption mismatch does not block WordPress publish or Copy Caption.
- [ ] Rewrite history alternates roles and never resends prior source chunks.
- [ ] Rewrite and Generate screens cancel queued/running Jobs directly.
- [ ] Cancelled Jobs/drafts reach stable terminal states.
- [ ] Pattern retry defaults only to an active AI-backed source.
- [ ] Pattern retry errors are visible inline.
- [ ] Backend, TypeScript, lint, build, and Playwright gates pass.
- [ ] Worktree contains no unrelated changes.
