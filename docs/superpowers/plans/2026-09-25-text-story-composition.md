# Text Story Composition Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a page that turns pasted source text into a short rewrite, title, copyable image prompt, and complete WordPress-ready story.

**Architecture:** A dedicated composition row stores source and intermediate artifacts beside an existing `ContentDraft`. A four-stage background service calls the existing OpenAI-compatible account in order, persists each result, and exposes it through a small API. The page reuses the current pipeline selector, progress display, draft editor, and WordPress publishing path.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy, SQLite migrations, pytest, React 19, TypeScript, TanStack Query, Playwright.

**Spec:** `docs/superpowers/specs/2026-09-25-text-story-composition-design.md`

## Global Constraints

- Requests run in this order: rewrite, title, image prompt, continuation.
- The title and image prompt use the 550–650-word rewrite, never the complete story.
- The continuation uses separate rewrite and enhance user messages with the saved assistant rewrite between them.
- The continuation is one model response of at least 3,000 words; do not split it into scenes or silently trim input.
- All reader-facing outputs use the pipeline language.
- The image prompt is copyable text; do not generate an image.
- Code joins the saved rewrite verbatim with the continuation once.
- No automatic WordPress publication.
- `docs/rewrite.md` and `docs/enhance.md` exist locally but are untracked; copy their approved intent into versioned Python templates during Task 2. Runtime must not read these Markdown files.

## File Map

| File | Responsibility |
|---|---|
| `app/db/models.py`, `app/db/migrations.py` | Composition row and repeatable migration 11 |
| `app/domain/text_story_prompts.py` | Versioned rewrite/enhance/title/image instructions and message builders |
| `app/domain/text_story_validation.py` | Word counts, completion checks, exact assembly, caption |
| `app/integrations/ai/openai_compatible.py` | Model response metadata without changing existing `chat()` callers |
| `app/services/text_story_workflow_service.py` | Four-stage persistence, retry, cancellation checks |
| `app/api/routes/text_story_jobs.py`, `app/api/workflow_schemas.py` | Start, read artifacts, retry contracts |
| `app/api/main.py`, `app/api/routes/content_drafts.py`, `app/services/content_draft_service.py` | Router, new draft kind, publish/deletion integration |
| `frontend/src/pages/TextStory/index.tsx` | Two-column input, progress, artifacts, draft editor, history |
| `frontend/src/api/workflows.ts`, `frontend/src/api/types.ts`, `frontend/src/App.tsx`, `frontend/src/components/Sidebar.tsx` | Typed calls, route, navigation |

## Review Focus

1. A source story longer than the provider context: reject with a clear error and retain the source; test in Task 3.
2. An AI response with visible text but `finish_reason="length"`: reject that stage and preserve prior artifacts; test in Task 2 and Task 3.
3. A retry after title or image prompt succeeds: skip completed requests and do not overwrite saved title/prompt; test in Task 3.
4. Cancellation after rewrite: keep the rewrite and prevent continuation and publication; test in Task 3.
5. Deleting an unpublished composition draft: remove its composition row without touching other drafts; test in Task 1.

---

### Task 1: Persist composition artifacts and recognize the draft kind

**Files:**
- Modify: `app/db/models.py`
- Modify: `app/db/migrations.py`
- Modify: `app/api/workflow_schemas.py`
- Modify: `app/services/content_draft_service.py`
- Modify: `tests/db/test_migrations.py`
- Create: `tests/services/test_text_story_persistence.py`

**Interfaces:**
- Produces: `models.TextStoryComposition` with `draft_id: str`, `source_text: str`, `rewrite_text: str`, `continuation_text: str`, `image_prompt: str`, `prompt_version: str`, `stage_status: dict[str, str]`. The draft kind is `"text_story"`.
- Consumes: Existing `ContentDraft`, `run_migrations`, and `ContentDraftService.delete`.

- [ ] **Step 1: Write persistence tests.**

```python
def test_composition_is_unique_per_draft(test_db):
    draft = models.ContentDraft(kind="text_story", state="generating")
    test_db.add(draft); test_db.flush()
    record = models.TextStoryComposition(
        draft_id=draft.id, source_text="source", prompt_version="text-story-v1",
        stage_status={"rewrite": "pending", "title": "pending", "image_prompt": "pending", "enhance": "pending"},
    )
    test_db.add(record); test_db.commit()
    assert test_db.query(models.TextStoryComposition).filter_by(draft_id=draft.id).one().source_text == "source"
    test_db.add(models.TextStoryComposition(
        draft_id=draft.id, source_text="duplicate", prompt_version="text-story-v1",
        stage_status={},
    ))
    with pytest.raises(IntegrityError):
        test_db.commit()
    test_db.rollback()
    assert ContentDraftService(test_db).delete(draft.id) is True
    assert test_db.query(models.TextStoryComposition).filter_by(draft_id=draft.id).count() == 0
```

Extend `tests/db/test_migrations.py` to assert `text_story_compositions` exists, `schema_migrations` count is 11, and running migrations twice leaves one table and no extra backup.

- [ ] **Step 2: Run the focused tests; verify they fail because the model/table is absent.**

Run: `uv run pytest -q tests/services/test_text_story_persistence.py tests/db/test_migrations.py`

- [ ] **Step 3: Add the model and idempotent migration.**

```python
class TextStoryComposition(Base):
    __tablename__ = "text_story_compositions"
    id = Column(String, primary_key=True, default=generate_uuid)
    draft_id = Column(String, ForeignKey("content_drafts.id"), unique=True, nullable=False)
    source_text = Column(Text, nullable=False)
    rewrite_text = Column(Text, default="", nullable=False)
    continuation_text = Column(Text, default="", nullable=False)
    image_prompt = Column(Text, default="", nullable=False)
    prompt_version = Column(String, nullable=False)
    stage_status = Column(JSON, default=dict, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
```

Add migration 11 with `CREATE TABLE IF NOT EXISTS` and a unique index on `draft_id`. Add `"text_story"` to `DraftKind`. In `ContentDraftService.delete`, delete the linked composition row before deleting an unpublished draft; keep the existing published-draft rejection.

- [ ] **Step 4: Run focused tests and commit.**

Run: `uv run pytest -q tests/services/test_text_story_persistence.py tests/db/test_migrations.py`
Expected: PASS.
Commit: `git add app/db/models.py app/db/migrations.py app/api/workflow_schemas.py app/services/content_draft_service.py tests/db/test_migrations.py tests/services/test_text_story_persistence.py && git commit -m "feat: persist text story composition artifacts"`

### Task 2: Define prompts, response metadata, and exact text validation

**Files:**
- Create: `app/domain/text_story_prompts.py`
- Create: `app/domain/text_story_validation.py`
- Modify: `app/integrations/ai/openai_compatible.py`
- Create: `tests/domain/test_text_story_prompts.py`
- Create: `tests/domain/test_text_story_validation.py`
- Modify: `tests/integrations/test_openai_compatible.py`

**Interfaces:**
- Produces: `build_rewrite_messages(source: str, language: str) -> list[dict]`; `build_title_messages(rewrite: str, language: str) -> list[dict]`; `build_image_prompt_messages(rewrite: str, language: str) -> list[dict]`; `build_enhance_messages(source: str, rewrite: str, language: str) -> list[dict]`; `validate_stage(stage: str, result: AITextResult, rewrite: str = "") -> str`; `assemble_story(rewrite: str, continuation: str) -> tuple[str, str]`.
- Produces: `AITextResult(content: str, model: str, finish_reason: str | None, usage: dict)` and `OpenAICompatibleAIClient.chat_with_meta(messages, *, priority="foreground") -> AITextResult`.
- Consumes: The current chat-completions provider and the approved wording in `docs/rewrite.md` and `docs/enhance.md`.

- [ ] **Step 1: Write failing tests for history, truncation, word counts, and caption.**

```python
def test_enhance_history_preserves_two_prompts_and_saved_rewrite():
    messages = build_enhance_messages("Original plot", "Rewritten opening.", "Polish")
    assert [item["role"] for item in messages] == ["system", "user", "assistant", "user"]
    assert "Original plot" in messages[1]["content"]
    assert messages[2]["content"] == "Rewritten opening."
    assert "continuation" in messages[3]["content"].lower()

def test_visible_but_truncated_response_is_invalid():
    result = AITextResult("word " * 600, "model", "length", {"completion_tokens": 600})
    with pytest.raises(ValueError, match="incomplete"):
        validate_stage("rewrite", result)

def test_assembly_keeps_rewrite_once_and_caption_exact():
    content, caption = assemble_story("First sentence. Second sentence.", "The end.")
    assert content == "First sentence. Second sentence.\n\nThe end."
    assert content.startswith(caption)
```

In the integration test, mock `requests.post` returning `choices[0].finish_reason="length"` and `usage`; assert `chat_with_meta` retains both without changing the behavior of `chat()`.

- [ ] **Step 2: Run the focused tests; verify the new functions are absent.**

Run: `uv run pytest -q tests/domain/test_text_story_prompts.py tests/domain/test_text_story_validation.py tests/integrations/test_openai_compatible.py`

- [ ] **Step 3: Implement versioned prompt builders and validation.**

```python
PROMPT_VERSION = "text-story-v1"
def build_enhance_messages(source: str, rewrite: str, language: str) -> list[dict]:
    return [
        {"role": "system", "content": f"Write all reader-facing text in {language}."},
        {"role": "user", "content": rewrite_instruction(language) + "\n\n<source_story>\n" + source + "\n</source_story>"},
        {"role": "assistant", "content": rewrite},
        {"role": "user", "content": enhance_instruction(language) +
         "\nReturn ONLY the NEW continuation; do not repeat the rewrite. Continue the immediately preceding assistant story."},
    ]

@dataclass(frozen=True)
class AITextResult:
    content: str
    model: str
    finish_reason: str | None
    usage: dict
```

Copy the story requirements from the two source prompts into `rewrite_instruction` and `enhance_instruction`, replacing fixed English with `language` and the enhance demand to reprint the source with the continuation-only rule. Include the 550–650 and 3,000–3,500 word instructions, cliffhanger, exact character continuity, and complete ending. Implement title/image instructions from the approved spec. `chat_with_meta` should parse `choices[0].message.content`, `choices[0].finish_reason`, `usage`, and `model`. Do not log the message body. `validate_stage` rejects empty, `length`/`incomplete` finishes, out-of-range rewrite, under-3,000-word continuation, copied rewrite prefix, and missing sentence ending. `assemble_story` joins with one blank line and derives a 45–70-word sentence-boundary caption from the rewrite.

- [ ] **Step 4: Run focused tests and commit.**

Run: `uv run pytest -q tests/domain/test_text_story_prompts.py tests/domain/test_text_story_validation.py tests/integrations/test_openai_compatible.py`
Expected: PASS.
Commit: `git add app/domain/text_story_prompts.py app/domain/text_story_validation.py app/integrations/ai/openai_compatible.py tests/domain/test_text_story_prompts.py tests/domain/test_text_story_validation.py tests/integrations/test_openai_compatible.py && git commit -m "feat: add text story prompt and validation core"`

### Task 3: Run and resume the four-stage background workflow

**Files:**
- Create: `app/services/text_story_workflow_service.py`
- Create: `app/api/routes/text_story_jobs.py`
- Modify: `app/api/workflow_schemas.py`
- Modify: `app/api/main.py`
- Create: `tests/services/test_text_story_workflow_service.py`
- Create: `tests/api/test_text_story_jobs.py`

**Interfaces:**
- Consumes: Task 1 composition model; Task 2 builders, validator, assembler, and `chat_with_meta`.
- Produces: `TextStoryWorkflowService.execute(job_id: str, draft_id: str) -> None` and `POST /text-story-jobs`, `GET /text-story-jobs/{draft_id}/artifacts`, `POST /text-story-jobs/{draft_id}/retry`.
- API input: `TextStoryJobInput(pipeline_id: str, source_text: str)`. Artifacts response: `source_text`, `rewrite_text`, `image_prompt`, `continuation_text`, `stage_status`, `prompt_version`.

- [ ] **Step 1: Write service and API tests with a fake AI client.**

```python
def test_run_saves_each_stage_and_uses_rewrite_for_metadata(test_db, monkeypatch):
    calls = []
    class FakeAI:
        def chat_with_meta(self, messages, **kwargs):
            calls.append(messages)
            body = ["Opening. " * 600, "A title", "A bright room with two people", "Ending. " * 3100][len(calls) - 1]
            return AITextResult(body.strip(), "fake", "stop", {})
    monkeypatch.setattr("app.services.text_story_workflow_service.create_ai_client", lambda account: FakeAI())
    TextStoryWorkflowService.execute("job-id", "draft-id")
    assert len(calls) == 4
    assert "Opening." in calls[1][-1]["content"]
    assert "Ending." not in calls[2][-1]["content"]
    assert calls[3][-2]["role"] == "assistant"
```

Use real seeded job/draft/AI/WP account rows in the fixture. Add tests for missing AI/WP accounts, a pipeline with an empty target language, oversized source against a configured model context limit, interrupted/length-limited stage preserving prior artifacts, retry skipping completed stages, cancellation after rewrite, and concurrent retry returning 409 instead of issuing duplicate requests. API tests assert that start saves source before scheduling, list/read responses omit API secrets, and retry reuses the draft.

- [ ] **Step 2: Run focused tests; verify service and route are absent.**

Run: `uv run pytest -q tests/services/test_text_story_workflow_service.py tests/api/test_text_story_jobs.py`

- [ ] **Step 3: Implement ordered stage execution and endpoints.**

```python
STAGES = ("rewrite", "title", "image_prompt", "enhance")
for stage in STAGES:
    if composition.stage_status.get(stage) == "completed":
        continue
    check_cancelled(job_id)
    messages = {
        "rewrite": build_rewrite_messages(composition.source_text, draft.language),
        "title": build_title_messages(composition.rewrite_text, draft.language),
        "image_prompt": build_image_prompt_messages(composition.rewrite_text, draft.language),
        "enhance": build_enhance_messages(composition.source_text, composition.rewrite_text, draft.language),
    }[stage]
    result = ai.chat_with_meta(messages)
    value = validate_stage(stage, result, composition.rewrite_text)
    save_stage(db, composition, draft, stage, value, result)
```

Define `check_cancelled(job_id)` and `save_stage(db, composition, draft, stage, value, result)` in this service. Persist the artifact and a copied `stage_status` JSON after each accepted response. Store only model, elapsed time, token usage, and finish reason in job output/log metadata; sanitize errors. For source preflight, use optional `account.config["context_length"]` and `account.config["max_output_tokens"]` when available; reject impossible single-response continuation, otherwise mark capacity unverified and rely on completion checks. Require a nonempty pipeline language. Start and retry routes create a job with `workflow_type="text_story"` and run `execute` through `workflow_runner`. Serialize retries per draft with a lock and reject an active run with 409.

- [ ] **Step 4: Run focused tests and commit.**

Run: `uv run pytest -q tests/services/test_text_story_workflow_service.py tests/api/test_text_story_jobs.py`
Expected: PASS.
Commit: `git add app/services/text_story_workflow_service.py app/api/routes/text_story_jobs.py app/api/workflow_schemas.py app/api/main.py tests/services/test_text_story_workflow_service.py tests/api/test_text_story_jobs.py && git commit -m "feat: orchestrate resumable text story jobs"`

### Task 4: Add the two-column Text Story page

**Files:**
- Create: `frontend/src/pages/TextStory/index.tsx`
- Modify: `frontend/src/api/workflows.ts`
- Modify: `frontend/src/api/types.ts`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/Sidebar.tsx`
- Modify: `frontend/src/components/Layout.tsx`
- Modify: `frontend/src/pages/Dashboard/components/JobCard.tsx`
- Create: `frontend/e2e/text-story.spec.ts`

**Interfaces:**
- Consumes: Task 3 start, artifacts, retry endpoints; current `getDraft`, `getDrafts`, `getJob`, `cancelJob`, `DraftEditor`, `DraftHistory`, `PipelineSelect`.
- Produces: route `/text-story` and page-specific history for draft kind `text_story`.

- [ ] **Step 1: Write an E2E scenario against intercepted API calls.**

```typescript
test('shows saved rewrite and copyable image prompt before full draft', async ({ page }) => {
  await page.goto('/text-story');
  await page.getByLabel('Source story').fill('A long source story.');
  await page.getByRole('button', { name: 'Create story' }).click();
  await expect(page.getByText('Short rewrite')).toBeVisible();
  await expect(page.getByText('Image prompt')).toBeVisible();
  await expect(page.getByText('Review & publish')).toBeVisible();
});
```

Mock pipelines, start response, job progression, artifact response, and draft response like `frontend/e2e/rewrite.spec.ts`. Add a second scenario for failed enhance with retained rewrite/title/prompt and a retry button; confirm WP publishing is unavailable until `ready_for_review`.

- [ ] **Step 2: Run TypeScript and E2E; verify route is absent.**

Run: `cd frontend && pnpm build && pnpm test:e2e -- e2e/text-story.spec.ts`
Expected: new E2E fails before page implementation.

- [ ] **Step 3: Implement typed API calls and the page.**

```typescript
export interface TextStoryArtifacts {
  source_text: string;
  rewrite_text: string;
  continuation_text: string;
  image_prompt: string;
  prompt_version: string;
  stage_status: Record<'rewrite' | 'title' | 'image_prompt' | 'enhance', string>;
}
export const startTextStory = (pipeline_id: string, source_text: string) =>
  client.post<{ job_id: string; draft_id: string }>('/text-story-jobs', { pipeline_id, source_text });
export const getTextStoryArtifacts = (draftId: string) =>
  client.get<TextStoryArtifacts>(`/text-story-jobs/` + draftId + '/artifacts');
```

Implement the page using the existing two-column Generate Story structure: left pipeline selector with `requiresAI` and `requiresWP`, source textarea, run/retry/cancel controls, and four progress steps; right short rewrite with Copy button and image prompt with Copy button. Mount `DraftEditor` for title/full story only when draft state is `ready_for_review` or a later publish state; show saved read-only artifacts while generation is incomplete, so its publish button cannot be used early. Bottom history is filtered to `kind="text_story"`. Poll job and artifacts while active. On open from history, restore source and artifacts. Register the route, sidebar label, layout title, and job recovery path. Keep the existing `DraftEditor` publish action as the only publication path.

- [ ] **Step 4: Run frontend checks and commit.**

Run: `cd frontend && pnpm build && pnpm lint && pnpm test:e2e -- e2e/text-story.spec.ts`
Expected: PASS.
Commit: `git add frontend/src/pages/TextStory/index.tsx frontend/src/api/workflows.ts frontend/src/api/types.ts frontend/src/App.tsx frontend/src/components/Sidebar.tsx frontend/src/components/Layout.tsx frontend/src/pages/Dashboard/components/JobCard.tsx frontend/e2e/text-story.spec.ts && git commit -m "feat: add text story composition page"`

### Task 5: Wire WordPress publishing and verify the complete path

**Files:**
- Modify: `app/api/routes/content_drafts.py`
- Modify: `tests/api/test_text_story_jobs.py`
- Modify: `tests/services/test_wordpress_publishing_service.py`
- Modify: `frontend/e2e/text-story.spec.ts`

**Interfaces:**
- Consumes: `ContentDraft.kind="text_story"`, `DraftEditor`, and `WordPressPublishingService.publish`.
- Produces: the existing `POST /content-drafts/{draft_id}/publish` path for text-story drafts.

- [ ] **Step 1: Write the failing publish test.**

```python
def test_text_story_draft_uses_existing_wordpress_publish_route(client, test_db, monkeypatch):
    draft = models.ContentDraft(
        kind="text_story", pipeline_id="pipeline-with-wp", state="ready_for_review",
        title="Title", content="Opening.\n\nEnding.", wp_status="draft",
    )
    test_db.add(draft); test_db.commit()
    response = client.post(
        f"/content-drafts/{draft.id}/publish",
        json={"confirmed": True},
    )
    assert response.status_code == 200
    assert response.json()["kind"] == "text_story"
```

In the fixture, stub only the WordPress gateway, not the draft service. Assert source text and image prompt do not appear in the WordPress body, and publishing before `ready_for_review` is rejected. Extend E2E to verify the default action is `Create WP draft` and that no publish request occurs after generation.

- [ ] **Step 2: Run the focused tests; verify the current draft-kind mapping rejects text_story.**

Run: `uv run pytest -q tests/api/test_text_story_jobs.py tests/services/test_wordpress_publishing_service.py`

- [ ] **Step 3: Add the new kind to the existing publish mapping and readiness guard.**

```python
workflow_type = {
    "manual": "wp_publish",
    "rewrite": "rewrite",
    "generated": "generate_story",
    "text_story": "text_story",
    "article_workflow": "article_workflow",
    "article_v1": "article_v1",
    "article_v2": "article_v2",
}[draft.kind]
if draft.kind == "text_story" and draft.state != "ready_for_review":
    raise HTTPException(status_code=409, detail="Story is not ready for review")
```

Preserve the existing explicit confirmation for public publication, category, optional uploaded/remote image, and draft version checks. Do not add automatic publication to the generation service.

- [ ] **Step 4: Run targeted plus existing workflow tests and commit.**

Run: `uv run pytest -q tests/api/test_text_story_jobs.py tests/services/test_wordpress_publishing_service.py tests/services/test_article_workflow_service.py tests/domain/test_story_agent.py`
Run: `cd frontend && pnpm build && pnpm test:e2e -- e2e/text-story.spec.ts`
Expected: PASS.
Commit: `git add app/api/routes/content_drafts.py tests/api/test_text_story_jobs.py tests/services/test_wordpress_publishing_service.py frontend/e2e/text-story.spec.ts && git commit -m "feat: publish reviewed text story drafts"`

## Final Verification

- Run `uv run pytest -q` and `cd frontend && pnpm build && pnpm lint` once after all tasks pass.
- Review the generated plan and implementation against every section of the spec, including retry after restart, source preservation, one-response enhance, and no automatic image generation or publication.
- Confirm `git status --short` contains only the three pre-existing untracked prompt/reference files, unless the operator has changed them independently.
