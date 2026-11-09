# WordPress Publisher Pipeline Input Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Add a manual title/content/image input mode to WordPress Publisher that executes the existing Dashboard article pipeline, preserving direct publishing.

**Architecture:** Persist manual source input in WorkflowRecovery before scheduling an article job. Branch only source preparation, then reuse ArticleWorkflowService translation, rewriting, quota scheduling, publication and delivery recovery. Share image storage validation and reuse existing job UI.

**Tech Stack:** Python, FastAPI, SQLAlchemy/SQLite, pytest; React, TypeScript, TanStack Query, Tailwind, Playwright; existing requests-based publisher adapters.

**Spec:** `docs/superpowers/specs/2026-11-09-wordpress-publisher-pipeline-input-design.md` (approved).

## Global Constraints

- Chế độ đăng trực tiếp hiện tại tiếp tục hoạt động như cũ.
- Không tạo một bộ dịch, scheduler hoặc bộ đăng đa kênh riêng.
- Title và content bắt buộc, không chấp nhận chỉ có khoảng trắng.
- Content đầu vào là văn bản thuần, giữ xuống dòng.
- `source_url` để trống cho nguồn nhập tay; không tạo URL giả.
- Bản ghi cũ thiếu source_kind được hiểu là nguồn URL, giữ tương thích.
- Không tạo URL giả hoặc tự thêm bài nhập tay vào Pattern Library.
- Không thêm tính năng sinh ảnh AI.
- Không cần migration cấu trúc bảng mới.
- Không thay DB người dùng hoặc cấu hình account trong quá trình kiểm thử.
- Dùng mock cho AI và các nền tảng đăng bài; không phát sinh API trả phí hay đăng bài thật khi kiểm thử.
- No release build, unrelated refactor, dependency upgrades, or new multi-pipeline execution.

## Review Focus

1. A process interruption after intake commit but before worker dispatch must retain source and produce a retryable attempt (Task 2/4).
2. Retrying from Dashboard must work for a manual article with no input URL, including uncertain delivery resolution (Task 4/5).
3. Switching modes while inputs or an active job exist must not erase fields, cancel jobs or start another run (Task 5).
4. Uploaded image files must survive restart/retry and be sent as files to Facebook, with rejected/rolled-back uploads cleaned (Task 1/2/3).
5. Concurrent URL and manual jobs sharing credentials must use one quota limit; cancellation and duplicate retry must not overwrite a newer attempt (Task 4).

## Workspace and implementation rules

The checkout contains earlier approved implementation and unrelated user edits, including the translation recovery upgrade. Treat that state as the baseline. Record `git diff` and untracked paths in a workspace-local progress directory before edits. Do not move, reset or broadly stage the working tree. Use only path/hunk-scoped commits of this feature's changes; if a shared file cannot safely be separated, leave its change reviewable and report that instead of committing unrelated work. Do not create a clean worktree from HEAD alone: HEAD lacks required uncommitted recovery code.

Use `.venv/bin/python`, `.venv/bin/pytest` and Node 24 at `/Users/admin/.nvm/versions/node/v24.13.0/bin`. Frontend commands run in `frontend/` with that directory on PATH. When localhost binding/browser execution is denied by sandbox, rerun that command with the required escalation.

## File map and boundaries

| File | Responsibility |
|---|---|
| Create `app/services/draft_image_storage.py` | Shared upload validation, disk storage and cleanup |
| Modify `app/api/routes/content_drafts.py` | Delegate existing upload to shared storage without changing API |
| Create `app/services/article_workflow_intake.py` | Freeze manifest, construct manual source, atomically persist manual draft/job/recovery |
| Modify `app/api/routes/article_workflows.py` | Multipart manual intake, shared dispatch, retry source-kind routing |
| Modify `app/services/article_workflow_service.py` | Manual source branch and file-aware Facebook dispatch; existing processing remains shared |
| Modify `app/integrations/publishers/facebook_page.py` | Local file multipart photo publication |
| Modify `frontend/src/api/workflows.ts` | Typed FormData client for manual input |
| Create `frontend/src/features/workflows/ArticleWorkflowOptions.tsx` | Pipeline + version inputs with shared version preference |
| Modify `frontend/src/pages/Dashboard/components/QuickRun.tsx` | Consume shared options while retaining URL/proxy/enrichment behavior |
| Create `frontend/src/pages/WordPressPublisher/components/PipelinePublisher.tsx` | Manual input form and selected job view |
| Modify `frontend/src/pages/WordPressPublisher/index.tsx` | Mode switch, retaining existing editor/form state |
| Modify `frontend/src/pages/Dashboard/index.tsx` | Article retries call retry endpoint before URL checks |
| Test files below | Focused intake, execution, recovery, image, quota and UI regression coverage |
| Modify `README.md` | Explain the two modes and automatic multi-channel run behavior |

No schema migration, separate worker pool, or changes to AI prompts are planned. Use existing JobCard, JobDetailsModal and DeliveryRecovery contracts; avoid duplicating their logic.

### Task 1: Share image upload storage and support Facebook file images

**Files:** create `app/services/draft_image_storage.py`, `tests/services/test_draft_image_storage.py`; modify `app/api/routes/content_drafts.py`, `app/integrations/publishers/facebook_page.py`; create `tests/integrations/test_facebook_page.py`.

**Interfaces:**
- `async store_draft_image(image: UploadFile) -> str` validates using ALLOWED_IMAGE_MIME, MAX_IMAGE_BYTES and validate_image_signature, stores under `var/uploads`, returns internal path, removes partial files on rejection. Validation errors are ValueError; route maps to HTTP 400.
- `FacebookPagePublisher.publish_photo_file(caption: str, image_path: str) -> str` returns confirmed post ID using multipart `source` file field. Keep URL and text methods unchanged.

- [x] Write failing tests for valid JPEG storage, MIME/signature mismatch, oversized/empty files and partial-file cleanup. Use `tmp_path` + monkeypatch.chdir, actual UploadFile, no production upload directory. Add a fake HTTP request test for multipart source and a closed file after return.

```python
def test_photo_file_uses_source_not_url(tmp_path, monkeypatch):
    from app.integrations.publishers.facebook_page import FacebookPagePublisher
    import app.integrations.publishers.facebook_page as module
    image = tmp_path / 'photo.jpg'
    image.write_bytes(b'\xff\xd8\xfftest')
    captured = {}
    class Response:
        status_code = 200
        def json(self): return {'post_id': 'post-1'}
    def post(url, **kwargs):
        captured.update(kwargs)
        assert kwargs['files']['source'].read() == image.read_bytes()
        assert 'url' not in kwargs['data']
        return Response()
    monkeypatch.setattr(module.requests, 'post', post)
    assert FacebookPagePublisher('page', 'token').publish_photo_file('Caption', str(image)) == 'post-1'
    assert captured['files']['source'].closed
```

- [x] Run `.venv/bin/pytest tests/services/test_draft_image_storage.py tests/integrations/test_facebook_page.py -q`; confirm failures identify missing behavior.
- [x] Extract the upload loop from content_drafts into store_draft_image. Preserve max size, filename uniqueness, signature checks, existing successful draft update/version increment and old image deletion. In Facebook adapter extend `_post` with optional `files=None`, pass files only when supplied, and implement:

```python
def publish_photo_file(self, caption: str, image_path: str) -> str:
    with open(image_path, 'rb') as source:
        body = self._post(f'{self.page_id}/photos',
                          {'caption': caption, 'published': 'true'},
                          files={'source': source})
    post_id = body.get('post_id') or body.get('id')
    if not post_id:
        raise ValueError('Facebook response is missing a post id')
    return post_id
```

- [x] Run focused tests and existing draft upload API tests with mocked network; compare status codes and image removal behavior.
- [x] Check `git diff --check`; commit only separable Task 1 changes with message `refactor: share publisher image storage and support Facebook files`.

### Task 2: Persist manual intake before dispatch

**Files:** create `app/services/article_workflow_intake.py`, `tests/api/test_manual_article_workflows.py`; modify `app/api/routes/article_workflows.py`, `app/services/article_workflow_service.py` (manifest construction only).

**Interfaces:**
- `build_article_manifest(db: Session, draft: ContentDraft, *, mode: str, source_kind: str = 'url', use_proxy: bool = False, use_enrichment: bool = False) -> dict`: same account/model/language/chunk size/translation settings and prompt version as current execute manifest; shared with execute, preserves URL semantics.
- `create_manual_article_attempt(db: Session, *, pipeline_id: str, mode: str, title: str, content: str, image_kind: str | None, image_source: str | None) -> tuple[Job, ContentDraft]`: validates active pipeline and typed AI/WP accounts, constructs and commits draft/job/recovery together, returns queued attempt; no network, no runner dispatch.
- New `POST /article-workflows/run-text`, multipart `pipeline_id`, `mode` (`v1` or `v2`), `title`, `content`, optional `image_url` or `image`; returns existing WorkflowJobCreated.
- Route-local shared `_schedule_article(job_id: str, draft_id: str, *, mode: str, use_proxy: bool = False, use_enrichment: bool = False) -> None` calls existing workflow_runner and run_workflow_blocking. Both endpoints use it.

- [x] Create isolated tmp SQLite fixture with dependency override and patch runner.start to inspect state before any execution. Add V1/V2 parametrized failing test; full source text including internal whitespace/newlines must be preserved.

```python
@pytest.mark.parametrize('mode', ['v1', 'v2'])
def test_manual_intake_is_durable_before_dispatch(client, db_factory, monkeypatch, mode):
    from app.api.routes.article_workflows import workflow_runner
    seen = []
    def start(job_id, operation):
        with db_factory() as db:
            job = db.get(models.Job, job_id)
            recovery = db.get(models.WorkflowRecovery, job.draft_id)
            assert recovery.manifest['source_kind'] == 'manual'
            assert recovery.artifacts['source']['content'] == 'First paragraph.\n\nSecond paragraph.'
            assert not db.get(models.ContentDraft, job.draft_id).source_url
            seen.append(job_id)
    monkeypatch.setattr(workflow_runner, 'start', start)
    response = client.post('/article-workflows/run-text', data={
        'pipeline_id': 'pipe', 'mode': mode, 'title': 'Source title',
        'content': 'First paragraph.\n\nSecond paragraph.',
    })
    assert response.status_code == 200, response.text
    assert seen == [response.json()['job_id']]
```

- [x] Add parameterized validation tests: missing/whitespace title/content, invalid mode, inactive/missing pipeline, missing/wrong account types, invalid image URL, URL+file together, invalid upload signature. Assert no runner call and no draft/job/recovery rows for rejected requests.
- [x] Run `.venv/bin/pytest tests/api/test_manual_article_workflows.py -q`, confirm expected failures.
- [x] Implement manifest builder using current execute values, defaulting old URL execution to source_kind=url. Snapshot manual input in recovery.artifacts.source (`title`, `content`, `image_url`, `source_url=None`, `image_kind`, `image_source`) with source_hash. Construct models in one session transaction, using flush for IDs rather than WorkflowJobService.create (which commits early).

```python
db.add(draft)
db.flush()
job = models.Job(pipeline_id=draft.pipeline_id, draft_id=draft.id,
                 workflow_type=f'article_{mode}', status='queued',
                 progress=0, input_type='prompt', input_text=title, logs=[], outputs={})
db.add(job)
db.flush()
db.add(models.WorkflowRecovery(draft_id=draft.id, active_job_id=job.id,
    manifest=manifest, artifacts={'source': source, 'source_hash': source_hash}, revision=0))
db.commit()
```

  Store original body only in source artifact before execution, not output draft.content. Keep title input as display text, never as retry source. Use Pydantic/explicit HTTP(S) validation for image URL, preserving URL query strings. Route deletes only its newly written upload when intake fails; never delete a file after a successful commit, even if dispatch fails.
- [x] Add failure injection tests: transaction rollback removes newly stored file and all three model rows; runner.start raising leaves committed source/file but marks job failed through WorkflowJobService and returns an error. Fresh attempt can recover that source. Retention pruning occurs after intake commit, without rolling back an already accepted run on prune failure.
- [x] Run new API tests and `tests/api/test_article_workflows.py`; check diff and commit only feature hunks with message `feat: accept durable manual article pipeline input`.

### Task 3: Run manual sources through the existing engines and publishers

**Files:** modify `app/services/article_workflow_service.py`; create `tests/services/test_manual_article_workflow_service.py`.

**Interfaces:** existing `ArticleWorkflowService.execute(job_id, draft_id, mode='v2', source_gateway=None, use_proxy=False, use_enrichment=False)` remains callable unchanged. Manual type is determined by recovery.manifest.source_kind, not a new public engine.

- [x] Write a tmp SQLite service fixture patching SessionLocal to that factory. Seed manual attempts through create_manual_article_attempt. Mock AI, RewriteEngine and all publishers; force WordPressSourceGateway.fetch, normalize_source_url, PatternCollectionService.collect and ArticleEnrichmentService.enqueue to raise if called for manual input.
- [x] Add parametrized engine tests and assert correct frozen pipeline language/options, source title/body, source image and final publication channels:

```python
@pytest.mark.parametrize('mode', ['v1', 'v2'])
@pytest.mark.parametrize('image_kind', [None, 'url', 'upload'])
def test_manual_input_uses_shared_processing(manual_run, mode, image_kind):
    run = manual_run(mode=mode, image_kind=image_kind)
    run.execute()
    assert run.calls['fetch'] == 0
    assert run.calls['collect'] == 0
    assert run.calls['enrich'] == 0
    assert run.calls['v1'] == (1 if mode == 'v1' else 0)
    assert run.calls['v2'] == (1 if mode == 'v2' else 0)
    assert run.calls['wordpress'] == 1
    assert run.calls['facebook_file'] == (1 if image_kind == 'upload' else 0)
    assert run.calls['telegram'] == 1
```

  Implement manual_run fixture with counters and real persisted models; use current service fake Publisher pattern in test_workflow_recovery.py. Persist fake WordPress ID/URL to exercise skip-on-retry correctly. Assertions on mock AI arguments must compare original content including paragraph breaks.
- [x] Run `.venv/bin/pytest tests/services/test_manual_article_workflow_service.py -q` and confirm missing source handling fails.
- [x] Read source_kind before source fetch/URL normalization. For manual, require nonempty saved source and load it with explicit fields (do not expand extra snapshot keys into a SourceArticle constructor). Use SimpleNamespace title/content/image_url/source_url only. Preserve draft image_kind/image_source from snapshot. Branch URL collection/enrichment as a whole so manual skips normalize_source_url, source_slug and URL lookups. Rejoin immediately before current shared V1/V2 branch.

```python
is_manual = manifest.get('source_kind', 'url') == 'manual'
if is_manual and not source_data:
    raise ValueError('Saved manual source is unavailable; start a new run')
# Source acquisition for URL remains in its existing branch.
if not is_manual:
    # Keep the current URL normalization/collection/enrichment block here.
    source_url = normalize_source_url(draft.source_url)
```

  Keep all existing AI/rewrite/publication logic once. At Facebook image selection use publish_photo_file for upload, publish_photo_caption for URL and publish_text without image, within existing receipt lock and pending-state logic. Keep source_kind default=url for historical jobs.
- [x] Add test for missing manual snapshot: fails clearly, never falls back to URL fetch or translated output. Assert no-image WordPress publication succeeds; image upload failure keeps existing warning behavior. Run new tests, `tests/services/test_article_workflow_service.py` and `tests/services/test_wordpress_publishing_service.py`.
- [x] Check diff and commit separable feature hunks with message `feat: reuse article execution for manual sources`.

### Task 4: Resume manual articles from persisted state and preserve shared quotas

**Files:** modify `app/api/routes/article_workflows.py`; extend `tests/api/test_manual_article_workflows.py`, `tests/services/test_manual_article_workflow_service.py`, `tests/domain/test_concurrent_workflows.py`.

**Interfaces:** `POST /article-workflows/{job_id}/retry` handles both source kinds; response unchanged. Existing URL retry, resolve-delivery endpoint and optimistic recovery ownership remain authoritative.

- [x] Write API tests for failed/cancelled manual retry with input_text missing or containing only a title; assert same draft, new job ID, frozen mode/options, no source_url normalization. Repeat retry and active-attempt tests assert rejection with no orphan queued job.
- [x] Add service scenario: fail first WordPress publish after translation; dispose/reopen sessions, mark interrupted work through recover_interrupted, retry via endpoint; assert body unchanged and translate called once. Add Facebook-only failure case with persisted WP receipt and Telegram-only failure case; each retry skips completed channels. Test publish_unknown requires resolve-delivery before republishing. Include cancelled old worker trying to save after new attempt owns recovery.

```python
assert first_response['draft_id'] == retry_response['draft_id']
assert first_response['job_id'] != retry_response['job_id']
assert calls['translate'] == 1
assert calls['wordpress'] == 2  # First was a definite failure; second succeeded.
assert saved_source['content'] == original_body
assert saved_source['image_source'] == original_image_path
```

- [x] Run new recovery tests and confirm they fail for current URL-only retry routing.
- [x] Split retry by recovery source_kind before consulting old_job.input_text. For manual, atomically claim old retry marker, create new job and keep draft/recovery source untouched; schedule shared executor. Preserve status filters, active job guard and rowcount CAS. Reuse a small helper for retry creation when possible instead of duplicating CAS logic. Do not hand-build source input from finished translation.
- [x] Add mixed-source quota test using real create_ai_client for the same account with mocked HTTP post and a threading event barrier: submit one URL workflow and one manual workflow, max_concurrency=1, assert observed inflight AI requests never exceed one and both complete. Reuse current concurrency tests' cancellation cleanup so no thread waits indefinitely; use event.wait(timeout=5), never sleep-only assertions. Both workflows use the same service and scheduler, with no quota code changes.
- [x] Run `.venv/bin/pytest tests/api/test_article_workflows.py tests/api/test_manual_article_workflows.py tests/services/test_manual_article_workflow_service.py tests/services/test_workflow_recovery.py tests/domain/test_concurrent_workflows.py -q`; check diff and commit feature hunks with message `fix: resume manual articles without requiring a source URL`.

### Task 5: Add Publisher pipeline mode using shared controls and job views

**Files:** create `frontend/src/features/workflows/ArticleWorkflowOptions.tsx`, `frontend/src/pages/WordPressPublisher/components/PipelinePublisher.tsx`, `frontend/e2e/wordpress-publisher-pipeline.spec.ts`; modify Publisher index, QuickRun, Dashboard index, frontend/src/api/workflows.ts; extend existing publisher/dashboard e2e where necessary.

**Interfaces:**
- `ManualArticleWorkflowInput = { pipelineId: string; mode: 'v1' | 'v2'; title: string; content: string; imageUrl?: string; image?: File }` and `startManualArticleWorkflow(input)` returning AxiosResponse<{job_id: string; draft_id: string; status: string}>.
- Shared `ArticleWorkflowOptions` consumes controlled pipelineId/mode, onPipelineChange, onModeChange, disabled; queries active pipelines with existing query key and filters AI+WP. Parent owns mode stored under existing `story-autogen-workflow-version` key. Options expose accessible labels `Select Pipeline`, version buttons `V1`/`V2`.
- `PipelinePublisher` owns text/image state, mutation and selected job ID. Use getJob, retryArticleWorkflow, cancelJob, JobCard, JobDetailsModal and existing delivery recovery UI. Poll the existing job resource while active; retain last selected job after reload using a dedicated localStorage job ID key, not article body storage.

- [x] Add failing Playwright tests using mockCommon and explicit mocks for pipeline list, run-text and GET /jobs/{id}. Cover selecting new mode and V2, multipart body preservation, URL/file exclusivity, optional remove-image, validation, error text retaining input, and job progress/result.

```typescript
test('switching publisher modes preserves unsent text', async ({ page }) => {
  await mockCommon(page);
  await page.goto('/#/wordpress-publisher');
  await page.getByRole('tab', { name: 'Pipeline workflow', exact: true }).click();
  await page.getByLabel('Source title', { exact: true }).fill('Original title');
  await page.getByLabel('Source content', { exact: true }).fill('Paragraph one.\n\nParagraph two.');
  await page.getByRole('tab', { name: 'Direct publishing', exact: true }).click();
  await page.getByRole('tab', { name: 'Pipeline workflow', exact: true }).click();
  await expect(page.getByLabel('Source content', { exact: true }))
    .toHaveValue('Paragraph one.\n\nParagraph two.');
});
```

  Mock all job network calls and inspect posted multipart Content-Type plus body fields. Test Dashboard retry of article_v1/v2 with input_text absent makes POST /retry, never POST /run; include prior source URL retry coverage and legacy/rewrite fallbacks.
- [x] Run `pnpm exec playwright test e2e/wordpress-publisher-pipeline.spec.ts --workers=1`; confirm missing mode/control behavior causes failures.
- [x] Add typed FormData client without setting a JSON Content-Type. Extract controlled pipeline/version fields from QuickRun into shared options while retaining QuickRun's proxy/enrichment validation and URL form. Move any shared version preference hook into ArticleWorkflowOptions module only if both parents need it, with explicit export `useArticleWorkflowVersion(): readonly ['v1' | 'v2', (value: 'v1' | 'v2') => void]`.

```typescript
export const startManualArticleWorkflow = (input: ManualArticleWorkflowInput) => {
  const form = new FormData();
  form.append('pipeline_id', input.pipelineId);
  form.append('mode', input.mode);
  form.append('title', input.title);
  form.append('content', input.content);
  if (input.imageUrl) form.append('image_url', input.imageUrl);
  if (input.image) form.append('image', input.image);
  return client.post<{ job_id: string; draft_id: string; status: string }>(
    '/article-workflows/run-text', form);
};
```

- [x] Add Tabs above Publisher existing content. Keep both subtrees mounted with hidden wrappers to preserve editor/form state; no CSS display hiding that leaves inactive inputs focusable. Keep manual history/editor together in direct mode and retain current state/query keys. Pipeline form uses existing Input/Textarea/Button/Card, disables submit during intake, holds input on error, and calls existing job handlers on success. Hide source proxy/enrichment controls in manual mode. No new prepublication confirmation.
- [x] Change Dashboard rerun mutation to route article_v1/article_v2/article_workflow through retryArticleWorkflow(job.id) before getJobInput; retain rewrite/legacy behavior and existing rerunning UI. Ensure DeliveryRecovery retry action uses same endpoint.

```typescript
if (['article_v1', 'article_v2', 'article_workflow'].includes(job.workflow_type ?? '')) {
  return retryArticleWorkflow(job.id);
}
const prompt = getJobInput(job); // Existing URL/legacy fallback follows.
```

- [x] Add browser cases for switching mode during a pending job without cancellation or second submission, stored V1/V2 shared selection, reopening selected job after reload, failed job retry and resolve-delivery visibility. At 375x667 and 1440x900 assert no horizontal page overflow and controls remain usable. Keep the existing direct publisher test unchanged except selectors genuinely made ambiguous by new tabs.
- [x] Run `pnpm exec playwright test e2e/wordpress-publisher.spec.ts e2e/wordpress-publisher-pipeline.spec.ts --workers=1`, `pnpm lint`, `pnpm exec tsc --noEmit`, `pnpm build`; check diff and commit feature hunks with message `feat: add pipeline input mode to WordPress Publisher`.

### Task 6: Verify integration and document behavior

**Files:** modify `README.md`; update this plan's checkboxes and record verification results under `.superpowers/sdd/wordpress-publisher-pipeline-2026-11-09/`.

**Interfaces:** no new product code; all functionality is exposed through the previous tasks' endpoints and UI.

- [x] Add README description near WordPress Publisher: direct mode unchanged, pipeline mode accepts title/plain content/optional URL or uploaded image, V1/V2 are Dashboard engines, Run publishes automatically to configured pipeline channels, URL collection/enrichment skipped, retry reuses original source and completed stages, no DB migration required.

```markdown
WordPress Publisher offers Direct publishing and Pipeline workflow modes.
Pipeline workflow accepts a title, plain text content and an optional image,
then runs the selected Dashboard V1/V2 workflow and its configured publishing
channels automatically. It skips URL fetching and URL-based source collection
and enrichment. Retry resumes saved work, including the original input and image.
```

- [x] Run `.venv/bin/pytest -q` against tests' temporary DBs. Do not start real publishing or use credentials from project config. Compare failures with baseline rather than changing unrelated code.
- [x] Run `pnpm lint`, `pnpm exec tsc --noEmit`, `pnpm build` and `pnpm exec playwright test --workers=1` from frontend; keep logs. Run `git diff --check` and review all changed paths for unrelated edits.
- [x] Inspect actual browser desktop/mobile screenshots of both modes using mocked API; verify existing Account modal scroll and unrelated navigation remain untouched. If live app needs restart for manual inspection, check for active jobs first and keep tests/mock requests separate from real account actions.
- [x] Review whole feature against spec: no fetch/manual source, both engines and all channels, no duplicate delivery, frozen retry, shared quotas, image lifetime, URL compatibility, no extra migration. Fix confirmed issues and repeat only affected checks.
- [x] Commit README and safely isolated remaining feature hunks with message `docs: explain WordPress Publisher pipeline mode`; report tests, limitations and working tree state. Do not claim release archives contain this feature or build them unless requested.

## Self-review record

- Spec coverage: UI/engine parity Task 3/5; intake/data/compatibility Task 2/4; images Task 1/3; retries/cancellation/limits Task 4; errors Task 1/2/4/5; documentation/full validation Task 6.
- Review Focus conditions are assigned explicit tests in their owning tasks.
- Interface consistency: mode v1/v2; source_kind manual/url; source artifact with separate immutable input; current article kinds, retry endpoint, API response and source snapshot contract preserved.
- Existing URL jobs without source_kind and current direct publishing have dedicated regression coverage.
- This plan requires no runtime/database/account changes during planning and no independent workflow implementation.

## Completion evidence

- Full mocked browser suite: 26 passed. Frontend build, lint and TypeScript checks passed.
- Independent read-only review found upload deletion before Facebook; fixed and verified with a real WordPress service/fake gateway regression. FB HTTP errors preserve response status for safe retry.
- Live app restarted only after confirming zero active jobs. Desktop/mobile read-only browser smoke passed against real pipelines; Account modal still scrolls.
- Database counts and integrity unchanged after live smoke; schema remains version 12. No paid AI calls or real publishing during tests.
- Shared files containing earlier baseline edits remain uncommitted; feature deltas and baseline preserved in the execution ledger directory. No merge/push/release requested.
