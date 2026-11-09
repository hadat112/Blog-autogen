import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import models
from app.db.session import Base
from app.services.article_workflow_service import ArticleWorkflowService


class DummySource:
    def __init__(self, title="Source Title", content="Source article text with many words.", image_url="https://img.test/photo.jpg"):
        self.source_url = "https://source.test/story"
        self.title = title
        self.content = content
        self.image_url = image_url


class DummyGateway:
    def __init__(self, source=None):
        self._source = source or DummySource()

    def fetch(self, url):
        return self._source


@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine)
    session = TestingSession()

    ai_acc = models.Account(id="ai_1", name="AI", type="ai", config={"api_key": "secret", "text_model": "test-model"})
    wp_acc = models.Account(id="wp_1", name="WP", type="wp", config={"url": "https://wp.test", "username": "admin", "password": "pwd"})
    fb_acc = models.Account(id="fb_1", name="FB", type="fb", config={"page_id": "page123", "access_token": "fb_token"})
    tg_acc = models.Account(id="tg_1", name="TG", type="tg", config={"bot_token": "tg_token", "chat_id": "12345"})

    pipe = models.Pipeline(
        id="pipe_1",
        name="Test Pipeline",
        type="rewrite",
        language="Italian",
        step_accounts={"ai": "ai_1", "wp": "wp_1", "fb": "fb_1", "tg": "tg_1"},
        settings={"collect_patterns": False},
        is_active=True,
    )
    session.add_all([ai_acc, wp_acc, fb_acc, tg_acc, pipe])
    session.commit()

    yield session, TestingSession
    session.close()


def test_article_workflow_v1_translates_and_publishes(test_db):
    session, TestingSession = test_db

    draft = models.ContentDraft(
        id="d1",
        kind="article_workflow",
        pipeline_id="pipe_1",
        source_url="https://source.test/story",
        state="generating",
    )
    job = models.Job(
        id="j1",
        pipeline_id="pipe_1",
        workflow_type="article_workflow",
        input_text="https://source.test/story",
        status="running",
        draft_id="d1",
    )
    session.add_all([draft, job])
    session.commit()

    mock_ai = MagicMock()
    mock_ai.translation_chunk_size = 6000
    mock_ai.translate_article_fields.return_value = {
        "title": "Titolo Tradotto",
        "content": "Testo dell'articolo tradotto completamente.",
        "caption": "Testo dell'articolo tradotto",
        "image_url": "https://img.test/photo.jpg",
    }

    mock_wp_pub = MagicMock()
    mock_pub_res = MagicMock()
    mock_pub_res.wp_post_id = 999
    mock_pub_res.wp_url = "https://wp.test/post-999"
    mock_pub_res.wp_status = "publish"
    mock_wp_pub.publish.return_value = mock_pub_res

    mock_fb = MagicMock()
    mock_fb.publish_photo_caption.return_value = "fb_post_123"

    with patch("app.services.article_workflow_service.SessionLocal", TestingSession), \
         patch("app.services.article_workflow_service.create_ai_client", return_value=mock_ai), \
         patch("app.services.article_workflow_service.WordPressPublishingService", return_value=mock_wp_pub), \
         patch("app.services.article_workflow_service.FacebookPagePublisher", return_value=mock_fb), \
         patch("app.services.article_workflow_service.send_telegram_msg") as mock_tg:

        ArticleWorkflowService.execute("j1", "d1", mode="v1", source_gateway=DummyGateway())

    session.refresh(job)
    session.refresh(draft)

    assert job.status == "success"
    assert job.outputs["wp_post_id"] == 999
    assert job.outputs["wp_url"] == "https://wp.test/post-999"
    assert job.outputs["fb_post_id"] == "fb_post_123"
    assert draft.title == "Titolo Tradotto"
    assert draft.state == "ready_for_review" or draft.wp_post_id == 999
    assert mock_ai.translate_article_fields.called
    assert mock_wp_pub.publish.called
    assert mock_fb.publish_photo_caption.called
    assert mock_tg.called


def test_article_workflow_v2_rewrites_and_publishes(test_db):
    session, TestingSession = test_db

    draft = models.ContentDraft(
        id="d2",
        kind="article_workflow",
        pipeline_id="pipe_1",
        source_url="https://source.test/story",
        state="generating",
    )
    job = models.Job(
        id="j2",
        pipeline_id="pipe_1",
        workflow_type="article_workflow",
        input_text="https://source.test/story",
        status="running",
        draft_id="d2",
    )
    session.add_all([draft, job])
    session.commit()

    mock_ai = MagicMock()
    mock_ai.translation_chunk_size = 6000

    mock_engine = MagicMock()
    mock_engine.rewrite.return_value = {
        "title": "Nuovo Titolo Drammatico",
        "content": "Una nuova storia riscritta in modo drammatico.",
        "caption": "Una nuova storia",
        "caption_matches_prefix": True,
        "warnings": [],
    }

    mock_wp_pub = MagicMock()
    mock_pub_res = MagicMock()
    mock_pub_res.wp_post_id = 1001
    mock_pub_res.wp_url = "https://wp.test/post-1001"
    mock_pub_res.wp_status = "publish"
    mock_wp_pub.publish.return_value = mock_pub_res

    with patch("app.services.article_workflow_service.SessionLocal", TestingSession), \
         patch("app.services.article_workflow_service.create_ai_client", return_value=mock_ai), \
         patch("app.services.article_workflow_service.RewriteEngine", return_value=mock_engine), \
         patch("app.services.article_workflow_service.WordPressPublishingService", return_value=mock_wp_pub), \
         patch("app.services.article_workflow_service.FacebookPagePublisher") as mock_fb_cls, \
         patch("app.services.article_workflow_service.send_telegram_msg"):

        mock_fb = MagicMock()
        mock_fb.publish_photo_caption.return_value = "fb_post_456"
        mock_fb_cls.return_value = mock_fb

        ArticleWorkflowService.execute("j2", "d2", mode="v2", source_gateway=DummyGateway())

    session.refresh(job)
    session.refresh(draft)

    assert job.status == "success"
    assert job.outputs["wp_post_id"] == 1001
    assert draft.title == "Nuovo Titolo Drammatico"
    assert mock_engine.rewrite.called


@pytest.mark.parametrize("mode", ["v1", "v2"])
def test_original_article_workflow_skips_ai_and_publishes_source(test_db, mode):
    session, TestingSession = test_db
    pipeline = session.get(models.Pipeline, "pipe_1")
    pipeline.language = ""
    pipeline.step_accounts = {"wp": "wp_1"}
    session.commit()

    draft = models.ContentDraft(
        id=f"original-{mode}",
        kind="article_workflow",
        pipeline_id="pipe_1",
        source_url="https://source.test/story",
        state="generating",
    )
    job = models.Job(
        id=f"original-job-{mode}",
        pipeline_id="pipe_1",
        workflow_type="article_workflow",
        input_text="https://source.test/story",
        status="running",
        draft_id=draft.id,
    )
    session.add_all([draft, job])
    session.commit()

    mock_wp_pub = MagicMock()
    mock_pub_res = MagicMock(
        wp_post_id=2000,
        wp_url="https://wp.test/original",
        wp_status="publish",
    )
    mock_wp_pub.publish.return_value = mock_pub_res

    with patch("app.services.article_workflow_service.SessionLocal", TestingSession), \
         patch("app.services.article_workflow_service.create_ai_client") as mock_create_ai, \
         patch("app.services.article_workflow_service.RewriteEngine") as mock_engine, \
         patch("app.services.article_workflow_service.WordPressPublishingService", return_value=mock_wp_pub):
        ArticleWorkflowService.execute(job.id, draft.id, mode=mode, source_gateway=DummyGateway())

    session.refresh(job)
    session.refresh(draft)
    assert job.status == "success"
    assert draft.title == "Source Title"
    assert draft.content == "Source article text with many words."
    assert mock_create_ai.call_count == 0
    assert mock_engine.call_count == 0
    mock_wp_pub.publish.assert_called_once()


def test_article_workflow_cancellation_during_ai(test_db):
    session, TestingSession = test_db

    draft = models.ContentDraft(
        id="d3",
        kind="article_workflow",
        pipeline_id="pipe_1",
        source_url="https://source.test/story",
        state="generating",
    )
    job = models.Job(
        id="j3",
        pipeline_id="pipe_1",
        workflow_type="article_workflow",
        input_text="https://source.test/story",
        status="running",
        draft_id="d3",
    )
    session.add_all([draft, job])
    session.commit()

    mock_ai = MagicMock()
    mock_ai.translation_chunk_size = 6000

    def mock_rewrite(title, content, language, progress=None):
        # Simulate cancellation while rewriting
        with TestingSession() as s:
            j = s.query(models.Job).filter(models.Job.id == "j3").first()
            j.status = "cancelled"
            s.commit()
        if progress:
            progress(1, 2, "rewriting", {"event": "start"})
        return {}

    mock_engine = MagicMock()
    mock_engine.rewrite.side_effect = mock_rewrite

    with patch("app.services.article_workflow_service.SessionLocal", TestingSession), \
         patch("app.services.article_workflow_service.create_ai_client", return_value=mock_ai), \
         patch("app.services.article_workflow_service.RewriteEngine", return_value=mock_engine):

        ArticleWorkflowService.execute("j3", "d3", mode="v2", source_gateway=DummyGateway())

    session.refresh(draft)
    assert draft.state == "generation_failed"
    assert "cancelled" in draft.error.lower()


def test_article_workflow_fails_when_account_missing(test_db):
    session, TestingSession = test_db

    pipe_no_wp = models.Pipeline(
        id="pipe_no_wp",
        name="Pipe No WP",
        type="rewrite",
        language="Italian",
        step_accounts={"ai": "ai_1"},
        is_active=True,
    )
    draft = models.ContentDraft(
        id="d4",
        kind="article_workflow",
        pipeline_id="pipe_no_wp",
        source_url="https://source.test/story",
        state="generating",
    )
    job = models.Job(
        id="j4",
        pipeline_id="pipe_no_wp",
        workflow_type="article_workflow",
        input_text="https://source.test/story",
        status="running",
        draft_id="d4",
    )
    session.add_all([pipe_no_wp, draft, job])
    session.commit()

    with patch("app.services.article_workflow_service.SessionLocal", TestingSession):
        ArticleWorkflowService.execute("j4", "d4", mode="v2", source_gateway=DummyGateway())

    session.refresh(job)
    assert job.status == "failed"
    assert any("wordpress account is unavailable" in str(l.get("detail", "")).lower() for l in (job.logs or []))


def test_article_workflow_sanitizes_errors(test_db):
    session, TestingSession = test_db

    draft = models.ContentDraft(
        id="d5",
        kind="article_workflow",
        pipeline_id="pipe_1",
        source_url="https://source.test/story",
        state="generating",
    )
    job = models.Job(
        id="j5",
        pipeline_id="pipe_1",
        workflow_type="article_workflow",
        input_text="https://source.test/story",
        status="running",
        draft_id="d5",
    )
    session.add_all([draft, job])
    session.commit()

    mock_ai = MagicMock()
    mock_ai.translation_chunk_size = 6000

    def mock_failing_rewrite(*args, **kwargs):
        raise ValueError("Sensitive key sk-1234567890abcdef failed")

    mock_engine = MagicMock()
    mock_engine.rewrite.side_effect = mock_failing_rewrite

    with patch("app.services.article_workflow_service.SessionLocal", TestingSession), \
         patch("app.services.article_workflow_service.create_ai_client", return_value=mock_ai), \
         patch("app.services.article_workflow_service.RewriteEngine", return_value=mock_engine):

        ArticleWorkflowService.execute("j5", "d5", mode="v2", source_gateway=DummyGateway())

    session.refresh(job)
    session.refresh(draft)

    assert job.status == "failed"
    assert draft.state == "generation_failed"
    assert "sk-1234567890abcdef" not in draft.error
    assert "[REDACTED]" in draft.error or "failed" in draft.error
