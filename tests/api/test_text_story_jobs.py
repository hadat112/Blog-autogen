from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.main import app
from app.db import models
from app.db.session import Base, get_db


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
