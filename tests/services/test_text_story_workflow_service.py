import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import models
from app.db.session import Base
from app.integrations.ai.openai_compatible import AITextResult
from app.services.text_story_workflow_service import TextStoryWorkflowService


@pytest.fixture
def seeded(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'story.db'}")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    monkeypatch.setattr("app.services.text_story_workflow_service.SessionLocal", sessions)
    with sessions() as db:
        db.add_all([
            models.Account(id="ai", name="AI", type="ai", config={"api_key": "secret", "text_model": "m"}),
            models.Account(id="wp", name="WP", type="wp", config={}),
            models.Pipeline(id="pipe", name="Pipe", type="rewrite", language="Polish",
                            step_accounts={"ai": "ai", "wp": "wp"}, is_active=True),
            models.ContentDraft(id="draft", kind="text_story", pipeline_id="pipe", state="generating", language="Polish"),
            models.Job(id="job", pipeline_id="pipe", draft_id="draft", workflow_type="text_story", status="queued"),
            models.TextStoryComposition(draft_id="draft", source_text="Original plot", prompt_version="text-story-v1",
                                        stage_status={"rewrite": "pending", "title": "pending", "image_prompt": "pending", "enhance": "pending"}),
        ])
        db.commit()
    yield sessions
    engine.dispose()


def test_four_stages_use_saved_rewrite_and_publishable_assembly(seeded, monkeypatch):
    calls = []

    class FakeAI:
        def chat_with_meta(self, messages, **kwargs):
            calls.append(messages)
            body = ["Opening. " * 600, "A title", "A bright room with two people", "Ending. " * 3100][len(calls) - 1]
            return AITextResult(body.strip(), "fake", "stop", {"completion_tokens": 1})

    monkeypatch.setattr("app.services.text_story_workflow_service.create_ai_client", lambda account: FakeAI())
    TextStoryWorkflowService.execute("job", "draft")
    with seeded() as db:
        draft = db.get(models.ContentDraft, "draft")
        artifact = db.query(models.TextStoryComposition).filter_by(draft_id="draft").one()
        assert len(calls) == 4
        assert "Opening." in calls[1][-1]["content"]
        assert "Ending." not in calls[2][-1]["content"]
        assert calls[3][-2] == {"role": "assistant", "content": artifact.rewrite_text}
        assert draft.state == "ready_for_review"
        assert draft.content == artifact.rewrite_text + "\n\n" + artifact.continuation_text
        assert draft.content.startswith(draft.caption)
        assert artifact.stage_status == dict.fromkeys(("rewrite", "title", "image_prompt", "enhance"), "completed")


def test_failed_continuation_keeps_artifacts_and_retry_skips_completed(seeded, monkeypatch):
    calls = []

    class FakeAI:
        def chat_with_meta(self, messages, **kwargs):
            calls.append(messages)
            body = ["Opening. " * 600, "A title", "A bright room", "Ending. " * 3100][len(calls) - 1]
            return AITextResult(body.strip(), "fake", "length" if len(calls) == 4 else "stop", {})

    monkeypatch.setattr("app.services.text_story_workflow_service.create_ai_client", lambda account: FakeAI())
    TextStoryWorkflowService.execute("job", "draft")
    with seeded() as db:
        artifact = db.query(models.TextStoryComposition).filter_by(draft_id="draft").one()
        assert artifact.rewrite_text and artifact.image_prompt
        assert artifact.stage_status["enhance"] == "failed"
        assert db.get(models.ContentDraft, "draft").state == "generation_failed"
        db.add(models.Job(id="retry", pipeline_id="pipe", draft_id="draft", workflow_type="text_story", status="queued"))
        db.commit()
    calls.clear()

    class RetryAI:
        def chat_with_meta(self, messages, **kwargs):
            calls.append(messages)
            return AITextResult(("Ending. " * 3100).strip(), "fake", "stop", {})

    monkeypatch.setattr("app.services.text_story_workflow_service.create_ai_client", lambda account: RetryAI())
    TextStoryWorkflowService.execute("retry", "draft")
    assert len(calls) == 1


@pytest.mark.parametrize("raises", [False, True])
def test_cancelled_worker_cannot_corrupt_new_retry(seeded, monkeypatch, raises):
    class OldAI:
        def chat_with_meta(self, messages, **kwargs):
            # A cancelled asyncio task leaves this worker thread running. A new retry begins
            # before the original provider request returns or raises.
            with seeded() as other:
                other.get(models.Job, "job").status = "cancelled"
                other.get(models.ContentDraft, "draft").state = "generating"
                other.add(models.Job(id="new", pipeline_id="pipe", draft_id="draft",
                                     workflow_type="text_story", status="queued"))
                other.commit()
            if raises:
                raise RuntimeError("provider failed after cancellation")
            return AITextResult(("Opening. " * 600).strip(), "fake", "stop", {})

    monkeypatch.setattr("app.services.text_story_workflow_service.create_ai_client", lambda account: OldAI())
    TextStoryWorkflowService.execute("job", "draft")
    with seeded() as db:
        assert db.get(models.ContentDraft, "draft").state == "generating"
        assert db.get(models.Job, "new").status == "queued"
        item = db.query(models.TextStoryComposition).filter_by(draft_id="draft").one()
        assert item.stage_status["rewrite"] == "pending"
