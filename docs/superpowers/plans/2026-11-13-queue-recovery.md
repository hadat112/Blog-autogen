# Queue recovery implementation plan

Authorized scope: fix the simulated scheduler faults and prevent silent AI queue stalls; improve WordPress rejection diagnostics. Work in the existing checkout; do not change the supplied DB or contact providers.

Design: preserve actual HTTP concurrency. Never release an occupied network slot just because its async wrapper was cancelled. Clean every abandoned queue ticket, run status callbacks outside scheduler locks, and bound queue admission. Use one retry budget per AI call and cap Retry-After. Emit meaningful progress before title translation and on admission/retry. Include sanitized WordPress error code/message, never credentials or complete response bodies.

- [x] Add regression tests for callback errors, cross-account lock contention, admission timeout, cancelled in-flight failure, retry limits, title progress and WordPress rejection details; observe failures.
- [x] Implement scheduler cleanup, bounded admission, diagnostic snapshots and capped cooldown.
- [x] Integrate AI queue/request/retry progress and bounded retry budget. Retain slots for real in-flight calls; cancel prevents retry. Avoid speculative fallback across models because recovery manifests freeze the model.
- [x] Surface cancellation semantics and improve WordPress rejection diagnostics without retrying post creation.
- [x] Run focused tests, entire Python suite, independent review and document prevention/recovery steps.

Constraints: no new dependencies; no external publishing; test concurrency with events and finite joins; no DB migrations. A requests read timeout limits inactivity, not total wall-clock duration. Hard termination of in-flight sockets would require a different transport/process boundary and is not claimed by this change.

Review focus: callback exceptions after enqueue; callback reentry; cooldown with no active HTTP; cancellation after HTTP failure; preserved external publish receipts; sanitized server-provided error strings.

Verification: full Python suite passed (307 passed, 3 skipped; existing Starlette deprecation warning). Independent review found and verified a fix for Basic Auth redaction; no remaining actionable findings. Changes remain in the existing checkout, uncommitted.
