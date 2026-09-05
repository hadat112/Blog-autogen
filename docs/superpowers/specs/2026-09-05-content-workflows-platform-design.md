# Content Workflows Platform — Design Specification

**Date:** 2026-09-05

**Status:** Ready for user review

**Supersedes as implementation source:** `docs/spec-1.md`, `docs/spec-2.md`, and `docs/spec-3.md`

## 1. Purpose

Extend Story Autogen with four isolated, reusable content workflows while preserving the current translation, crawl, publishing, rerun, and cancellation behavior:

1. Rewrite a fetched WordPress drama article into a substantially new localized story.
2. Collect article themes and narrative structures into the existing SQLite database.
3. Generate a new story from stored patterns with an AI tool-calling loop.
4. Publish manually supplied content to WordPress from one dedicated screen.

Each workflow has its own route and screen. New workflows share narrow infrastructure contracts, not orchestration branches. Existing screens continue to serve existing pipelines.

## 2. Confirmed Product Decisions

- Use separate screens for Rewrite, Pattern Library, Generate Story, and WordPress Publisher.
- Store new workflow profiles in the existing `pipelines` table with new type values.
- Create and edit new profiles inside their corresponding screens. Do not expose them in the legacy Pipelines screen.
- Keep all job monitoring in the existing Job system and Dashboard.
- Save generated/reworked content persistently before review and publication.
- Require review before publishing Rewrite or Generate Story output.
- New workflows publish only to WordPress. They never invoke the Facebook publisher.
- Published Rewrite and Generate Story items expose `Copy Caption` and `Copy Link`.
- Manual WordPress Publisher items expose only `Copy Link`.
- Pattern collection is opt-in per source-capable pipeline and defaults to off.
- Pattern analysis runs independently in the background and cannot change the primary job result.
- Use current `translation_mode` and `translation_max_concurrency` settings for AI scheduling; do not create a second rate-limit configuration.
- Retain the current Zinc/Emerald design tokens, light/dark mode, and Lucide icon set. Do not globally restyle legacy pages.

## 3. Goals and Non-goals

### Goals

- Preserve all legacy behavior and data.
- Isolate workflows behind clear service and API boundaries.
- Reuse WordPress, AI, account, job, and persistence capabilities without duplicating HTTP logic.
- Allow independent non-AI tasks to run concurrently.
- Bound AI concurrency to reduce provider rate-limit pressure.
- Make generation, review, publication, copying, and recovery understandable from the UI.
- Make database upgrades repeatable and recoverable.

### Non-goals

- No vector database, embeddings, semantic retrieval, or RAG.
- No agent framework for Rewrite or Pattern Store.
- No Facebook auto-publishing in any new workflow.
- No automatic model change, prompt change, or retry for new Rewrite, Pattern Analysis, or Generate Story AI calls.
- No image generation for Generate Story in this scope.
- No automatic language-detection dependency. Target language is prompt-enforced and user-reviewed; this avoids false rejection of valid Croatian, Romanian, and other closely related Latin-script output.
- No redesign of Dashboard, Accounts, Pipelines, or Settings beyond the explicitly listed integrations.
- No user-selected theme or example count during Generate Story runs; the agent decides both.

## 4. Architecture

### 4.1 Isolation boundary

`StoryOrchestrator` and its legacy pipeline remain the owner of existing prompt generation, translation, crawl, WordPress, Facebook, and Telegram behavior. Do not add `rewrite`, `pattern`, `generate_story`, or `manual_publish` conditionals to it.

Create separate application services:

- `RewriteWorkflowService`: source fetch, sequential chat-history rewrite, title/caption generation, validation, and draft persistence.
- `PatternCollectionService`: metadata/tag extraction, background structure analysis, retry, and pattern persistence.
- `GenerateStoryWorkflowService`: bounded tool-calling loop, final output validation, and draft persistence.
- `ContentDraftService`: draft CRUD, optimistic concurrency, and state transitions.
- `WordPressPublishingService`: strict publication for new workflows and idempotency safeguards.
- `WorkflowJobService`: generic new-workflow job creation, progress, outputs, cancellation, and parent-child relationships.

Shared contracts:

- `AIChatClient`: message arrays, optional tools, response parsing, request policy, and scheduler admission.
- `WordPressSourceGateway`: fetch normalized raw article fields without translation.
- `WordPressDestinationGateway`: categories, media upload, post creation, and post update.
- `WorkflowProfileResolver`: resolve and validate accounts/settings by workflow type.
- Repository interfaces for drafts, patterns, theme rules, pipelines, and jobs.

Services depend on these contracts. Routes and React pages depend on services/API schemas. Shared contracts never depend on a workflow or UI.

### 4.2 Controlled extraction from existing code

The following extractions are allowed only with characterization tests that freeze current behavior:

- Extract raw WordPress article retrieval from `article_importer` so both legacy crawl and Rewrite/Pattern Store call the same normalized fetch operation. The current public legacy wrapper and result shape remain unchanged.
- Rename the vendor-specific `NineRouterAI` implementation to `OpenAICompatibleAIClient` in `app/integrations/ai/openai_compatible.py`, then add the general message-array/tool-call operation beneath it. Existing translation/generation methods retain their prompts, parsing, fallback, and retry semantics.
- Extract destination WordPress primitives from `WordPressPublisher`. The legacy `publish()` behavior remains best-effort for image failure; new `WordPressPublishingService` uses strict image failure.
- Add structured Job outputs while retaining current logs and legacy URL parsing fallback.

### 4.3 Provider-neutral AI naming

The AI integration is configured by API key, base URL, and model identifiers and is not intrinsically tied to 9Router. Use these names throughout new code and UI:

- Class: `OpenAICompatibleAIClient`
- Module: `app/integrations/ai/openai_compatible.py`
- UI account label: `AI Provider`
- Descriptive copy: `OpenAI-compatible endpoint`

Keep a deprecated import alias from the old module/class during migration so existing internal imports and external scripts do not fail abruptly. New code must not import `ninerouter` or use `NineRouterAI`. Persisted Account rows already use the generic type `ai` and generic config keys, so they require no data migration. Continue reading legacy YAML keys prefixed with `ninerouter_` for backward compatibility, but do not write new vendor-prefixed keys. Update tests, README, account labels, and documentation to provider-neutral terminology.

## 5. Persistence and Migration

### 5.1 Versioned migrations

Move startup schema changes out of `app/api/main.py` into idempotent, versioned migration functions. Continue using SQLAlchemy/SQLite rather than adding Alembic in this scope.

Before the first migration from the current schema, use SQLite's backup API to create a timestamped copy under `var/backups/`. Migration requirements:

- Run inside transactions where SQLite permits it.
- Record applied versions in `schema_migrations`.
- Be safe to run repeatedly.
- Never drop or rewrite legacy tables/columns.
- Test upgrade from a snapshot of the current schema and test a second no-op run.

When `STORY_AUTOGEN_DB_URL` is not SQLite, skip the file backup and log that external database backup is operator-managed.

### 5.2 Existing tables

#### `pipelines`

Keep all existing columns and data. Add no required column. Recognize these new `type` values:

- `rewrite`
- `generate_story`
- `wp_publish`

The existing `settings` JSON holds workflow defaults such as `collect_patterns`, WordPress category, and workflow-specific options. Existing rows without these keys use safe defaults.

#### `jobs`

Add nullable/default-safe columns:

- `workflow_type`: string, default `legacy` for old/new rows without an explicit workflow.
- `parent_job_id`: nullable self-reference for background Pattern Analysis.
- `draft_id`: nullable reference to `content_drafts`.
- `outputs`: JSON object, default `{}`. WordPress results use `wp_post_id`, `wp_url`, and `wp_status`.

Do not persist redundant UI capabilities. The API computes capabilities from workflow type, status, draft state, and outputs:

- `can_cancel`
- `can_rerun`
- `can_open_draft`
- `can_copy_link`

Legacy failed jobs keep their current rerun behavior. New failed jobs direct the user to their owning workflow screen for recovery.

### 5.3 New tables

#### `content_drafts`

- `id`
- `kind`: `rewrite`, `generated`, or `manual`
- `pipeline_id`
- `source_url`, nullable
- `language`, nullable for manual items
- `title`
- `content`
- `caption`, nullable and always null for manual items
- `image_kind`, nullable: `upload` or `url`
- `image_source`, nullable
- `category_id`, nullable
- `wp_status`: `draft` or `publish`
- `state`: `generating`, `ready_for_review`, `generation_failed`, `publishing`, `publish_failed`, `publish_unknown`, or `wordpress_created`
- `wp_media_id`, nullable
- `wp_post_id`, nullable
- `wp_url`, nullable
- `error`, nullable
- `version`, integer for optimistic concurrency
- `created_at`, `updated_at`, and `wordpress_created_at`

All three authoring workflows use this table so editor, history, Job, and publishing behavior share one contract.

#### `articles`

- `id`
- `source_url`, unique
- `original_title`
- `theme_tags`, JSON array
- `structure`, nullable JSON object
- `word_count`
- `analysis_status`: `pending`, `processing`, `completed`, or `failed`
- `analysis_error`, nullable
- `processed_at`
- `updated_at`

Upsert by normalized source URL. A failed structure request retains deterministic metadata and tags.

#### `theme_rules`

- `id`
- `tag`, unique
- `keywords`, JSON array
- `is_active`
- `created_at`
- `updated_at`

Seed initial rules through an idempotent seed. Store rules in SQLite instead of a file because the approved Pattern Library UI manages them.

## 6. Profiles and API Separation

New screens use a dedicated `/workflow-profiles` API backed by `pipelines`. It validates allowed account types and settings for each workflow. The legacy `/pipelines` API and page continue to expose legacy types only.

Required profile fields:

- Rewrite: AI account, destination WP account, target language, default WP category, and `collect_patterns`.
- Generate Story: AI account, destination WP account, target language, and default WP category.
- WP Publisher: destination WP account and optional default category.

Pattern Library includes a Collection Sources control. It can toggle `collect_patterns` for eligible legacy crawl and Rewrite profiles without adding controls to the legacy Pipeline form.

Required endpoint surface:

| Method and path | Purpose |
|---|---|
| `GET /workflow-profiles?type={type}` | List one new workflow profile type. |
| `POST /workflow-profiles` | Create a validated new workflow profile. |
| `GET/PUT/DELETE /workflow-profiles/{id}` | Read, replace, or delete a new workflow profile. |
| `GET /workflow-profiles/{id}/wp-categories` | Resolve its WP account server-side and list categories without returning credentials. |
| `POST /rewrite-jobs` | Start one rewrite from `profile_id` and `source_url`. |
| `POST /generation-jobs` | Start one generation from `profile_id`. |
| `GET/POST /content-drafts` | List/filter drafts or create a manual draft. |
| `GET/PUT/DELETE /content-drafts/{id}` | Read, versioned-update, or delete an eligible local draft. A stale `version` returns `409`. |
| `POST /content-drafts/{id}/publish` | Create the configured WP draft/post after validation and confirmation. |
| `GET /patterns/summary` | Return Pattern Library metrics. |
| `GET /patterns` | Search/filter/sort/page articles. |
| `GET/DELETE /patterns/{id}` | Read detail or delete after confirmation. |
| `POST /patterns/{id}/retry-analysis` | Create one explicit analysis attempt for an eligible record. |
| `GET /pattern-collection-sources` | List eligible legacy/new profiles and current opt-in state. |
| `PUT /pattern-collection-sources/{pipeline_id}` | Set `collect_patterns` from an explicit boolean body. |
| `GET/POST /theme-rules` | List or create tag rules. |
| `PUT/DELETE /theme-rules/{id}` | Replace or delete a tag rule. |

Current `/jobs` endpoints are extended only in response fields. Current `/pipelines` endpoints continue to serve legacy types. Publish and delete actions require explicit IDs and UI confirmation where destructive or externally visible.

## 7. Job Execution and AI Concurrency

### 7.1 General parallelism

- Independent fetch, database, validation, and upload work may run concurrently.
- Legacy AI-bearing pipeline jobs retain their existing outer JobRunner queue behavior.
- New workflow jobs do not share one global job lock; dependency ordering occurs inside each workflow.
- Blocking HTTP work runs outside the asyncio event loop.

### 7.2 AI admission

All AI calls acquire a scheduler permit keyed by AI account. The scheduler uses only the existing settings:

- `translation_mode = sequential`: one active AI request per account.
- `translation_mode = parallel`: up to `translation_max_concurrency` active requests per account.

This is an admission limit, not a retry mechanism. Foreground Rewrite/Generate calls have priority over background Pattern Analysis. Waiting background tasks do not consume a permit.

Dependency constraints override parallel mode:

- Chunks of one Rewrite article are sequential because each uses previous assistant outputs.
- Multiple independent Rewrite articles may progress concurrently when parallel mode is enabled.
- Tool turns within one Generate Story agent run are sequential.
- Independent Generate/Rewrite/Pattern jobs may overlap within the configured account limit.
- Existing parallel translation chunks acquire the same account permit so new background work cannot exceed the shared ceiling.

New AI request policy is single-attempt: a network error, timeout, provider error, policy rejection, `429`, invalid JSON, or invalid content fails that operation. Existing legacy retry/fallback behavior remains unchanged.

## 8. Workflow Specifications

### 8.1 Rewrite Article

1. User selects or creates a Rewrite profile and enters a WordPress source URL.
2. Create a Job and `content_drafts` row in `generating` state.
3. Fetch normalized raw `title`, `content`, and original image using `WordPressSourceGateway`.
4. If `collect_patterns` is enabled, upsert deterministic pattern fields and enqueue a child Pattern Analysis job. Do not await it.
5. Split source content with the current chunking function/configuration. Do not change legacy chunk boundaries.
6. Build a fixed system prompt that frames the task as creating a new localized story inspired by the supplied reference, permits consistent name/location changes, preserves dramatic intent, and targets similar length.
7. For each chunk, send exactly:
   - the fixed system message;
   - prior rewritten chunks as assistant messages; if the provider rejects consecutive assistant messages, insert the exact user placeholder `Continue.` between those assistant messages;
   - the current original chunk plus rewrite instruction as the final user message.
8. Never resend prior original chunks. Do not use the legacy previous-sentence translation context.
9. After all chunks, send a final user turn in the same constructed conversation requesting JSON with a new title and a caption. The caption must be an exact prefix of the assembled rewritten story and stop at a suspenseful point.
10. Validate non-empty title/content, JSON shape, and exact caption prefix. Compare rewritten word count with the original and show a review warning outside the 70%–130% range; length alone does not fail the draft.
11. On success, set `ready_for_review`. The user may edit title, content, caption, category, and image reference.
12. Before publishing or copying caption, validate that caption remains an exact prefix of the current content.
13. Publish only after explicit confirmation. After success, show Copy Caption and Copy Link.

There is no AI retry, model fallback, prompt fallback, partial WordPress publication, or automatic Facebook action.

### 8.2 Article Pattern Store

Pattern collection is enabled per eligible pipeline/profile and defaults off.

After raw source fetch succeeds:

1. Normalize URL and upsert `source_url`, original title, word count, and timestamps.
2. Match active `theme_rules` against normalized original title/plain text. Store unique matching tags deterministically.
3. Enqueue a child Job with `workflow_type = pattern_analysis`, `parent_job_id`, and low AI priority.
4. Send the complete original article in one single-attempt analysis request.
5. Require JSON structure with `hook`, `conflict`, `turning_points[]`, `climax`, and `resolution`.
6. On success, persist structure and `completed` status.
7. On failure, persist `failed` and a safe error message. Never modify the parent Job outcome.

App restart may leave `pending` or `processing` records. Pattern Library presents them as recoverable and provides a manual Retry Analysis action; it does not silently resume paid AI calls.

Pattern Library capabilities:

- Summary counts for total, completed, failed/pending, and distinct themes.
- Search/filter/sort and paginated article list.
- Article detail with source, tags, structure, status, and safe error.
- Retry missing/failed structure analysis.
- Delete with confirmation.
- Theme Rules tab with create, edit, enable/disable, and delete.
- Collection Sources control for opt-in pipelines.

### 8.3 Generate New Story

1. User selects or creates a Generate Story profile and starts generation. Target language comes from the profile.
2. Create a Job and draft in `generating` state.
3. Confirm the selected model accepts chat tool definitions. If it rejects tool-calling, fail clearly and direct the user to choose another model. Do not fall back.
4. Provide exactly two read-only tools:
   - `list_themes() -> [{theme, count}]`
   - `get_examples(theme, n) -> [{title, structure}]`
5. Validate tool arguments. Cap `n` at 10 per call and never return original full text.
6. Allow at most six tool calls for the run. Exceeding the limit fails without retry.
7. The model decides theme, number of examples, and whether to inspect another theme.
8. Require final JSON with `title`, `story`, and `caption`.
9. Validate title, story length of 1500–4000 words, and caption as an exact story prefix. Target language is enforced in the prompt and confirmed during the mandatory review rather than by unreliable automatic detection.
10. Store a `ready_for_review` draft. User may edit title, story, caption, and category.
11. Publish only to WordPress after confirmation. After success, show Copy Caption and Copy Link.

No source article, vector retrieval, image generation, Facebook publishing, automatic retry, or automatic model selection is part of this workflow.

### 8.4 Manual WordPress Publisher

1. User selects or creates a WP Publisher profile.
2. Create/open a manual content draft.
3. Require title and content. Category is selectable from the selected WP account. Image is optional and may be either an uploaded file or HTTP(S) URL, but not both.
4. Content editor has an explicit `Plain text`/`HTML` format selector plus Write and sanitized Preview tabs. Plain text paragraphs are converted to WordPress paragraph markup; HTML mode sends the supplied HTML unchanged to WordPress after explicit confirmation. Preview always renders a DOM-sanitized copy and never executes scripts.
5. User chooses `Create WordPress draft` or `Publish now`; default is WordPress draft. `Publish now` requires confirmation.
6. Validate uploaded image MIME as JPEG, PNG, WebP, or GIF and maximum size 10 MiB. Store it under a unique name in `var/uploads/` until publication; clean it after successful upload or explicit draft deletion.
7. Remote images allow only HTTP(S), bounded redirects, timeouts, permitted image MIME, and a streamed 10 MiB maximum. URLs containing credentials are rejected.
8. If a supplied image cannot be uploaded, fail strict publication and preserve the draft. Do not silently publish without the image.
9. Publish through `WordPressPublishingService`, persist post ID/link/status, and show only Copy Link.

## 9. Publication Safety and Idempotency

Publishing obtains a per-draft lock and checks current state before any external request.

- A draft with stored `wp_post_id` is never created again. A successfully created WordPress item is terminal for this workflow; later editing occurs in WordPress.
- A `wordpress_created` draft cannot be submitted again from the same action.
- A stored `wp_media_id` is reused after a definite post-creation failure so retry does not upload duplicate media.
- A definite provider error sets `publish_failed` and permits a deliberate retry.
- A timeout/disconnect after an ambiguous create response sets `publish_unknown`. Automatic retry is disabled because WordPress may already have created the post. UI instructs the user to verify WordPress and reconcile the post before continuing.
- Never log credentials, full story text, uploaded bytes, or raw provider payloads.

The legacy publisher keeps its current behavior. Strict image/idempotency rules apply to new workflow publication only.

## 10. UI and Interaction Design

### 10.1 Navigation

Group sidebar items as:

- **Overview:** Dashboard
- **Content Workflows:** Rewrite Article, Generate Story, Pattern Library, WordPress Publisher
- **Configuration:** Accounts, Pipelines, Settings

Collapsed desktop navigation uses accessible tooltips. Mobile uses the current drawer and closes after navigation.

### 10.2 Rewrite and Generate workspaces

Use the approved split layout:

- Left: profile selector/manager, input or generation summary, run button, and live step progress.
- Right: persistent review editor, validation, save state, category/image controls where applicable, and publish actions.
- Draft/history list is available below or in a drawer without replacing the active editor.
- At mobile widths, panes stack vertically and the primary action bar remains reachable without horizontal scrolling.

Profile creation/editing is scoped to the current workflow. It writes through `/workflow-profiles`; it does not open or modify the legacy Pipeline form.

### 10.3 Pattern Library

- Metric summary.
- Articles and Theme Rules tabs.
- Search/filter controls and paginated table.
- Detail drawer for structures/errors.
- Visible confirmations for retry/delete/rule changes.
- Collection Sources control for the opt-in setting.

### 10.4 WordPress Publisher

- Profile/category controls.
- Title and image URL/upload controls.
- Controlled Write/Preview content editor.
- Clear WordPress Draft/Publish choice.
- Local save status and inline validation.
- Success panel with Copy Link only.

### 10.5 Dashboard integration

- Add workflow badges and safe filters.
- Render capabilities returned by the API rather than guessing actions from status or logs.
- Show Copy Link on Job Card and Job Details when `outputs.wp_url` exists.
- For legacy Jobs, derive a link from recognized WP success logs when structured output is absent.
- Copy buttons stop card-click propagation and announce success/failure accessibly.
- Existing rerun/cancel behavior remains available only where currently valid.

### 10.6 Design and accessibility rules

- Reuse existing semantic tokens and shared Card/Button/Input/Select components.
- Add focused reusable components: Textarea, Tabs, ProgressTimeline, Toast/InlineStatus, CopyButton, ProfileSelector, DraftEditor, and DraftHistory.
- Use Lucide icons only; no emoji UI icons.
- Controlled form fields, labels, visible keyboard focus, inline blur validation, and `role=alert` for errors.
- Use `aria-live=polite` for progress and copy/save status.
- Maintain at least 4.5:1 normal-text contrast in light and dark modes.
- Use 150–300 ms color/opacity transitions without layout-shifting hover scale.
- Respect `prefers-reduced-motion`.
- Verify 375, 768, 1024, and 1440 px widths.

## 11. Error Handling

- New AI operations are single-attempt and preserve actionable error context without sensitive payloads.
- One article failure does not cancel unrelated queued/running articles.
- Pattern errors never fail the source pipeline.
- Validation errors identify the exact field/chunk/tool turn.
- Draft content survives generation/publication failures and browser reloads.
- New publish errors distinguish definite failure from ambiguous external state.
- Copy failures display a manual-select fallback rather than silently failing.
- Category/account deletion conflicts return explicit errors and do not corrupt saved profiles/drafts.

## 12. Legacy Impact Review

### High-review areas

- `app/integrations/ai/openai_compatible.py` and the deprecated `ninerouter.py` compatibility shim
- `app/domain/article_importer.py`
- `app/domain/job_runner.py`
- `app/integrations/publishers/wordpress.py`
- database startup/migration code

Required protection: characterize existing prompts, chunk modes, retry/fallback, normalized article output, job state transitions, original repost behavior, and best-effort legacy image handling before extraction.

### Medium-review areas

- Pipeline validation/filtering and API schemas.
- Job API and Dashboard cards/details.
- App router, FastAPI SPA fallback prefixes, and Sidebar.

Required protection: legacy API payloads remain valid; legacy screens continue to display existing records and actions; new API path prefixes are excluded from SPA fallback handling.

### Low-impact areas

- New workflow services/routes/pages.
- Draft/pattern/theme-rule repositories.
- Scoped UI components.

No unrelated refactor is permitted during implementation.

## 13. Testing Strategy

### 13.1 Baseline and characterization

Keep the current 94 passing backend tests green. Add characterization tests before shared extraction for:

- sequential and parallel translation;
- translation concurrency limit;
- provider-neutral AI client naming and deprecated import compatibility;
- current transient retry and fallback model behavior;
- prompt and article crawl paths;
- original WordPress repost;
- WordPress/Facebook/Telegram pipeline steps;
- job queue, rerun, cancellation, and progress;
- legacy WordPress image failure behavior.

### 13.2 Backend tests

- Versioned migration from current schema, repeated migration, backup behavior, and old-row serialization.
- Workflow profile validation and legacy/new filtering.
- Draft state machine, optimistic concurrency, locks, and idempotency guards.
- AI scheduler sequential/parallel modes, account isolation, priorities, and permit release on failure/cancellation.
- Rewrite message construction proving prior original chunks are not resent.
- Rewrite title/caption validation and single-attempt failures.
- Pattern tag matching, upsert, parent-child jobs, failure isolation, restart states, and retry.
- Agent tool validation, example data minimization, six-call limit, unsupported tools, JSON/language/length/prefix validation.
- Manual content normalization, image validation/limits, strict image failure, WP draft/publish requests, and ambiguous publish state.
- Structured outputs, computed capabilities, and legacy log URL fallback.
- API authorization assumptions remain local/single-user as in the existing app; no new public listener is introduced.

All automated AI and WordPress calls use fakes/mocks. Tests never publish externally.

### 13.3 Frontend tests

Add Vitest and React Testing Library for profile forms, controlled editors, validation, draft recovery, pattern actions, workflow progress, publish confirmation, and Copy buttons.

Continue requiring ESLint and production build. Add Playwright journeys with mocked APIs for:

- Rewrite failure, resume, edit, publish, Copy Caption, and Copy Link.
- Pattern filter/detail/retry/delete and Theme Rule CRUD.
- Generate tool progress, validation failure, review, publish, and copy actions.
- Manual file/URL image modes, Write/Preview, WP Draft/Publish confirmation, and Copy Link.
- Dashboard workflow badges/capabilities and legacy rerun/cancel.
- Keyboard/focus, light/dark, and responsive layouts at 375/768/1440 px.

## 14. Implementation Phases and Gates

### Phase 0 — Legacy characterization

Add behavior-locking tests only. Gate: backend tests, frontend lint, and frontend build pass.

### Phase 1 — Shared foundation

Add versioned migrations/backup, tables/columns, profile API, draft/job contracts, AI admission/request policies, raw WP source gateway, and strict new-workflow publisher. Gate: migration, contract, concurrency, and full legacy regression tests pass.

### Phase 2 — Independent feature tracks

After Phase 1 contracts are stable, these tracks may proceed in parallel:

- Phase 2A: Manual WordPress Publisher backend/UI/tests.
- Phase 2B: Pattern Store, background collection, Pattern Library UI/tests.
- Phase 2C: Rewrite backend/UI/tests.
- Dashboard structured outputs/capabilities and responsive shared UI hardening may also proceed against frozen contracts.

Each track must pass its focused tests plus the legacy regression gate before merge.

### Phase 3 — Generate Story Agent

Begins only after Pattern Store APIs and schemas are stable. Implement tools, bounded loop, validation, draft review, WordPress publication, and UI/tests.

### Phase 4 — Integrated release gate

Run all backend/frontend/browser suites, migration upgrade twice, packaging build checks, and manual smoke tests with non-production accounts. Confirm no real external API is used by automated tests.

## 15. Acceptance Criteria

- Existing translation/crawl pipeline behavior and current tests remain green.
- New profile records never appear in the legacy Pipelines screen.
- Rewrite never resends earlier original chunks and always requires review before publication.
- Pattern collection defaults off, runs as a low-priority child job, and cannot change its parent result.
- Generate Story uses only the two approved tools, makes at most six tool calls, and cannot retrieve source full text.
- Rewrite/Generate final caption exactly prefixes final content before publish/copy.
- No new workflow invokes Facebook publishing.
- Manual Publisher accepts exactly one optional image source, supports WP Draft/Publish, and only exposes Copy Link.
- All new WordPress-created items record structured media/post ID, link, and status and guard against duplicate retry.
- Dashboard shows new jobs safely and provides Copy Link on cards/details, including legacy fallback.
- Current sequential/parallel AI settings bound all AI concurrency without a second setting surface.
- Migrations are additive, backed up for default SQLite, repeatable, and preserve old records.
- Required backend, frontend, and browser gates pass at release.
