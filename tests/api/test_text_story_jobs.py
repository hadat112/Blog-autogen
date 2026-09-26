from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.main import app
from app.db import models
from app.db.session import Base, get_db
from app.services.wordpress_publishing_service import WordPressPublishingService


@pytest.fixture
def setup(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'api.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)

    def override():
        with sessions() as db:
            yield db

    app.dependency_overrides[get_db] = override
    with sessions() as db:
        db.add_all([
            models.Account(id="ai", name="AI", type="ai", config={"api_key": "secret", "text_model": "m"}),
            models.Account(id="wp", name="WP", type="wp", config={}),
            models.Pipeline(id="pipe", name="Pipe", type="rewrite", language="Italian",
                            step_accounts={"ai": "ai", "wp": "wp"}, is_active=True),
        ])
        db.commit()
    yield TestClient(app), sessions
    app.dependency_overrides.pop(get_db, None)
    engine.dispose()


def test_start_persists_source_before_scheduling_and_retry_reuses_draft(setup):
    client, sessions = setup
    with patch("app.api.routes.text_story_jobs.workflow_runner.start") as start:
        response = client.post("/text-story-jobs", json={"pipeline_id": "pipe", "source_text": "Original story"})
        assert response.status_code == 200, response.text
        data = response.json()
        with sessions() as db:
            artifact = db.query(models.TextStoryComposition).filter_by(draft_id=data["draft_id"]).one()
            assert artifact.source_text == "Original story"
            assert db.get(models.Job, data["job_id"]).input_text is None
            db.get(models.Job, data["job_id"]).status = "failed"
            db.get(models.ContentDraft, data["draft_id"]).state = "generation_failed"
            db.commit()
        assert start.call_count == 1
        artifacts = client.get(f"/text-story-jobs/{data['draft_id']}/artifacts")
        assert artifacts.status_code == 200
        assert artifacts.json()["source_text"] == "Original story"
        assert "secret" not in artifacts.text
        retry = client.post(f"/text-story-jobs/{data['draft_id']}/retry")
        assert retry.status_code == 200, retry.text
        assert retry.json()["draft_id"] == data["draft_id"]
        assert start.call_count == 2


def test_missing_account_and_language_rejected(setup):
    client, sessions = setup
    with sessions() as db:
        db.get(models.Pipeline, "pipe").language = ""
        db.commit()
    assert client.post("/text-story-jobs", json={"pipeline_id": "pipe", "source_text": "Story"}).status_code == 400


def test_retry_active_job_conflicts(setup):
    client, _ = setup
    with patch("app.api.routes.text_story_jobs.workflow_runner.start"):
        created = client.post("/text-story-jobs", json={"pipeline_id": "pipe", "source_text": "Story"}).json()
        assert client.post(f"/text-story-jobs/{created['draft_id']}/retry").status_code == 409


def test_reviewed_text_story_uses_existing_wordpress_route_without_artifacts(setup, monkeypatch):
    client, sessions = setup
    posts = []

    class Gateway:
        def __init__(self, config):
            pass

        def create_post(self, title, content, status, category_id, media_id):
            posts.append((title, content, status, category_id, media_id))
            return {"id": "42", "link": "https://wp.test/story", "status": status}

    monkeypatch.setattr("app.api.routes.content_drafts.WordPressPublishingService",
                        lambda db: WordPressPublishingService(db, Gateway))
    with sessions() as db:
        db.add(models.ContentDraft(id="ready", kind="text_story", pipeline_id="pipe", state="ready_for_review",
                                   title="The Door", content="Opening.\n\nEnding.", wp_status="draft"))
        db.add(models.TextStoryComposition(draft_id="ready", source_text="SECRET SOURCE", image_prompt="SECRET IMAGE",
                                           prompt_version="text-story-v1", stage_status={}))
        db.add(models.ContentDraft(id="pending", kind="text_story", pipeline_id="pipe", state="generating",
                                   title="Incomplete", content="Opening.", wp_status="draft"))
        db.commit()
    pending = client.post("/content-drafts/pending/publish", json={"confirmed": True})
    assert pending.status_code == 409
    assert not posts
    response = client.post("/content-drafts/ready/publish", json={"confirmed": True})
    assert response.status_code == 200, response.text
    assert response.json()["kind"] == "text_story"
    assert posts[0][1] == "<p>Opening.</p>\n<p>Ending.</p>"
    assert "SECRET SOURCE" not in posts[0][1] and "SECRET IMAGE" not in posts[0][1]
