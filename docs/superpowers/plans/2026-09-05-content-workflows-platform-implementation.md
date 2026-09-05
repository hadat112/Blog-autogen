# Content Workflows Platform — Implementation Plan

**Date:** 2026-09-05

**Status:** Ready to execute

**Source of truth:** `docs/superpowers/specs/2026-09-05-content-workflows-platform-design.md`

## 1. Delivery Contract

This plan adds four isolated workspaces—Rewrite Article, Pattern Library, Generate Story, and WordPress Publisher—without routing new behavior through `StoryOrchestrator` or changing the legacy Pipelines user flow.

Implementation rules:

- Keep every legacy test green at every checkpoint.
- Add characterization tests before extracting shared legacy behavior.
- Use additive, repeatable SQLite migrations and make a backup before the first upgrade from the current schema.
- Keep `translation_mode` and `translation_max_concurrency` as the only AI admission settings.
- New AI operations are single-attempt. Legacy retry/fallback behavior stays unchanged.
- No automated test may contact a real AI or WordPress endpoint.
- Do not add Vitest or React Testing Library. Frontend gates are ESLint, production build, and mocked Playwright journeys.
- Use provider-neutral names in new code. Keep the old `ninerouter` import only as a deprecated compatibility shim.
- Make small commits at the checkpoints below; do not combine independent feature lanes into one large commit.

Baseline commands:

```bash
uv run pytest -q
pnpm --dir frontend lint
pnpm --dir frontend build
```

Expected baseline: 94 backend tests pass, 3 skip; frontend lint and build pass.

## 2. Dependency and Parallelization Map

```text
Phase 0: behavior characterization
  └─ Phase 1A: migrations + data model
      ├─ Phase 1B: workflow profile/draft/job contracts
      ├─ Phase 1C: provider-neutral AI client + shared scheduler
      └─ Phase 1D: WordPress source/destination gateways
           └─ freeze shared contracts
               ├─ Lane A: Manual WordPress Publisher
               ├─ Lane B: Pattern Store + Pattern Library
               ├─ Lane C: Rewrite Article
               └─ Lane D: Dashboard + shared frontend shell
                    └─ Generate Story (requires Pattern Store APIs)
                         └─ Integrated release gate
```

After the shared contracts are frozen, Lanes A–D may be developed concurrently. AI calls are not made concurrently merely because code work is parallel: runtime admission always goes through the shared scheduler. Generate Story starts only after the Pattern Store query contracts are stable.

## 3. Phase 0 — Lock Existing Behavior

### Task 0.1 — Record the clean baseline

**Modify:** none.

1. Run all three baseline commands.
2. Save failures before implementation as pre-existing; do not weaken tests to accommodate them.
3. Confirm `git status --short` contains only the approved docs changes.

**Gate:** all baseline commands pass.

### Task 0.2 — Characterize the current AI integration

**Modify:**

- `tests/integrations/test_ai_9router.py`
- `tests/domain/test_story_orchestrator.py`

Add tests that freeze:

- current prompt/message construction;
- sequential and parallel translation results;
- `translation_max_concurrency` behavior;
- transient retry count and fallback-model selection;
- response parsing and error shape;
- existing imports of `NineRouterAI`.

Use fake sessions and synchronization primitives, never timing-only assertions.

**Gate:** `uv run pytest -q tests/integrations/test_ai_9router.py tests/domain/test_story_orchestrator.py`

### Task 0.3 — Characterize source fetch, publishing, and jobs

**Modify:**

- `tests/domain/test_article_importer.py`
- `tests/integrations/test_wp_rest.py`
- `tests/domain/test_pipeline_core.py`
- `tests/domain/test_job_runner.py`
- `tests/api/test_api_execution.py`

Add tests that freeze:

- normalized WordPress source fields and chunk boundaries;
- original repost and current best-effort image-upload failure;
- WordPress/Facebook/Telegram step ordering;
- job queue, progress, cancellation, rerun, and log output;
- the outer legacy AI job lock.

**Gate:** focused tests and then `uv run pytest -q`.

**Checkpoint commit:** `test: characterize legacy workflow behavior`

## 4. Phase 1 — Shared Backend Foundation

### Task 1.1 — Introduce versioned schema migrations and backup

**Create:**

- `app/db/migrations.py`
- `tests/db/test_migrations.py`

**Modify:**

- `app/api/main.py`
- `app/db/session.py`

Implementation:

1. Move every current inline inspection/ALTER operation from `main.py` into ordered migration functions.
2. Add `schema_migrations(version, applied_at)`.
3. Before the first migration of an existing SQLite file, use SQLite backup API to write `var/backups/story_autogen-<timestamp>.db`.
4. Skip the file backup for memory/non-SQLite/external DB URLs and emit an operator-facing log.
5. Run migrations before default language seeding and router startup.
6. Keep migration execution idempotent and transactional where supported.

Tests:

- empty database bootstrap;
- upgrade from a current-schema fixture;
- second run is a no-op;
- backup is created once and can be opened;
- external DB path takes the documented skip branch;
- old rows remain readable.

**Gate:** `uv run pytest -q tests/db/test_migrations.py tests/api/test_api_basic.py`

### Task 1.2 — Add workflow persistence models

**Modify:**

- `app/db/models.py`
- `app/db/migrations.py`
- `tests/domain/test_db_models.py`
- `tests/db/test_migrations.py`

Add:

- nullable/default-safe Job columns `workflow_type`, `parent_job_id`, `draft_id`, `outputs`;
- `ContentDraft` with the approved states, WordPress identifiers, timestamps, and optimistic `version`;
- `Article` with unique normalized source URL and analysis fields;
- `ThemeRule` with unique tag and JSON keywords;
- indexes for job workflow/status, draft kind/state/updated time, article status/processed time, and parent jobs.

Keep foreign keys nullable so old rows and deletion policies remain safe. Seed initial Theme Rules idempotently in the migration/seed layer.

**Gate:** model and migration tests, followed by full backend tests.

**Checkpoint commit:** `feat(db): add versioned workflow persistence`

### Task 1.3 — Add new API schemas and repositories

**Create:**

- `app/api/workflow_schemas.py`
- `app/api/pattern_schemas.py`
- `app/services/content_draft_service.py`
- `app/services/workflow_job_service.py`
- `app/domain/workflow_runner.py`
- `app/services/theme_rule_service.py`
- `app/services/article_service.py`
- `tests/services/test_content_draft_service.py`
- `tests/services/test_workflow_job_service.py`
- `tests/domain/test_workflow_runner.py`
- `tests/services/test_pattern_repositories.py`

**Modify:**

- `app/services/job_service.py`
- `app/api/schemas.py`

Implementation:

- Keep legacy schemas import-compatible; place new contracts in dedicated modules.
- Implement draft create/list/read/versioned update/delete and the approved state-transition table.
- Return `409` for stale versions.
- Prevent deletion while publishing or after WordPress creation; allow explicit cleanup of eligible local drafts/uploads.
- Add new job creation, parent-child relation, structured outputs, safe error messages, and computed capabilities.
- Add a runner for new workflow tasks with an active-task registry, cancellation, restart-safe terminal-state updates, and no dependency on the legacy runner's global lock. Workflow-specific services supply the task body; the runner owns only lifecycle and cleanup.
- Preserve legacy job serialization and derive legacy WordPress URL only from recognized success-log forms.
- Implement Article upsert/search/filter/sort/page and Theme Rule CRUD with normalized, unique keywords.

**Gate:** new service tests plus existing Job API tests.

### Task 1.4 — Add isolated workflow profile APIs

**Create:**

- `app/services/workflow_profile_service.py`
- `app/api/routes/workflow_profiles.py`
- `tests/api/test_api_workflow_profiles.py`

**Modify:**

- `app/services/pipeline_service.py`
- `app/api/routes/pipelines.py`
- `app/api/routes/__init__.py`
- `app/api/main.py`
- `tests/api/test_api_pipelines.py`

Implementation:

- Accept only `rewrite`, `generate_story`, and `wp_publish` through `/workflow-profiles`.
- Validate required AI/WP account types, language, category defaults, and settings per profile type.
- Resolve WordPress categories server-side without returning credentials.
- Filter all new types out of legacy `/pipelines` list/read/update/delete paths; reject attempts to create them through the old API.
- Add new prefixes to the SPA-fallback exclusion list.
- Return explicit conflicts when referenced accounts/categories make a mutation unsafe.

**Gate:** workflow profile tests, legacy pipeline tests, full backend suite.

**Checkpoint commit:** `feat(api): add isolated workflow contracts`

### Task 1.5 — Rename the AI client without breaking compatibility

**Create:**

- `app/integrations/ai/openai_compatible.py`
- `app/integrations/ai/scheduler.py`
- `tests/integrations/test_openai_compatible.py`
- `tests/integrations/test_ai_scheduler.py`

**Modify:**

- `app/integrations/ai/ninerouter.py`
- `app/integrations/ai/__init__.py`
- `app/integrations/ai/base.py`
- `app/domain/story_orchestrator.py`
- `app/domain/settings_manager.py`
- `tests/integrations/test_ai_9router.py`
- `README.md`

Implementation:

1. Move the implementation to `OpenAICompatibleAIClient` while preserving legacy methods byte-for-byte where practical.
2. Make `ninerouter.py` export a deprecated `NineRouterAI` alias/subclass only.
3. Add a provider-neutral `chat(messages, tools=None, request_policy=...)` response contract supporting text and tool calls.
4. Separate request policy: legacy calls retain retry/fallback; new workflow calls use one attempt and no fallback.
5. Add a thread-safe, account-keyed fair scheduler usable by both existing synchronous worker threads and new workflow tasks. Sequential means one active request; parallel means at most `translation_max_concurrency`.
6. Give foreground Rewrite/Generate waiters priority over background Pattern Analysis without starving a queued background task indefinitely.
7. Release permits on success, exception, timeout, and cancellation.
8. Route existing parallel translation calls through the scheduler without changing result ordering.
9. Continue reading legacy `ninerouter_` YAML settings, but only document/write generic endpoint, key, and model names.

Tests use barriers/events to prove limits, priority, account isolation, cancellation release, legacy policy, and new single-attempt policy.

**Gate:** AI-focused tests, orchestrator tests, then full backend suite.

### Task 1.6 — Extract WordPress gateways and strict publishing service

**Create:**

- `app/integrations/wordpress/__init__.py`
- `app/integrations/wordpress/source.py`
- `app/integrations/wordpress/destination.py`
- `app/services/wordpress_publishing_service.py`
- `tests/integrations/test_wordpress_gateways.py`
- `tests/services/test_wordpress_publishing_service.py`

**Modify:**

- `app/domain/article_importer.py`
- `app/integrations/publishers/wordpress.py`
- `tests/domain/test_article_importer.py`
- `tests/integrations/test_wp_rest.py`

Implementation:

- Extract raw source fetch into a normalized result contract while retaining the legacy importer facade and output.
- Extract category, streamed image fetch/upload, post create, and post update primitives.
- Keep legacy publisher behavior—including best-effort image handling—unchanged.
- Implement strict new-workflow publication with a per-draft lock, state guard, media reuse, structured outputs, and distinct `publish_failed`/`publish_unknown` results.
- Enforce remote URL scheme/credentials/redirect/timeout/MIME/10 MiB rules and local upload MIME/size/unique-path rules.
- Never log credentials, content bodies, raw image bytes, or full provider payloads.

Tests cover definite failures, ambiguous timeouts, duplicate submits, concurrent submits, media reuse, and legacy compatibility.

**Gate:** focused WordPress tests, full backend suite.

**Checkpoint commit:** `refactor: add shared AI and WordPress gateways`

### Task 1.7 — Freeze shared contracts

Before feature lanes begin:

1. Run backend tests twice, including a migration upgrade twice against a copied current database fixture.
2. Review all changes to `StoryOrchestrator`, `job_runner.py`, `article_importer.py`, and the legacy publisher against Phase 0 characterization tests.
3. Record the stable request/response shapes in docstrings and OpenAPI examples.
4. Do not rename shared fields after feature lanes start without updating every lane in the same commit.

**Gate:** baseline commands pass.

## 5. Shared Frontend Foundation (Lane D, may run after Task 1.4)

### Task 2.1 — Add typed clients and scoped reusable components

**Create:**

- `frontend/src/api/workflows.ts`
- `frontend/src/api/patterns.ts`
- `frontend/src/features/workflows/types.ts`
- `frontend/src/components/ui/Textarea.tsx`
- `frontend/src/components/ui/Tabs.tsx`
- `frontend/src/components/ui/InlineStatus.tsx`
- `frontend/src/components/ui/CopyButton.tsx`
- `frontend/src/components/ui/ProgressTimeline.tsx`
- `frontend/src/features/workflows/ProfileSelector.tsx`
- `frontend/src/features/workflows/ProfileManager.tsx`
- `frontend/src/features/workflows/DraftEditor.tsx`
- `frontend/src/features/workflows/DraftHistory.tsx`

**Modify:**

- `frontend/src/api/types.ts`
- `frontend/src/api/client.ts`
- `frontend/src/index.css`

Requirements:

- Keep API modules split by domain and re-use the existing Axios instance.
- Use controlled fields, real labels, visible focus, inline validation, `role=alert`, and polite live regions.
- `CopyButton` handles clipboard denial and provides a manual-selection fallback.
- Components use existing Zinc/Emerald tokens and Lucide icons; no global legacy restyle.
- Editors preserve unsaved text during query refreshes and expose version conflicts explicitly.
- Responsive behavior works without horizontal scroll at 375 px.

**Gate:** `pnpm --dir frontend lint && pnpm --dir frontend build` (run as two commands if the shell/tool requires it).

### Task 2.2 — Add routes and sectioned navigation

**Create:**

- `frontend/src/pages/RewriteArticle/index.tsx`
- `frontend/src/pages/GenerateStory/index.tsx`
- `frontend/src/pages/PatternLibrary/index.tsx`
- `frontend/src/pages/WordPressPublisher/index.tsx`

Create typed route shells wired to loading/error/empty states; feature mutations are added in their owning lanes.

**Modify:**

- `frontend/src/App.tsx`
- `frontend/src/components/Sidebar.tsx`
- `frontend/src/components/Layout.tsx`

Group navigation into Overview, Content Workflows, and Configuration. Preserve the current mobile drawer, active-route styling, dark mode, and legacy URLs. Add accessible collapsed-nav tooltips.

**Gate:** frontend lint/build plus manual route smoke at desktop and mobile widths.

**Checkpoint commit:** `feat(frontend): add workflow shell and shared components`

## 6. Lane A — Manual WordPress Publisher

### Task 3.1 — Add manual draft and publishing endpoints

**Create:**

- `app/api/routes/content_drafts.py`
- `tests/api/test_api_content_drafts.py`

**Modify:**

- `app/api/main.py`
- `app/api/routes/__init__.py`
- `app/services/content_draft_service.py`
- `app/services/wordpress_publishing_service.py`

Implement:

- list/filter, create, read, versioned update, eligible delete;
- multipart upload to a unique `var/uploads/` path and URL image mode, mutually exclusive;
- plain-text paragraph normalization and explicit HTML pass-through;
- category resolution for the selected profile;
- publish endpoint with Draft default, Publish-now confirmation token, strict image behavior, lock/idempotency, structured Job outputs, and cleanup rules.

Do not sanitize the stored HTML into a different payload; sanitize only the browser preview. Reject scripts/unsafe preview behavior client-side and rely on WordPress permissions/content policy for the submitted HTML.

**Gate:** content-draft API/service/WordPress tests and full backend suite.

### Task 3.2 — Build the WordPress Publisher workspace

**Create:**

- `frontend/src/pages/WordPressPublisher/PublisherForm.tsx`
- `frontend/src/pages/WordPressPublisher/ContentPreview.tsx`
- `frontend/src/pages/WordPressPublisher/PublishResult.tsx`
- `frontend/src/features/workflows/useDraftAutosave.ts`

**Modify:**

- `frontend/src/pages/WordPressPublisher/index.tsx`
- `frontend/src/api/workflows.ts`

UI:

- profile create/select/edit;
- required title/content and category selector;
- exactly one optional image mode (upload or URL), with type/size feedback;
- Plain text/HTML selector and Write/sanitized Preview tabs;
- persistent local draft/history and conflict-safe save status;
- WordPress Draft default and confirmed Publish now;
- result panel with Copy Link only.

Use DOMPurify for preview sanitization and update `frontend/package.json` plus the lockfile. Never use raw `dangerouslySetInnerHTML` with unsanitized content.

**Gate:** frontend lint/build and manual mocked-API smoke.

**Checkpoint commit:** `feat: add manual WordPress publisher workflow`

## 7. Lane B — Pattern Store and Pattern Library

### Task 4.1 — Implement deterministic collection and background analysis

**Create:**

- `app/domain/theme_matcher.py`
- `app/domain/pattern_analyzer.py`
- `app/services/pattern_collection_service.py`
- `tests/domain/test_theme_matcher.py`
- `tests/domain/test_pattern_analyzer.py`
- `tests/services/test_pattern_collection_service.py`

**Modify:**

- `app/services/workflow_job_service.py`
- `app/domain/story_orchestrator.py`
- `app/domain/job_runner.py`

Implementation:

- Normalize source URLs and upsert deterministic title, word count, tags, and timestamps.
- Enqueue `pattern_analysis` as a low-priority child Job only when `collect_patterns` is true.
- Never await the child from its parent and never propagate its error to the parent.
- Send the complete article once; require the approved JSON structure; use the single-attempt request policy.
- Persist pending/processing/completed/failed safely across restart.
- Add one generic, optional `source_article_callback` boundary to `StoryOrchestrator`, invoked after raw fetch succeeds and before publication. It only emits the normalized raw article; it contains no Pattern-specific condition. `JobRunner` wires the callback when the pipeline setting explicitly enables collection, and the callback hands work to `PatternCollectionService` and the new workflow runner.

**Gate:** matching, isolation, parent-child, restart, and failure tests plus legacy execution tests.

### Task 4.2 — Add Pattern, Theme Rule, and Collection Source APIs

**Create:**

- `app/api/routes/patterns.py`
- `app/api/routes/theme_rules.py`
- `app/api/routes/pattern_collection_sources.py`
- `tests/api/test_api_patterns.py`
- `tests/api/test_api_theme_rules.py`
- `tests/api/test_api_pattern_collection_sources.py`

**Modify:**

- `app/api/main.py`
- `app/api/routes/__init__.py`

Implement every endpoint in the approved spec, including summary metrics, validated sort fields, bounded pagination, safe errors, explicit retry eligibility, delete confirmation at UI level, Theme Rule CRUD, and boolean opt-in for eligible legacy/Rewrite profiles. Default all missing `collect_patterns` settings to false.

**Gate:** focused API tests and full backend suite.

### Task 4.3 — Build Pattern Library

**Create:**

- `frontend/src/pages/PatternLibrary/SummaryCards.tsx`
- `frontend/src/pages/PatternLibrary/ArticleTable.tsx`
- `frontend/src/pages/PatternLibrary/ArticleDetails.tsx`
- `frontend/src/pages/PatternLibrary/ThemeRules.tsx`
- `frontend/src/pages/PatternLibrary/CollectionSources.tsx`

**Modify:**

- `frontend/src/pages/PatternLibrary/index.tsx`
- `frontend/src/api/patterns.ts`

Implement metrics, Articles/Theme Rules tabs, debounced search, filters, safe sorting/pagination, details drawer, retry/delete confirmations, rule create/edit/enable/delete, and collection-source toggles. Keep table actions keyboard accessible and stack filters at mobile widths.

**Gate:** frontend lint/build and mocked-API manual smoke.

**Checkpoint commit:** `feat: add pattern collection and library`

## 8. Lane C — Rewrite Article

### Task 5.1 — Implement sequential rewrite engine and validation

**Create:**

- `app/domain/rewrite_engine.py`
- `app/domain/content_validation.py`
- `tests/domain/test_rewrite_engine.py`
- `tests/domain/test_content_validation.py`

Implementation tests must prove:

- source uses the shared raw gateway and current chunker;
- one article's chunks execute sequentially even in parallel mode;
- previous rewritten chunks are assistant messages;
- prior original chunks never reappear in later turns;
- the exact `Continue.` placeholder is inserted only when provider compatibility requires it;
- title/caption request uses the constructed conversation;
- caption is an exact content prefix;
- malformed JSON/provider/429/network errors fail once without fallback;
- 70%–130% length produces a review warning, not failure.

### Task 5.2 — Add Rewrite service and API

**Create:**

- `app/services/rewrite_workflow_service.py`
- `app/api/routes/rewrite_jobs.py`
- `tests/services/test_rewrite_workflow_service.py`
- `tests/api/test_api_rewrite_jobs.py`

**Modify:**

- `app/api/main.py`
- `app/api/routes/__init__.py`
- `app/services/workflow_job_service.py`
- `app/services/content_draft_service.py`

Implement Job/draft creation, progress steps, cancellation boundaries, source fetch, optional fire-and-forget pattern collection, scheduler admission, generation failure persistence, review state, editable draft, publish confirmation, strict WordPress-only publication, Copy Caption eligibility, and Copy Link outputs.

Unrelated Rewrite jobs may overlap within the account scheduler limit. A failed job must not cancel another job.

**Gate:** rewrite unit/service/API tests and full backend suite.

### Task 5.3 — Build Rewrite workspace

**Create:**

- `frontend/src/pages/RewriteArticle/RewriteSetup.tsx`
- `frontend/src/pages/RewriteArticle/RewriteReview.tsx`

**Modify:**

- `frontend/src/pages/RewriteArticle/index.tsx`
- `frontend/src/api/workflows.ts`
- shared workflow editor/history components as narrowly required

Use the approved split workspace: profile and source/progress on the left; persistent title/content/caption/category/image review on the right; history below/drawer. Validate caption prefix before copy/publish, show word-count warning, confirm publication, and expose Copy Caption plus Copy Link only after WordPress success.

**Gate:** frontend lint/build and mocked-API manual smoke at 375/768/1440 px.

**Checkpoint commit:** `feat: add review-first article rewrite workflow`

## 9. Dashboard Integration (Lane D)

### Task 6.1 — Extend Job API responses and legacy URL fallback

**Modify:**

- `app/api/schemas.py`
- `app/services/job_service.py`
- `app/api/routes/jobs.py`
- `tests/api/test_api_execution.py`
- `tests/api/test_api_basic.py`

Return workflow type, parent/draft IDs, structured outputs, and computed capabilities. Parse a URL from only recognized legacy WordPress success log patterns when `outputs.wp_url` is absent. Keep old fields unchanged and do not infer copy capability from arbitrary URLs.

**Gate:** Job API tests and full backend suite.

### Task 6.2 — Add workflow badges and Copy Link to current Job UI

**Modify:**

- `frontend/src/api/types.ts`
- `frontend/src/pages/Dashboard/index.tsx`
- `frontend/src/pages/Dashboard/components/JobCard.tsx`
- `frontend/src/pages/Dashboard/components/JobDetailsModal.tsx`

Render server capabilities rather than reconstructing them. Add workflow badges/filters and Copy Link to both card and details. Stop event propagation from copy, announce result, retain legacy rerun/cancel behavior, and link new failed jobs back to their owning workflow screen.

**Gate:** frontend lint/build and manual checks for legacy/new job payloads.

**Checkpoint commit:** `feat(dashboard): expose workflow jobs and WordPress links`

## 10. Generate Story — Depends on Lane B

### Task 7.1 — Implement read-only agent tools

**Create:**

- `app/domain/story_agent_tools.py`
- `tests/domain/test_story_agent_tools.py`

Implement exactly:

- `list_themes() -> [{theme, count}]`
- `get_examples(theme, n) -> [{title, structure}]`

Validate tool name and JSON arguments, clamp `n` to 10, return no full original text, filter unusable structures, and produce deterministic ordering for tests.

**Gate:** tool tests plus Pattern repository tests.

### Task 7.2 — Implement bounded story agent

**Create:**

- `app/domain/story_agent.py`
- `tests/domain/test_story_agent.py`

Implementation:

- Probe/use chat tool definitions through the shared client; a tool-unsupported provider error is terminal and actionable.
- Execute turns sequentially under scheduler admission.
- Permit only the two registered tools and at most six tool calls total.
- Require final JSON `title`, `story`, `caption`.
- Validate 1500–4000 words and exact caption prefix; language remains prompt-enforced and review-confirmed.
- Never retry, switch model, generate an image, or request source full text.

Test unknown tools, invalid args, repeated calls, six-call boundary, seventh-call failure, malformed final JSON, invalid length/prefix, unsupported tools, and cancellation.

### Task 7.3 — Add Generate service and API

**Create:**

- `app/services/generate_story_workflow_service.py`
- `app/api/routes/generation_jobs.py`
- `tests/services/test_generate_story_workflow_service.py`
- `tests/api/test_api_generation_jobs.py`

**Modify:**

- `app/api/main.py`
- `app/api/routes/__init__.py`
- `app/services/workflow_job_service.py`
- `app/services/content_draft_service.py`

Implement Job/draft lifecycle, tool-progress events, safe failures, review persistence, edit/version behavior, WordPress-only confirmed publish, structured outputs, Copy Caption, and Copy Link. Independent jobs may overlap only through scheduler permits.

**Gate:** Generate tests and full backend suite.

### Task 7.4 — Build Generate Story workspace

**Create:**

- `frontend/src/pages/GenerateStory/GenerationSetup.tsx`
- `frontend/src/pages/GenerateStory/AgentProgress.tsx`
- `frontend/src/pages/GenerateStory/GenerationReview.tsx`

**Modify:**

- `frontend/src/pages/GenerateStory/index.tsx`
- `frontend/src/api/workflows.ts`

Use the split layout, showing model/tool progress without exposing hidden reasoning. Provide profile manager, review editor/history, exact validation messages, publish confirmation, and post-success Copy Caption/Copy Link. Do not add theme/example inputs.

**Gate:** frontend lint/build and mocked-API manual smoke.

**Checkpoint commit:** `feat: add pattern-guided story generation workflow`

## 11. Browser Journeys Without Vitest

### Task 8.1 — Add Playwright harness

**Create:**

- `frontend/playwright.config.ts`
- `frontend/e2e/helpers/mockApi.ts`
- `frontend/e2e/rewrite.spec.ts`
- `frontend/e2e/pattern-library.spec.ts`
- `frontend/e2e/generate-story.spec.ts`
- `frontend/e2e/wordpress-publisher.spec.ts`
- `frontend/e2e/dashboard.spec.ts`

**Modify:**

- `frontend/package.json`
- `frontend/pnpm-lock.yaml`
- `.gitignore`

Add Playwright only; do not add Vitest, jsdom, RTL, or unit-test setup. All journeys intercept API calls.

Cover:

- Rewrite failure/recovery/edit/publish/copy actions;
- Pattern filters/details/retry/delete/rule CRUD/source toggle;
- Generate tool progress/validation/review/publish/copy;
- manual file/URL exclusivity, format preview, Draft/Publish confirmation, Copy Link only;
- Dashboard legacy/new capabilities and both Copy Link locations;
- keyboard focus, reduced motion, light/dark, and 375/768/1440 px viewports.

Add scripts `test:e2e` and `test:e2e:install` with documented browser installation. Avoid screenshot goldens unless a stable visual defect requires one.

**Gate:** frontend lint, build, and `pnpm --dir frontend test:e2e`.

**Checkpoint commit:** `test(frontend): cover workflow browser journeys`

## 12. Documentation, Packaging, and Release

### Task 9.1 — Update operator and user documentation

**Modify:**

- `README.md`
- `packaging/PACKAGING_GUIDE.md`
- `packaging/mac/README_MAC.txt`
- `packaging/windows/README_WINDOWS.txt`

Document:

- AI Provider endpoint/key/model terminology and legacy YAML compatibility;
- migration backup location and recovery procedure;
- new workflow profile ownership and navigation;
- AI sequential/parallel behavior and rate-limit implications;
- strict publish failure vs `publish_unknown` recovery;
- local upload lifecycle;
- Playwright prerequisites and test commands.

### Task 9.2 — Verify packaging includes new modules and runtime directories

**Modify only if required by verification:**

- `packaging/app_launcher.py`
- `packaging/build_mac_release.command`
- `packaging/build_windows_release.command`
- installer scripts

Verify builds include the new Python packages, compiled frontend, default Theme Rule seed, and writable `var/backups`/`var/uploads` creation. Never bundle local DBs, uploads, credentials, or backups.

**Gate:** packaging dry-run/check appropriate to the current OS and both baseline frontend commands.

### Task 9.3 — Final impact review and release matrix

Review these files line-by-line against the approved spec and Phase 0 tests:

- `app/domain/story_orchestrator.py`
- `app/domain/job_runner.py`
- `app/domain/article_importer.py`
- `app/integrations/ai/openai_compatible.py`
- `app/integrations/ai/ninerouter.py`
- `app/integrations/publishers/wordpress.py`
- `app/api/main.py`
- `app/services/pipeline_service.py`
- `frontend/src/pages/Pipelines/**`
- `frontend/src/pages/Dashboard/**`

Run:

```bash
uv run pytest -q
pnpm --dir frontend lint
pnpm --dir frontend build
pnpm --dir frontend test:e2e
```

Then perform a manual smoke test with non-production accounts:

1. Legacy translate/crawl run, cancel, rerun, and original repost.
2. Rewrite to review, refresh recovery, edit, publish, Copy Caption, Copy Link.
3. Pattern opt-in where analysis fails while parent succeeds; retry from Library.
4. Generate with supported and unsupported tool-call models.
5. Manual WP Draft and Publish now using upload and URL images.
6. Forced ambiguous WordPress timeout and reconciliation guidance.
7. Dashboard cards/details for old and new jobs.
8. Light/dark and 375/768/1024/1440 px layouts.

Confirm no automated test made an external request, no new workflow invoked Facebook, and no new profile appears in the legacy Pipelines screen.

**Checkpoint commit:** `docs: finalize content workflows rollout guidance`

## 13. Completion Checklist

- [ ] Phase 0 characterization protects every shared extraction.
- [ ] Database backup and repeatable migrations are verified on a current-schema fixture.
- [ ] Legacy and new workflow profiles are isolated at both API and UI layers.
- [ ] Provider-neutral AI naming is complete; deprecated import remains compatible.
- [ ] One account-keyed scheduler enforces the existing sequential/parallel settings.
- [ ] New AI operations perform one attempt with no model/prompt fallback.
- [ ] Manual Publisher creates persistent drafts and returns Copy Link only.
- [ ] Pattern Analysis is a low-priority child and cannot alter parent outcome.
- [ ] Rewrite never resends previous original chunks and requires review.
- [ ] Generate uses only two tools, at most six tool calls, and no source full text.
- [ ] Strict new publication prevents duplicate posts and distinguishes ambiguous state.
- [ ] Dashboard shows Copy Link in card/details, including recognized legacy fallback.
- [ ] No Vitest/RTL dependency or configuration was added.
- [ ] Backend, lint, build, Playwright, packaging, responsive, and manual gates pass.
- [ ] Final diff contains no unrelated refactor and no credential/content leakage.
