# Unified V1 & V2 Article Workflows Design

## Goal

Unify the article processing workflows (previously split into V1 legacy pipeline runner and V2 rewrite engine) into a single, cohesive service (`ArticleWorkflowService`). All stages—input normalization, source extraction, pattern collection, draft persistence, multi-channel publishing, cancellation, error sanitization, and retries—are shared. The ONLY branching point occurs at Step 3 (AI processing), where the system routes between V1 (deterministic translation) and V2 (dramatic rewrite).

## User Experience & UI

- **Dashboard QuickRun**:
  - Exposes simple, concise **V1** and **V2** toggle buttons without redundant descriptive labels.
  - Input field strictly accepts a source article URL (`https://...`).
  - Pipeline selector lists pipelines that have active AI and WordPress accounts configured.
  - Single submission action calling the unified article workflow endpoint with `mode: "v1" | "v2"`.
- **Job Display & Timeline**:
  - Tags jobs cleanly as `V1` or `V2`.
  - Timeline renders standard 5-step progress:
    1. Fetch source article
    2. AI processing (chunk progress, word count, elapsed time)
    3. Draft assembly & validation
    4. WordPress publishing
    5. Multi-channel distribution (Facebook / Telegram if configured)
  - Retry button is available for all failed jobs regardless of mode (V1 or V2).

## Architecture & Data Contracts

### 1. API Payload

```python
class ArticleWorkflowRunInput(BaseModel):
    pipeline_id: str
    source_url: str
    mode: Literal["v1", "v2"] = "v2"
    rerun_from_job_id: Optional[str] = None
```

Existing endpoints (`/rewrite-jobs`, `/pipelines/{id}/run`) delegate to this unified runner for backward compatibility.

### 2. Job & ContentDraft Lifecycle

- **`Job`**:
  - `workflow_type`: Stored as `"article_workflow"` (or preserves `"legacy"`/`"rewrite"` alias for UI filtering).
  - `input_text`: Stores the `source_url`.
  - `status`: Transitions from `queued` -> `running` -> `completed` / `failed` / `cancelled`.
- **`ContentDraft`**:
  - Instantiated at Step 2 with `state = "generating"`.
  - Stores `pipeline_id`, `source_url`, `image_source`, and `image_kind = "url"`.
  - Updated upon completion of Step 3 & 4 with `title`, `content`, `caption`, `language`, `version += 1`, and `state = "ready_for_review"`.
  - Transitioned to `state = "published"` upon successful WordPress post creation.

## 5-Step Unified Pipeline Flow

### Step 1: Input & Pipeline Validation
- Validates `source_url` is a valid HTTP/HTTPS URL.
- Loads the active `Pipeline` record.
- Resolves account configurations (`ai`, `wp`, `fb`, `tg`).
- Validates that mandatory accounts (`ai` and `wp`) are present. Rejects immediately if either is missing.

### Step 2: Source Ingestion & Pattern Collection
- Fetches article data using `WordPressSourceGateway.fetch(source_url)`:
  - Extracts `title`, `content`, and `image_url` via WordPress REST API or standardized HTML parser fallback.
- If `pipeline.settings.collect_patterns` is enabled:
  - Dispatches source data to `PatternCollectionService.collect(...)`.
- Initializes `ContentDraft` record with source content and image URL.
- Emits progress: 10% (`fetch_source`).

### Step 3: AI Processing Core (The Only Branching Point)
Progress is reported per chunk (10% to 85%), updating chunk index, total chunks, word counts, and elapsed milliseconds.

- **Branch A — Mode V1 (Deterministic Translation)**:
  - Translates original title faithfully.
  - Splits source content into chunks by `translation_chunk_size` (default 6,000 characters).
  - Translates chunks sequentially or concurrently based on `translation_mode` and `translation_max_concurrency`.
  - Maintains `_tail_paragraph_context` across chunks to preserve terminology, pronouns, and flow.
  - Extracts teaser caption with localized Call-To-Action (CTA).
  - Returns `{ "title": translated_title, "content": translated_content, "caption": caption, "warnings": [] }`.

- **Branch B — Mode V2 (Dramatic Rewrite)**:
  - Executes `RewriteEngine.rewrite(...)`.
  - Splits source content into chunks.
  - Multi-turn conversation history (`_history_messages`) preserves all preceding source and rewritten turns to ensure narrative continuity.
  - Generates dramatic re-creation in target language with localized syntax and style.
  - Requests JSON metadata for a new creative title and exact verbatim opening prefix teaser caption.
  - Returns `{ "title": new_title, "content": rewritten_story, "caption": caption, "caption_matches_prefix": bool, "warnings": [...] }`.

### Step 4: Draft Assembly & Quality Validation
- Validates word count ratio against source text (issues warning if outside 70%–130%).
- Verifies caption prefix fidelity (`caption_matches_prefix`).
- Updates `ContentDraft` with assembled `title`, `content`, `caption`, `language`.
- Transitions `draft.state = "ready_for_review"`.
- Emits progress: 90% (`prepare_publish`).

### Step 5: Multi-Channel Publishing Hub
Publishes following a prioritized distribution order:

1. **WordPress (Mandatory Core)**:
   - Invokes `WordPressPublishingService.publish(draft.id, confirmed=True)`.
   - Creates post, attaches featured media, sets target category.
   - Stores `wp_post_id`, `wp_url`, `wp_status` on `ContentDraft`.
   - If WordPress publishing fails, marks `draft.state = "publish_failed"` (or `"publish_unknown"` on network ambiguity) and stops subsequent channels.
2. **Facebook Page (Optional Secondary)**:
   - If `pipeline.step_accounts.fb` is configured:
     - Posts teaser caption, featured image, and WordPress URL via `FacebookPagePublisher`.
     - Logs `fb_post_id` or warning on social API failure (does not invalidate successful WordPress publication).
3. **Telegram Channel (Optional Secondary)**:
   - If `pipeline.step_accounts.tg` is configured:
     - Sends summary message with WordPress URL via `send_telegram_msg`.
     - Logs notification event or warning.
4. **Job Finalization**:
   - Calls `jobs.complete(job_id, payload)` with complete publishing summary and warnings.

## Resilience & Error Handling

- **Real-time Cancellation**:
  - DB is queried during chunk progress. If `job.status == "cancelled"`, throws `InterruptedError`.
  - Sets `draft.state = "generation_failed"` with `"Generation was cancelled"`.
  - Aborts any further publishing or AI requests.
- **Error Sanitization**:
  - All caught exceptions pass through `sanitize_error(str(exc))[:500]` to eliminate leaked secrets and sensitive URLs.
  - Clear error categorization: `generation_failed` vs `publish_failed` / `publish_unknown`.
- **Unified Retries**:
  - Failed or interrupted jobs (both V1 and V2) support retry via `rerun_from_job_id`.
  - Restores `pipeline_id`, `source_url`, and original `mode` without duplicating unneeded draft history.

## Testing Strategy

- **`tests/services/test_article_workflow_service.py`**:
  - V1 execution end-to-end: translation, draft creation, multi-channel dispatch.
  - V2 execution end-to-end: rewrite engine, multi-turn history, draft creation, WordPress publish.
  - Cancellation mid-chunk with `InterruptedError`.
  - Missing account validations and error sanitization.
  - Retry execution from failed job ID.
- **API and Backward Compatibility**:
  - Verify `/article-workflows/run`, `/rewrite-jobs`, and `/pipelines/{id}/run`.
- **Frontend E2E**:
  - Verify V1 and V2 buttons in Dashboard QuickRun.
  - Verify URL input validation and timeline step progression.
