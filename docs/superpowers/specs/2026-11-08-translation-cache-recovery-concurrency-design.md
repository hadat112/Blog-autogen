# Translation caching, durable recovery, and account concurrency

Date: 2026-11-08
Status: Design approved in conversation; written specification awaiting user review.

## Purpose and approved behavior

Improve the existing article translation workflow without changing its translation rules or publishing choices:

1. Reorder translation prompts to improve reusable-prefix caching.
2. Raise the translation chunk ceiling and the configured working size to 50,000 characters.
3. Resume failed work from persisted results, starting with source fetching and continuing through publication.
4. Run different pipelines concurrently while sharing an AI request limit per account. Each account can have a different limit.

These changes form one workflow upgrade. They do not add provider-specific RPM/TPM configuration, new AI providers, a translation quality benchmark, or a general cache of completed translations across unrelated runs.

## Existing behavior and constraints

- Translation instructions currently contain changing language and paragraph information near the beginning of the user message, before the source text.
- The 30,000-character ceiling is repeated in settings normalization, AI normalization, API validation, and the settings UI.
- Article V1 and V2 persist a final draft before WordPress publication, but article retry creates another draft and starts again with fetching.
- Intermediate translation chunks are not durable recovery artifacts.
- WordPress publication already persists media and post IDs and distinguishes a definite failure from an ambiguous result.
- The workflow runner drains jobs serially. The legacy runner also has a serialization lock. Request-level AI scheduling exists, but its account keys differ between workflow and legacy paths, and its capacity is coupled to translation mode.
- Successful draft bodies are compacted after the most recent 100; job history is limited to 500. Recovery must not depend on job logs or a retained successful draft body alone.
- The workspace contains unrelated, uncommitted model-benchmark changes. Implementation and commits must preserve those changes and stage only files belonging to this upgrade.

## 1. Cache-friendly translation messages

Extract translation message construction into a focused builder that can be verified without making API calls. Preserve every current translation requirement, output-cleaning rule, paragraph-order requirement, and target-language constraint.

Arrange messages in this logical order:

1. Stable system instructions: translate faithfully, preserve structure and names, emit only the translation, and treat source text as data rather than instructions.
2. Stable user prefix containing the source text delimited as source data.
3. Request-specific suffix: exact target language, paragraph count, article title, and optional continuity context.

The system instructions explicitly direct the model to use the authoritative target-language field in the suffix. The source text must not be interpreted as an instruction that overrides that field. Preserve sequential mode's previous translated context and parallel mode's previous source context.

Identical sources and instruction versions must produce identical prefixes across target languages. Titles remain separately translated as today; changing prompt order does not silently merge the title and body into a new output format.

DeepSeek caching remains automatic. Do not add warm-up API calls or promise cache hits. Do not introduce Anthropic-specific fields into the generic OpenAI-compatible payload. Provider-specific explicit cache controls are outside this change. Preserve existing response parsing compatibility.

## 2. A 50,000-character working size

Use one shared backend definition for a 1,000-character minimum, a 50,000-character maximum, and a new default of 50,000 characters. Keep API validation, configuration normalization, client construction, and frontend controls consistent.

Apply a versioned, one-time configuration upgrade that sets the existing working chunk size to 50,000, as approved. Subsequent operator changes must be retained, including after a restart. Set this workspace's active configuration to 50,000 without exposing other configuration values.

The number is a source-character threshold, not a word count or a token budget. Preserve paragraph boundaries where possible. Longer articles still produce ordered chunks; never truncate an article to fit the setting.

For translation responses, retain completion metadata and treat an explicit length-limit finish reason as incomplete rather than a successful checkpoint. Continue to enforce existing content validation. Configure output capacity and timeout through provider-compatible client behavior; do not equate a 50,000-character input ceiling with an output-token limit. Do not silently switch model, discard a paragraph, or mark a truncated response complete. An incomplete attempt is retryable and its earlier completed chunks remain available.

The shared chunk-size setting also affects rewriting today. Preserve that relationship and verify V2 chunking, metadata assembly, and continuation handling at the larger size.

## 3. Durable workflow checkpoints

### Ownership and data model

Add a focused recovery service and durable checkpoint records owned by the draft/workflow execution, independent of transient logs and job history. Use normal database migrations; existing databases remain readable.

Persist the following logical artifacts:

- Execution manifest: normalized source URL, workflow mode, target language, source proxy/enrichment choices, selected account IDs, prompt version, source hash, and original chunk boundaries.
- Source snapshot: title, full content, source image URL, and canonical source URL, saved immediately after a successful fetch even when automatic pattern collection is disabled.
- Fetch-adjacent collection status, so a retry can finish archiving or collection without fetching again or duplicating analysis jobs.
- Translated title and each completed, validated body chunk, indexed in original order. V2 additionally retains completed rewrite and metadata results needed to continue its existing sequence.
- Assembled title, body, caption, and applicable validation metadata.
- Publication progress: existing WordPress media/post IDs and URL, Facebook post ID, and notification completion where applicable.

Reuse existing draft publication columns where they already express the result. Avoid storing credentials in manifests, artifacts, logs, or job outputs. API keys are resolved from the saved account when executing a request.

### Retry behavior

A retry creates a new job for history but attaches to the same recoverable draft and checkpoints. Link the previous attempt to the new job. Permit only one active attempt for a draft and reject double submissions atomically.

| Failed or interrupted stage | Resume behavior |
| --- | --- |
| Source fetch | Fetch again; partial HTTP data is not a completed snapshot. |
| Collection after fetch | Reuse source snapshot and retry the missing collection work. |
| Title translation | Reuse source; translate the title if not completed. |
| Body translation/rewrite | Reuse completed chunks; execute only missing or failed chunks in original order. |
| Metadata or assembly | Reuse completed content and retry only missing metadata/assembly. |
| WordPress image upload or post creation | Reuse complete translation and any confirmed media ID. |
| Facebook or Telegram after WordPress | Reuse confirmed WordPress result and resume only the missing delivery. |

In sequential translation or rewrite mode, resume with the persisted previous translated chunk. In parallel translation mode, reconstruct context from the frozen source snapshot. Persist each completed parallel chunk independently through a safe database boundary; never share a SQLAlchemy session across request threads.

Freeze the execution manifest on initial execution. A retry uses its original language, mode, and chunk boundaries even when settings subsequently change. Credentials may be updated on the same saved account to fix authentication. If the selected model or other output-defining settings no longer match, explain the incompatibility and require an explicit fresh run rather than silently mixing outputs. Existing data remains intact.

### External effects and cancellation

Keep the existing distinction between definite WordPress failure and `publish_unknown`. A known post ID is never posted again. An ambiguous WordPress timeout requires reconciliation or operator confirmation through the recovery flow before another create request; this design does not assume exactly-once delivery from an external API.

Persist successful downstream IDs immediately. Expose failed Facebook/Telegram delivery as resumable delivery status rather than hiding it in a success-only warning. Do not repeatedly send a channel already marked complete. An ambiguous external result must be shown as uncertain rather than blindly retried. Preserve optional-channel configuration and the existing policy that a failed featured-image upload may still publish without an image.

Cancellation stops admission of new work. Fence writes by active attempt ID: a cancelled or superseded worker thread cannot overwrite a newer retry, mark its job successful, or begin a subsequent external publication. A request already sent to an external API may still complete; retain the ambiguous-result handling where necessary. Interrupted jobs recover on restart with their committed checkpoints; retry is operator-initiated, not automatic publication on startup.

### Retention and old jobs

Never compact recovery data for unfinished, failed, cancelled, or uncertain executions. Completed channel checkpoints must protect retry of a remaining channel even if WordPress already succeeded. Clean up recovery bodies only after the entire configured workflow is complete, using the existing successful-draft retention policy. Delete associated checkpoints when their draft is deliberately deleted.

For historical jobs, use an existing complete draft to resume publication when available. Do not fabricate missing chunk checkpoints from progress logs. If earlier source/intermediate data is unavailable, state which stage must be repeated; do not claim old jobs can always resume without AI calls. Existing published WordPress results must remain protected from duplicate creation.

## 4. Concurrency per AI account

### Operator configuration

Add `max_concurrency` to saved AI account configuration, with default 2 and supported values 1 through 8, matching the application's current upper bound. Show it in the existing AI account form. The scope is active API requests, not pipelines or stories. Accounts without the new field use 2; stop treating the old global translation concurrency setting as the source of account capacity.

Keep sequential/parallel translation mode to choose whether chunks within one execution may overlap. Sequential mode does not force all other executions on the same account to wait: it orders only that execution's chunks. Parallel workers request permission from the shared account scheduler and must not multiply account capacity.

### Shared scheduler

Use one scheduler per application process for all AI request paths, including article workflows, rewrite/text-story generation, legacy pipelines, enrichment, and benchmarks. Preserve a benchmark's deliberate internal sequential order.

Resolve quota identity consistently from the normalized provider endpoint and a non-reversible fingerprint of the API credential. Do not use a raw key in diagnostics. Saved account entries with the same endpoint and key share a quota group; conflicting capacities use the lowest configured active limit. Key or endpoint changes produce the corresponding new group. Different quota groups have independent limits.

Fairly queue eligible requests so one large article cannot occupy every future slot indefinitely; preserve the scheduler's foreground/background fairness. Acquire a slot immediately before the HTTP attempt and release it when that attempt finishes. Local retry sleep and provider cooldown must not retain a slot. A new limit applies to admission of new requests; reducing it does not cancel already active requests.

Different API keys on the same provider may still share a provider organization quota. This simple design does not infer that relationship or promise to eliminate all rate-limit errors.

### Rate-limit handling

On HTTP 429, apply a cooldown to that quota group, honor a valid `Retry-After` header, and use bounded exponential backoff with jitter when no usable server delay is supplied. Allow at most three total automatic attempts per request, with a 1-second backoff base capped at 30 seconds for computed delays; server-supplied delays take precedence. Check cancellation while waiting. Exhausted requests remain failed at their own stage for manual retry.

Do not automatically retry authentication/validation errors. Preserve existing transient-network retry behavior while consolidating retry ownership so nested loops cannot multiply attempts. Do not silently switch models during resumed translation. Persist a checkpoint only for a valid completed response.

This design intentionally omits RPM/TPM entry, automatic provider-tier discovery, and adaptive throughput targets. The account concurrency limit plus cooldown is a simple throttle, not a guarantee that an external limit cannot be reached.

### Workflow execution

Replace the workflow runner's single-job drain with a bounded dispatch pool so different pipeline jobs can progress at the same time. Use a process-wide maximum of eight active workflow executions, independent of AI account limits; queued work remains bounded by that dispatcher. Ensure legacy execution does not retain a global serialization lock around AI calls that defeats the shared scheduler.

Keep per-draft publication locks and per-attempt write fences. Database connections/sessions belong to individual workers. A workflow waiting for AI must not hold a database write transaction. The application currently runs as a single backend process; distributed scheduling across multiple processes is outside this scope and must not be claimed as supported.

## Integration boundaries and UI

- A prompt builder owns stable translation-message construction.
- A recovery service owns manifests, validated artifacts, attempt ownership, and resume selection.
- An account quota resolver and shared request scheduler own AI admission and cooldowns.
- Workflow runners own bounded job dispatch; account limits belong to the request scheduler.
- Existing gateways retain network transport and external publication behavior.

Apply recovery to Article V1/V2 and the rewrite entry point that already dispatches ArticleWorkflowService. Route legacy source-URL article retry through the same durable recovery execution path with its existing V1 behavior, rather than implementing another incompatible checkpoint system. Unrelated prompt-based generation keeps its existing workflow semantics but participates in shared AI admission. Preserve text-story composition's existing stage recovery.

Update existing retry buttons and job details to distinguish a fresh run from resume, show the failed/resumed stage, retain the source/draft relationship, and prevent a second active retry. Support retry of failed optional deliveries without republishing WordPress. Keep existing source proxy choices on resume. Settings show the 50,000-character maximum and explain that account settings control total AI concurrency. No page redesign is required.

## Verification and acceptance

Use fake AI/source/publisher gateways; tests must not publish to real services or consume paid AI credits.

1. Prompt tests verify identical reusable prefixes across languages and preservation of every translation rule and continuity field.
2. Configuration/API/UI checks accept 50,000, reject larger values at validation boundaries, migrate the working setting once, and preserve later edits.
3. Source failure retries fetch; successful fetch plus later failure does not fetch again, including when pattern collection is disabled.
4. Partial sequential and parallel translation retries retain completed chunks and reassemble in original order. Explicit truncated responses are not completed checkpoints.
5. Restart and retention tests preserve unfinished artifacts. Cancellation and overlapping retry tests prevent stale-worker writes and duplicate active attempts.
6. Publication retry makes zero AI/source calls when a completed draft exists, reuses media IDs, and does not recreate a known WordPress post. Uncertain results remain blocked pending verification.
7. Failed downstream delivery can resume without another WordPress call or repeated completed channel delivery.
8. Barrier-based scheduler tests demonstrate that two pipelines using one account share its cap, independent accounts use their own caps, and duplicate credentials share the stricter cap. Sequential chunks do not serialize unrelated pipelines.
9. Rate-limit tests cover cooldown isolation, Retry-After, bounded attempts, cancellation during waiting, and release of request slots between attempts.
10. Runner tests verify overlapping pipeline execution within the dispatcher bound, independent sessions, and preservation of internally sequential benchmarks.
11. Historical-job tests distinguish recoverable existing drafts from missing artifacts and protect known publication results.
12. Run relevant backend suites and frontend build/lint for the touched controls. Broaden testing only when failures or additional changes warrant it.

## Delivery

After written-spec approval, create an implementation plan using the writing-plans skill. Implement in reviewable stages: shared prompt/settings behavior, durable recovery, account admission, and concurrent runner integration. Database upgrades must preserve existing data. Do not change unrelated model-benchmark work or run live publication as validation.
