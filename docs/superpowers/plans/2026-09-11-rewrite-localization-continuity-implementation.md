# Rewrite Localization and Continuity — Implementation Plan

**Date:** 2026-09-11

**Source:** `docs/superpowers/specs/2026-09-11-rewrite-localization-continuity-design.md`

## Implementation boundary

This plan changes only the Rewrite workflow. Generate Story, publishing, UI, AI
provider selection, job cancellation, and the existing caption-mismatch
semantics remain unchanged.

The 2026-09-06 workflow-review plan already made caption-prefix comparison
informational. This work keeps that rule: an incorrect caption prefix produces a
warning, while empty/malformed metadata is a blocking failure. The existing
alternating rewrite message-history behavior must also remain portable.

## Target design

`RewriteEngine.rewrite()` will follow this sequence:

```text
source chunks
    -> one full-source Cast Sheet request
    -> validate immutable entity registry
    -> rewrite chunks with Cast Sheet + mutable Continuity State
    -> update state after each chunk
    -> final title/caption JSON request
    -> validate metadata, caption prefix, and length
    -> return content, metadata, warnings, and continuity warnings
```

The Cast Sheet is immutable after parsing. The Continuity State may change after
each chunk, but its identity and relationship fields are copied from the Cast
Sheet and cannot be overwritten by a model response.

## Phase 1 — Context contracts and validation

Modify or add:

- `app/domain/rewrite_context.py` (new focused module)
- `app/domain/content_validation.py`
- `tests/domain/test_rewrite_context.py` (new)

Steps:

1. Define the Cast Sheet contract with an explicit JSON shape. Use a top-level
   object containing `entities`, `locations`, `timeline`, `objects`, and
   `immutable_facts`; require `entities` to be a non-empty list.
2. Require every important entity to include original/localized name, gender
   fields where applicable, age or approximate age, role, relationships, and
   pronoun/forms-of-address data. Reject missing names, roles, or relationship
   fields with a clear `ValueError`.
3. Define a Continuity State contract containing the immutable cast sheet plus
   active characters, current location/timeline, relevant relationships,
   established events, unresolved threads, and the previous rewritten-chunk
   summary.
4. Parse JSON through the existing JSON helper, reject empty/non-object/
   malformed responses, and normalize only safe optional fields. Do not attempt
   to repair malformed model JSON.
5. Add validation that a state update cannot change immutable entity names,
   genders, roles, or relationships. A mismatch becomes an explicit continuity
   warning or a blocking error according to whether identity is missing versus
   contradictory; contradictory immutable identity must fail the job.
6. Add focused tests for valid sheets, missing required fields, malformed JSON,
   immutable-field mutation, and empty state updates.

Gate:

```bash
uv run pytest -q tests/domain/test_rewrite_context.py
```

## Phase 2 — Native rewrite prompts and preflight Cast Sheet

Modify:

- `app/domain/rewrite_engine.py`
- `tests/domain/test_rewrite_engine.py`

Steps:

1. Replace `REWRITE_SYSTEM_PROMPT` with the approved native-literary prompt:
   idiomatic cadence/syntax, no literal calques, target-language gender/case/
   declension/agreement/conjugation, preserved facts and dramatic beats, stable
   names/roles/relationships, and output-only behavior.
2. Add a preflight request using the complete source title, complete source
   content, and target language. Require Cast Sheet JSON only. Parse and
   validate it before any chunk request; fail clearly before rewriting if the
   source exceeds the configured AI context window rather than truncating it.
3. Make preflight failure explicit for empty output, malformed JSON, empty
   entity registry, or missing required fields. Do not silently continue with an
   unvalidated context.
4. Keep calls through the existing `ai.chat(messages, temperature=...)`
   interface; do not change provider interfaces or add provider-specific logic.
5. Preserve alternating system/user/assistant history for prior rewritten chunks.
   The preflight response must not be inserted as story content or reused as a
   historical assistant rewrite.
6. Update fake AI fixtures and tests so the first call is the preflight, followed
   by chunk calls and final metadata.

Required assertions:

- the native-language and anti-calque instructions are present;
- the complete source is included only in the preflight request;
- the Cast Sheet is passed to every chunk request;
- prior original chunks are never resent after their own request;
- empty/malformed Cast Sheet responses fail before chunk rewriting.

## Phase 3 — Chunk continuity processing

Modify:

- `app/domain/rewrite_engine.py`
- `app/domain/rewrite_context.py`
- `tests/domain/test_rewrite_engine.py`
- `tests/domain/test_rewrite_context.py`

Steps:

1. Initialize Continuity State from the validated Cast Sheet.
2. For every source chunk, send the native system prompt, fixed Cast Sheet,
   current mutable state, and exactly one source chunk. Require seamless
   continuation, explicit subject/pronoun control, localized names and
   relationships, grammar polishing, and only rewritten prose in the response.
3. Reject empty chunk output immediately. Keep the existing progress callback
   and cancellation behavior unchanged.
4. After a successful chunk, make one structured state-update request using the
   rewritten chunk and current state. Require JSON containing current
   location/timeline, active characters, established events, unresolved threads,
   and a short last-chunk summary. This explicit follow-up is necessary because
   the rewrite response must remain prose-only; do not ask the prose response
   to mix JSON and story text. Validate the update against the immutable Cast
   Sheet before using it for the next chunk. If the update is malformed or
   empty, fail the job rather than silently dropping continuity context.
5. Ensure a niece, sibling, or similarly related entity cannot be replaced by
   another entity because of a later model response. Test localized names,
   gendered forms, pronouns, and relationships across at least two chunks.
6. Keep assembled story behavior and the existing 70%–130% length warning.

The resulting call sequence is one Cast Sheet call, then for each chunk one
rewrite call plus one state-update call, followed by one metadata call. Tests
must assert this ordering and ensure state-update JSON never enters the
assembled story.

## Phase 4 — Final metadata and caption validation

Modify:

- `app/domain/rewrite_engine.py`
- `app/domain/content_validation.py`
- `tests/domain/test_rewrite_engine.py`

Steps:

1. Send a final metadata request after all chunks with strict JSON containing
   only `title` and `caption`.
2. Require a localized title and a caption copied exactly from the assembled
   story prefix, ending at a complete sentence and emotional suspense point,
   without cutting a word and preserving Unicode. Target 40–70 words; if the
   assembled story is shorter than 40 words, emit a warning instead of failing
   solely for the unattainable minimum.
3. Reject malformed JSON, extra non-object output, empty title, empty caption,
   and missing metadata fields. Do not repair malformed responses.
4. Validate caption prefix exactly. Preserve the established warning behavior
   for a non-prefix caption, while adding explicit warnings for incomplete
   sentence/word-boundary/target-length violations when they can be determined
   locally. Do not make mismatch block saving or publishing.
5. Return structured warnings in the existing result shape so
   `RewriteWorkflowService` and Job output remain compatible.

Tests:

- valid title/caption JSON;
- malformed JSON and empty fields;
- exact story-prefix caption;
- caption that cuts a word or sentence;
- Unicode caption preservation;
- approximately 40–70-word caption warning behavior;
- existing length and caption mismatch warnings.

## Phase 5 — Service integration and regression coverage

Inspect and minimally update if needed:

- `app/services/rewrite_workflow_service.py`
- `tests/services/test_rewrite_workflow_service.py` or the closest existing
  rewrite service test module

Steps:

1. Confirm the engine's new preflight/chunk/final-call errors are persisted as
   generation failures with useful messages, not silently saved as drafts.
2. Keep progress percentages, cancellation checks, draft versioning, and job
   completion output unchanged.
3. Ensure continuity warnings are included in the completed Job output without
   exposing provider credentials or full source content in logs/API responses.
4. Add service coverage for malformed context, empty chunk response, and a
   successful multi-chunk rewrite.

## Test and release gates

Run focused tests first:

```bash
uv run pytest -q tests/domain/test_rewrite_context.py tests/domain/test_rewrite_engine.py
uv run pytest -q tests/services/test_rewrite_workflow_service.py
```

Then run the complete backend suite and packaging checks:

```bash
uv run pytest -q
python3 packaging/smoke_test.py
git diff --check
```

The smoke test is independent of this feature but must remain green because the
release packaging changes are already in the same working tree. If PyPI is
unreachable, report the network failure and do not claim the gate passed.

## Completion checklist

- [ ] Native literary prompt contains anti-calque and target-grammar rules.
- [ ] Cast Sheet is created once from the complete source and validated.
- [ ] Immutable names, genders, roles, and relationships cannot drift.
- [ ] Every chunk receives Cast Sheet and Continuity State.
- [ ] Continuity state is updated and validated after every chunk.
- [ ] Empty/malformed context, chunk, and metadata responses fail clearly.
- [ ] Final metadata is strict JSON with localized title/caption.
- [ ] Caption prefix, sentence, word-boundary, Unicode, and target-length checks
      are covered without making mismatch publication-blocking.
- [ ] Existing cancellation, length warning, and job persistence behavior stays
      compatible.
- [ ] Focused tests, full backend tests, smoke test, and diff checks pass.
