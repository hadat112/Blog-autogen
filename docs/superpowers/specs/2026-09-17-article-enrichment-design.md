# Article Source Archive and Deferred AI Enrichment

## Goal

Store fetched source articles as a reusable creative knowledge base without making the V1/V2 workflow depend on additional AI calls. AI enrichment is optional at run time and can be executed later from the Pattern Library.

## User experience

Settings contains:

- `Default AI enrichment`, default `Off`.
- `Enrichment AI account`, referencing an existing AI account.
- `Enrichment concurrency`, fixed/default to `1` for the first version.

The Dashboard run card contains an `AI enrichment` switch. It is initialized from the Settings default and can be overridden for that run.

Pattern Library provides:

- Per-article actions: `Generate Summary`, `Analyze Story`, and `Generate Creative DNA`.
- A bulk action: `Enrich All Missing`.
- Independent retry for failed enrichment steps.

When enrichment is disabled, the workflow only collects source data using deterministic code. When enabled, it still completes the normal V1/V2 workflow immediately and schedules enrichment in a separate background queue.

## Data model

### `articles`

`articles` is the durable source archive. It must contain enough data to avoid fetching the original site again:

- `source_url`
- `source_slug` (indexed lookup key)
- `source_title`
- `source_content`
- `source_image_url`
- `source_language`
- `source_content_hash`
- `source_fetched_at`
- existing deterministic fields: `theme_tags`, `word_count`, timestamps

The source slug check is performed before collection. A normalized URL is converted to a slug and looked up through the index. Existing articles are reused and do not create duplicate collection or analysis work. Existing rows from older schemas are handled safely during migration/backfill.

### `article_enrichments`

One-to-one with `articles`; it stores only the latest AI result:

- `article_id` (unique foreign key)
- `summary`
- `plot_beats`
- `characters`
- `setting`
- `conflict`
- `emotional_arc`
- `creative_dna`
- status and error fields for `summary`, `analysis`, and `dna`
- `ai_account_id`
- `model`
- `updated_at`

Rerunning a step overwrites that step's latest result. Historical AI versions are out of scope.

## Job and queue design

The existing workflow queue remains responsible for V1/V2 and publishing. A separate enrichment queue has concurrency `1` and does not block or delay the workflow queue.

For an article with enrichment enabled:

1. Create or reuse the article source record.
2. Enqueue Summary and Story Analysis as independent enrichment steps.
3. Run them through the enrichment queue.
4. Enqueue Creative DNA only after both prerequisites complete successfully.
5. Update the one-to-one enrichment record after each successful step.

Summary and Story Analysis may be independent logically, but the queue's concurrency of one means they are executed one at a time initially. The dependency is enforced for Creative DNA, not by the main workflow.

Each enrichment job stores its parent workflow ID when created from a workflow. Manual and bulk enrichment jobs may have no workflow parent. Job status, progress, logs, and errors use the existing job infrastructure.

## AI account and failure handling

Only the selected enrichment AI account ID is stored in Settings; credentials remain in `accounts`. At execution time:

- Missing, inactive, or invalid account causes the enrichment step to fail with a clear error.
- The parent V1/V2 job remains successful if publishing succeeded.
- A failed step can be retried independently.
- Bulk enrichment skips completed steps and selects only missing or failed steps.

## Creative DNA rules

The full source is stored for retrieval, but it is not passed wholesale to a future story-generation prompt. Creative DNA is an abstract representation of themes, emotional movement, generalized conflict, and twist style.

Story generation must require novelty constraints:

- new characters
- new setting
- new conflict details
- new event sequence
- no copied sentences or paragraphs from source material

The source archive is used to retrieve relevant records; the generation prompt uses selected abstract DNA rather than the full source text by default.

## API and UI boundaries

- Existing source collection remains part of the workflow service.
- Enrichment APIs expose per-step and bulk enqueue/retry operations.
- The Pattern Library reads article data and enrichment status separately.
- Settings owns the default switch and enrichment account selection.
- No per-pipeline `collect_patterns` setting or collection-source toggle remains.

## Migration and compatibility

The migration adds source archive columns and the one-to-one enrichment table without deleting existing articles or jobs. Existing articles remain usable even when enrichment fields are empty. Missing source content is marked as unavailable for deferred enrichment and can be explicitly re-fetched only when the user requests recovery.

## Verification criteria

## Local database visibility

Settings also displays local database usage for this personal desktop tool:

- SQLite file size when a file-backed database is used.
- Counts for articles, enrichments, jobs, and drafts.
- Values refresh periodically while Settings is open.

This is informational only. No automatic deletion or compaction is triggered from the usage panel.

- A normal V1/V2 run succeeds with AI enrichment Off and creates no enrichment job.
- A normal V1/V2 run with enrichment On creates source data and independent enrichment jobs while returning the workflow result without waiting for them.
- Re-running the same source slug does not create a duplicate article.
- Existing source content is reused without a network fetch for deferred enrichment.
- Creative DNA cannot run until Summary and Story Analysis are complete.
- Bulk enrichment does not rerun completed steps.
- AI account failures affect only enrichment jobs, not the parent workflow.
- The UI clearly shows per-step status and retry actions.
