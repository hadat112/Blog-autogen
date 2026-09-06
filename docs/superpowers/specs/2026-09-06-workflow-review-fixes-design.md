# Workflow Review Fixes — Design

**Date:** 2026-09-06

**Status:** Approved design

## 1. Scope

This change addresses four remaining workflow review findings without redesigning the existing content workflows:

- make caption-prefix comparison informational rather than blocking;
- make Rewrite chat history portable across stricter OpenAI-compatible providers;
- add direct cancellation controls to Rewrite and Generate Story;
- make Pattern Analysis retry source eligibility explicit.

The existing Pattern Analysis cancellation guard and cancelled-draft recovery remain in place. Pattern Analysis stays on its current background thread because terminal Job guards already prevent a late AI response from reviving a cancelled Job.

## 2. Caption Comparison

Rewrite and Generate Story prompts continue asking the model for JSON containing `title`, story/content, and `caption`. A missing or empty caption remains an invalid AI response.

The system keeps the simple exact comparison:

```text
content.startswith(caption)
```

The comparison becomes metadata only:

- a match records `caption_matches_prefix: true`;
- a mismatch records `caption_matches_prefix: false` and a review warning;
- a mismatch does not fail generation, mutate either value, or invoke another AI request;
- no quote/whitespace normalization, automatic caption extraction, or Sync button is added;
- a mismatch does not block saving, publishing to WordPress, or copying the caption.

The review editor displays a compact `Caption matched` or `Caption differs from story opening` status near the Caption field. The latter is a warning, not an error. WordPress publication does not validate the relationship because the caption is not included in the WordPress post payload.

## 3. Rewrite Message Ordering

Every historical rewritten chunk is represented by an alternating pair:

```text
system
user: Begin the rewritten story.          # history for chunk 1
assistant: <rewritten chunk 1>
user: Continue.                           # history for later chunks
assistant: <rewritten chunk N>
user: <request for the current operation>
```

The historical user messages contain no original article text. Only the current source chunk is sent in the final user message for a rewrite turn. The title/caption metadata request reuses the same alternating rewritten-history representation.

This preserves the existing no-resend guarantee while avoiding an assistant message immediately after the system message.

## 4. Direct Cancellation

Rewrite Article and Generate Story show a small destructive-outline `Cancel` button beside progress while the Job is `queued` or `running`.

The button calls the existing Job cancellation API and is disabled while the request is pending. On success, the page refetches the Job and draft immediately. The Job displays `cancelled`; the draft uses the existing recoverable `generation_failed` state with the message `Generation was cancelled`. No new database state or migration is introduced.

The current backend protections remain authoritative:

- `WorkflowRunner` marks the Job and generating draft when an active task is cancelled;
- Rewrite and Generate workers check cancellation before persisting final output;
- terminal Job states cannot be overwritten by late progress, failure, or completion calls.

## 5. Pattern Retry Eligibility

`GET /pattern-collection-sources` adds a non-secret boolean field:

```json
{
  "pipeline_id": "...",
  "name": "...",
  "type": "rewrite",
  "collect_patterns": true,
  "can_analyze": true
}
```

`can_analyze` is true only when the source is active and references an existing AI account of type `ai`. The response exposes neither the account ID nor credentials.

The Pattern Library:

- selects the first source with `can_analyze: true`;
- lists ineligible sources as disabled with `AI account required`;
- disables Retry when no eligible source exists;
- sends the explicitly selected pipeline ID;
- displays retry failures inline.

The retry endpoint continues validating eligibility server-side so a stale or forged client request cannot bypass these checks.

## 6. API and Persistence Impact

- Add `caption_matches_prefix` to generation result metadata and Job outputs/warnings where applicable.
- The persisted title, content, and caption remain unchanged.
- No database column or migration is needed.
- Existing draft and Job response fields remain backward compatible.
- The collection-source response gains one additive boolean field.
- Legacy pipelines, legacy AI retry/fallback behavior, Facebook publishing, and WordPress payload formatting are unchanged.

## 7. Error Handling

- Empty caption: generation fails once as an invalid response.
- Non-prefix caption: generation succeeds with a warning.
- Cancel API failure: keep polling and show the server error inline.
- Pattern retry with an invalid source: backend returns a safe validation error and UI displays it inline.
- Late worker response after cancellation: result is discarded and terminal states remain unchanged.

## 8. Tests and Release Gate

Backend tests cover:

- mismatched non-empty captions succeed and set `caption_matches_prefix: false`;
- matched captions set the flag to true;
- WordPress publication accepts a non-prefix caption;
- Rewrite message roles alternate and prior original chunks are never resent;
- cancelled Rewrite, Generate, and Pattern jobs cannot be revived by late workers;
- `can_analyze` reflects active source and valid AI-account ownership;
- retry rejects an ineligible source even when requested directly.

Playwright covers:

- matched and mismatched Caption status;
- mismatch does not disable Publish or Copy Caption;
- direct Cancel on Rewrite and Generate Story;
- eligible/default and disabled Pattern retry sources plus inline retry error.

Release commands:

```bash
uv run pytest -q
cd frontend && ./node_modules/.bin/tsc --noEmit
cd frontend && pnpm lint
cd frontend && pnpm build
cd frontend && pnpm test:e2e
```

No Vitest or React Testing Library is introduced. Automated tests continue using mocked AI and WordPress requests.

## 9. Acceptance Criteria

- A non-empty caption mismatch never causes generation or WordPress publication to fail.
- Caption comparison remains exact and visible as informational UI metadata.
- Rewrite messages alternate user/assistant after the system message without resending previous source chunks.
- Rewrite and Generate Story can be cancelled from their own progress panels.
- Cancelled jobs and generating drafts settle into terminal, recoverable states.
- Pattern retry defaults only to an eligible AI-backed source and reports failures inline.
- Existing legacy behavior and all release gates remain green.
