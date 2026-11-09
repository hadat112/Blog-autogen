# Translation Recovery and Account Concurrency Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Preserve completed work across retry while supporting cache-friendly 50,000-character translation and account-wide concurrency.
**Architecture:** Shared prompt/settings definitions, draft-owned recovery records, request admission by credential identity, and bounded concurrent workflow dispatch. Existing WordPress publication guards remain authoritative.
**Tech Stack:** Python, SQLAlchemy/SQLite, FastAPI, React/TypeScript, pytest.
**Spec:** `docs/superpowers/specs/2026-11-08-translation-cache-recovery-concurrency-design.md`

## Global Constraints

- Preserve unrelated uncommitted model-benchmark changes.
- 50,000 source characters maximum/default; no source truncation.
- Account concurrency defaults to 2, range 1–8; workflow dispatch maximum 8.
- Three total automatic HTTP attempts; account cooldown on 429; no live paid API or publishing tests.
- Recovery data must survive restart, job pruning, cancellation, and failed optional deliveries.

## Review Focus

- Same API credential saved twice must not double throughput: task 2.
- Retry after cancellation cannot admit stale writes/publication: tasks 3 and 5.
- Pruning job history cannot destroy recovery: task 3.
- Original-language repost skips AI and remains supported: task 4.
- Earlier user edits and benchmark cancellation semantics must survive: task 5 and final regression suite.

## Task 1: Prompt and character limits

Files: `app/domain/translation_settings.py` (new), `app/domain/translation_prompts.py` (new), settings manager, API schemas, AI client, frontend settings; tests in `tests/integrations/test_translation_upgrade.py`.
Interface: `build_translation_messages(text, language, article_title='', previous_translation_context='', previous_source_context='') -> tuple[str, str]`; common min/default/max constants.
- [x] Write tests asserting stable source prefix across languages, preservation of dialogue/paragraph instructions, and acceptance of 50,000 source characters without splitting a short article.
- [x] Run `.venv/bin/pytest tests/integrations/test_translation_upgrade.py -q`; expect failures before implementation.
- [x] Extract the full existing rules into a message builder with source before variable suffix; update shared settings ceiling/default and versioned config migration.
- [x] Run the new tests and existing AI/settings tests; reject explicit truncated translation responses.

## Task 2: Account admission and HTTP retry

Files: new `app/integrations/ai/quota.py`, scheduler, AI client, client factory, account service/form, legacy orchestrator, tests.
Interfaces: `quota_identity(base_url, api_key) -> str`; `scheduler.register(key, owner, limit)`, `scheduler.cooldown(key, seconds)`; `max_concurrency` account field.
- [x] Test credential identity, shared conflicting limits, independent accounts, sequential mode sharing account slots, cooldown isolation, and permits released between retries.
- [x] Run new tests to observe missing behavior.
- [x] Wire every request path to registered account quota; normalize concurrency 1–8; release permits before cooldown/retry; enforce three total attempts with Retry-After support and no model fallback for translation.
- [x] Run scheduler, AI transport, benchmark, and account suites.

## Task 3: Durable artifacts and attempt fencing

Files: models, migration 12, new `app/services/workflow_recovery_service.py`, draft deletion/retention, tests.
Interfaces: `WorkflowRecoveryService(db, draft_id, job_id)` exposes `claim(manifest)`, `check_active()`, `get(stage)`, `save(stage, value)`; checkpoints belong to a draft.
- [x] Test fresh claim, JSON persistence, new-attempt takeover after terminal job, rejection of active overlap, stale-worker rejection, and survival of history pruning.
- [x] Run failing service tests.
- [x] Implement a recovery record with manifest and artifacts, active attempt ID, compare-and-swap guarded writes, and migration. Persist separate chunk artifacts via service-created worker sessions, never a shared session across threads.
- [x] Test migration against existing SQLite schemas and deletion/retention.

## Task 4: Resume source, generation, and publication

Files: article workflow, translation client, rewrite engine, article/rewrite retry routes, workflow job service, legacy URL dispatch, tests.
Interfaces: optional `checkpoint` callback object on translation/rewrite execution; resume routes retain original draft and create linked job.
- [x] Test source failure, successful fetch followed by translation failure, middle chunk failure, WordPress failure after complete translation, and completed WordPress followed by failed optional delivery.
- [x] Observe failures with `.venv/bin/pytest tests/services/test_workflow_recovery.py tests/api/test_article_workflows.py -q`.
- [x] Save frozen manifest/source before collection, save title/chunks/metadata independently, reuse assembled draft on retry, retain successful external IDs, and stop duplicate external writes on uncertain outcomes.
- [x] Make retry atomic per draft; preserve proxy/enrichment settings and validate output-defining configuration; route URL legacy retries through the durable execution path while preserving unrelated generation.
- [x] Verify original repost, V2 history context, retry button/job links, and historical drafts without artifacts.

## Task 5: Concurrent workflow execution

Files: workflow runner, legacy job runner, scheduler cancellation integration, tests.
- [x] Add event/barrier tests proving two jobs overlap, cancellation keeps pending work running, duplicate active draft is rejected, and cancelled worker cannot publish or overwrite a retry.
- [x] Run tests before modifying runner.
- [x] Dispatch up to eight executions, share AI capacity across every pipeline, release database transactions before waiting, and preserve benchmark row cancellation.
- [x] Run workflow runner, cancellation, article, text-story, and benchmark suites.

## Task 6: Review and regression verification

- [x] Run full `.venv/bin/pytest -q` and frontend `pnpm build`, `pnpm lint`; compare to baseline and report pre-existing warnings/failures accurately.
- [x] Review all diffs for existing user changes, unsafe publication retry, unbounded work, secret exposure, source truncation, and missing checkpoint ownership.
- [x] Request one independent whole-change code review, resolve substantive findings with regression tests, and rerun checks affected by fixes.
- [x] Update README for account limits, retry behavior, one-process scheduling, and cache expectations; report any concrete limitations.

## Execution rulings

The user explicitly authorized implementation after reviewing the spec. Execute inline without another approval stop. Work in this existing feature checkout to preserve uncommitted integration changes; save baseline patch and avoid commits containing those changes. Per-task implementation commits are deferred because several touched files contain unrelated edits; the design document was committed separately.
