import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.main import app
from app.db import models
from app.db.session import Base, get_db


TEST_DB_PATH = "./test_api_workflows.db"
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
            models.Account(id="ai1", name="AI", type="ai", config={"api_key": "x", "text_model": "m", "base_url": "https://ai.test/v1"}),
            models.Account(id="wp1", name="WP", type="wp", config={"url": "https://wp.test", "username": "u", "password": "p"}),
        ])
        db.commit()
    yield
    app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(engine)
    engine.dispose()
    if os.path.exists(TEST_DB_PATH): os.remove(TEST_DB_PATH)


client = TestClient(app)


def create_profile(profile_type="wp_publish"):
    payload = {
        "name": "Workflow",
        "type": profile_type,
        "language": "" if profile_type == "wp_publish" else "Italian",
        "step_accounts": {"wp": "wp1", **({"ai": "ai1"} if profile_type != "wp_publish" else {})},
        "settings": {},
    }
    response = client.post("/workflow-profiles", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def test_workflow_profiles_are_hidden_from_legacy_pipeline_api():
    profile = create_profile("rewrite")
    assert client.get("/pipelines").json() == []
    assert client.get(f"/pipelines/{profile['id']}").status_code == 404
    assert client.post("/pipelines", json={**profile, "name": "Wrong API"}).status_code == 400
    assert client.get("/workflow-profiles", params={"type": "rewrite"}).json()[0]["id"] == profile["id"]


def test_profile_validates_account_types_and_prevents_type_change():
    response = client.post("/workflow-profiles", json={"name": "Bad", "type": "rewrite", "language": "Italian", "step_accounts": {"ai": "wp1", "wp": "wp1"}})
    assert response.status_code == 400
    profile = create_profile("rewrite")
    response = client.put(f"/workflow-profiles/{profile['id']}", json={**profile, "type": "generate_story"})
    assert response.status_code == 400


def test_manual_draft_is_persistent_and_uses_optimistic_version():
    profile = create_profile()
    response = client.post("/content-drafts", json={"kind": "manual", "pipeline_id": profile["id"], "title": "Draft", "content": "Body", "content_format": "plain", "wp_status": "draft"})
    assert response.status_code == 200, response.text
    draft = response.json()
    update = {**draft, "title": "Updated", "version": draft["version"]}
    response = client.put(f"/content-drafts/{draft['id']}", json=update)
    assert response.status_code == 200
    assert response.json()["version"] == draft["version"] + 1
    assert client.put(f"/content-drafts/{draft['id']}", json=update).status_code == 409


def test_manual_draft_rejects_non_publisher_profile():
    profile = create_profile("rewrite")
    response = client.post("/content-drafts", json={"kind": "manual", "pipeline_id": profile["id"], "title": "Draft", "content": "Body"})
    assert response.status_code == 400


def test_theme_rules_patterns_and_collection_sources():
    profile = create_profile("rewrite")
    rule = client.post("/theme-rules", json={"tag": "Family", "keywords": ["Mother", "mother", " Father "], "is_active": True})
    assert rule.status_code == 200
    assert rule.json()["keywords"] == ["mother", "father"]
    source = client.get("/pattern-collection-sources").json()[0]
    assert source["collect_patterns"] is False
    assert source["can_analyze"] is True
    assert client.put(f"/pattern-collection-sources/{profile['id']}", json={"collect_patterns": True}).json()["collect_patterns"] is True
    with TestingSession() as db:
        db.add(models.Article(source_url="https://source.test/a", original_title="A", theme_tags=["family"], word_count=12, analysis_status="failed"))
        db.commit()
    summary = client.get("/patterns/summary").json()
    assert summary == {"total": 1, "completed": 0, "recoverable": 1, "distinct_themes": 1}
    assert client.get("/patterns", params={"q": "source.test"}).json()["total"] == 1
    assert client.delete(f"/theme-rules/{rule.json()['id']}").status_code == 200


def test_pattern_sources_report_ai_eligibility_and_retry_revalidates_it():
    valid = create_profile("rewrite")
    with TestingSession() as db:
        db.add_all([
            models.Pipeline(id="missing-ai", name="Missing AI", type="crawl", language="English", step_accounts={}),
            models.Pipeline(id="inactive", name="Inactive", type="crawl", language="English", step_accounts={"ai": "ai1"}, is_active=False),
            models.Article(id="article", source_url="https://source.test/retry", original_title="Retry", analysis_status="failed"),
        ])
        db.commit()

    sources = {item["pipeline_id"]: item for item in client.get("/pattern-collection-sources").json()}
    assert sources[valid["id"]]["can_analyze"] is True
    assert sources["missing-ai"]["can_analyze"] is False
    assert sources["inactive"]["can_analyze"] is False
    assert client.post("/patterns/article/retry-analysis", params={"pipeline_id": "missing-ai"}).status_code == 400
    assert client.post("/patterns/article/retry-analysis", params={"pipeline_id": "inactive"}).status_code == 400


def test_job_api_exposes_structured_capabilities_and_legacy_url_fallback():
    with TestingSession() as db:
        pipeline = models.Pipeline(name="Legacy", type="story", language="English", step_accounts={})
        db.add(pipeline); db.commit(); db.refresh(pipeline)
        db.add(models.Job(pipeline_id=pipeline.id, status="success", progress=100, logs=[{"detail": "[x] WP Success: https://wp.test/post"}], outputs={}))
        db.commit()
    job = client.get("/jobs").json()[0]
    assert job["workflow_type"] == "legacy"
    assert job["outputs"]["wp_url"] == "https://wp.test/post"
    assert job["capabilities"]["can_copy_link"] is True


def test_exact_theme_filter_does_not_match_longer_tag():
    with TestingSession() as db:
        db.add_all([
            models.Article(source_url="https://source.test/a", original_title="A", theme_tags=["family"], word_count=1),
            models.Article(source_url="https://source.test/b", original_title="B", theme_tags=["family-drama"], word_count=1),
        ]); db.commit()
    response = client.get("/patterns", params={"theme": "family"})
    assert response.status_code == 200
    assert [item["original_title"] for item in response.json()["items"]] == ["A"]


def test_start_rewrite_and_generation_create_independent_job_and_draft(monkeypatch):
    started = []
    monkeypatch.setattr("app.api.routes.rewrite_jobs.workflow_runner.start", lambda job_id, operation: started.append(job_id))
    monkeypatch.setattr("app.api.routes.generation_jobs.workflow_runner.start", lambda job_id, operation: started.append(job_id))
    rewrite = create_profile("rewrite")
    generated = create_profile("generate_story")
    rewrite_response = client.post("/rewrite-jobs", json={"profile_id": rewrite["id"], "source_url": "https://source.test/story"})
    generation_response = client.post("/generation-jobs", json={"profile_id": generated["id"]})
    assert rewrite_response.status_code == generation_response.status_code == 200
    assert rewrite_response.json()["draft_id"] != generation_response.json()["draft_id"]
    assert len(started) == 2


def test_rewrite_rejects_source_url_with_embedded_credentials():
    profile = create_profile("rewrite")
    response = client.post(
        "/rewrite-jobs",
        json={"profile_id": profile["id"], "source_url": "https://user:pass@source.test/story"},
    )
    assert response.status_code == 400
    assert "credentials" in response.json()["detail"]


def test_account_used_by_workflow_profile_cannot_be_deleted():
    create_profile("wp_publish")
    response = client.delete("/accounts/wp1")
    assert response.status_code == 409
    assert "used by" in response.json()["detail"]


def test_uploaded_image_rejects_spoofed_mime_and_removes_partial_file():
    profile = create_profile("wp_publish")
    draft = client.post("/content-drafts", json={"kind": "manual", "pipeline_id": profile["id"], "title": "Draft", "content": "Body"}).json()
    response = client.post(
        f"/content-drafts/{draft['id']}/image",
        files={"image": ("fake.png", b"not really png", "image/png")},
    )
    assert response.status_code == 400
    assert "does not match" in response.json()["detail"]


def test_valid_uploaded_image_is_unique_and_cleaned_when_draft_deleted():
    profile = create_profile("wp_publish")
    draft = client.post("/content-drafts", json={"kind": "manual", "pipeline_id": profile["id"], "title": "Draft", "content": "Body"}).json()
    response = client.post(
        f"/content-drafts/{draft['id']}/image",
        files={"image": ("image.png", b"\x89PNG\r\n\x1a\ncontent", "image/png")},
    )
    assert response.status_code == 200, response.text
    from pathlib import Path
    uploaded = Path(response.json()["image_source"])
    assert uploaded.is_file() and uploaded.name != "image.png" and uploaded.suffix == ".png"
    assert client.delete(f"/content-drafts/{draft['id']}").status_code == 200
    assert not uploaded.exists()
