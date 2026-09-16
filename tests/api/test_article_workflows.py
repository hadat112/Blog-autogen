import os
from datetime import datetime
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.main import app
from app.db import models
from app.db.session import Base, get_db

TEST_DB_PATH = "./test_article_workflows_api.db"
engine = create_engine(f"sqlite:///{TEST_DB_PATH}", connect_args={"check_same_thread": False})
TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def override_get_db():
    with TestingSession() as db:
        yield db


@pytest.fixture(autouse=True)
def setup_db():
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(engine)
    with TestingSession() as db:
        db.add_all([
            models.Account(id="ai_acc", name="AI", type="ai", config={"api_key": "x", "text_model": "m"}),
            models.Account(id="wp_acc", name="WP", type="wp", config={"url": "https://wp.test", "username": "u", "password": "p"}),
            models.Pipeline(
                id="pipe_ok",
                name="Pipe Valid",
                type="rewrite",
                language="Italian",
                step_accounts={"ai": "ai_acc", "wp": "wp_acc"},
                is_active=True,
            ),
            models.Pipeline(
                id="pipe_no_wp",
                name="Pipe Missing WP",
                type="rewrite",
                language="Italian",
                step_accounts={"ai": "ai_acc"},
                is_active=True,
            ),
        ])
        db.commit()
    yield
    app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(engine)
    engine.dispose()
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)


client = TestClient(app)


def test_start_article_workflow_v1_and_v2():
    with patch("app.services.article_workflow_service.ArticleWorkflowService.execute") as mock_exec:
        # V1
        res1 = client.post(
            "/article-workflows/run",
            json={"pipeline_id": "pipe_ok", "source_url": "https://source.test/story-1", "mode": "v1"},
        )
        assert res1.status_code == 200, res1.text
        data1 = res1.json()
        assert data1["status"] == "queued"
        assert "job_id" in data1
        assert "draft_id" in data1

        # V2
        res2 = client.post(
            "/article-workflows/run",
            json={"pipeline_id": "pipe_ok", "source_url": "https://source.test/story-2", "mode": "v2"},
        )
        assert res2.status_code == 200, res2.text
        data2 = res2.json()
        assert data2["status"] == "queued"


def test_start_article_workflow_validation_errors():
    # Missing WP account
    res = client.post(
        "/article-workflows/run",
        json={"pipeline_id": "pipe_no_wp", "source_url": "https://source.test/story", "mode": "v1"},
    )
    assert res.status_code == 400
    assert "wordpress account" in res.json()["detail"].lower()

    # Invalid URL
    res = client.post(
        "/article-workflows/run",
        json={"pipeline_id": "pipe_ok", "source_url": "not-a-valid-url", "mode": "v1"},
    )
    assert res.status_code == 400


def test_article_workflow_retry():
    with TestingSession() as db:
        failed_job = models.Job(
            id="failed_job_1",
            pipeline_id="pipe_ok",
            workflow_type="article_v2",
            input_text="https://source.test/story-failed",
            status="failed",
        )
        db.add(failed_job)
        db.commit()

    with patch("app.services.article_workflow_service.ArticleWorkflowService.execute"):
        res = client.post("/article-workflows/failed_job_1/retry")
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["status"] == "queued"
        assert data["job_id"] != "failed_job_1"

        with TestingSession() as db:
            old = db.query(models.Job).filter(models.Job.id == "failed_job_1").first()
            assert old.rerun_job_id == data["job_id"]


def test_article_workflow_draft_can_be_published_again():
    with TestingSession() as db:
        draft = models.ContentDraft(
            id="publishable_article_v2",
            kind="article_v2",
            pipeline_id="pipe_ok",
            title="Ready article",
            content="Article body",
            state="ready_for_review",
            wp_status="publish",
        )
        db.add(draft)
        db.commit()

    with patch("app.api.routes.content_drafts.WordPressPublishingService.publish") as publish:
        publish.return_value = models.ContentDraft(
            id="publishable_article_v2",
            kind="article_v2",
            pipeline_id="pipe_ok",
            title="Ready article",
            content="Article body",
            content_format="plain",
            state="wordpress_created",
            wp_status="publish",
            version=2,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        res = client.post("/content-drafts/publishable_article_v2/publish", json={"confirmed": True})

    assert res.status_code == 200, res.text
