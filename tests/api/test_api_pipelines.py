import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from infrastructure.db.session import Base, get_db
from apps.api.main import app

# Test database setup
TEST_DB_PATH = "./test_api_pipelines.db"
SQLALCHEMY_DATABASE_URL = f"sqlite:///{TEST_DB_PATH}"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

@pytest.fixture(autouse=True)
def setup_db():
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)
    yield
    app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

client = TestClient(app)

def test_list_pipelines_empty():
    response = client.get("/pipelines")
    assert response.status_code == 200
    assert response.json() == []

def test_create_pipeline():
    pipeline_data = {
        "name": "Test Pipeline",
        "type": "story",
        "language": "Ukrainian",
        "step_accounts": {
            "ai": "ai_account_id",
            "wp": "wp_account_id"
        },
        "settings": {"wp_category_id": "12"},
        "is_active": True
    }
    response = client.post("/pipelines", json=pipeline_data)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Pipeline"
    assert data["language"] == "Ukrainian"
    assert "id" in data
    assert data["step_accounts"]["ai"] == "ai_account_id"
    assert data["settings"]["wp_category_id"] == "12"
    assert data["wp_category_id"] == "12"

def test_get_pipeline():
    # First create one
    pipeline_data = {
        "name": "Get Pipeline",
        "type": "story",
        "language": "Ukrainian",
        "step_accounts": {"ai": "x"}
    }
    create_resp = client.post("/pipelines", json=pipeline_data)
    pipeline_id = create_resp.json()["id"]

    response = client.get(f"/pipelines/{pipeline_id}")
    assert response.status_code == 200
    assert response.json()["id"] == pipeline_id

def test_update_pipeline():
    # First create one
    pipeline_data = {
        "name": "Old Name",
        "type": "story",
        "language": "Ukrainian",
        "step_accounts": {"ai": "x"}
    }
    create_resp = client.post("/pipelines", json=pipeline_data)
    pipeline_id = create_resp.json()["id"]

    update_data = {
        "name": "New Name",
        "type": "story",
        "language": "English",
        "step_accounts": {"ai": "y"},
        "settings": {"wp_category_id": "34"},
        "is_active": False
    }
    response = client.put(f"/pipelines/{pipeline_id}", json=update_data)
    assert response.status_code == 200
    assert response.json()["name"] == "New Name"
    assert response.json()["language"] == "English"
    assert response.json()["settings"]["wp_category_id"] == "34"
    assert response.json()["wp_category_id"] == "34"
    assert response.json()["is_active"] is False

def test_create_pipeline_accepts_top_level_wp_category_id():
    pipeline_data = {
        "name": "Top Level Category",
        "type": "story",
        "language": "Ukrainian",
        "step_accounts": {"wp": "wp_account_id"},
        "wp_category_id": "99"
    }
    response = client.post("/pipelines", json=pipeline_data)
    assert response.status_code == 200
    data = response.json()
    assert data["wp_category_id"] == "99"
    assert data["settings"]["wp_category_id"] == "99"

def test_delete_pipeline():
    # First create one
    pipeline_data = {
        "name": "Delete Me",
        "type": "story",
        "language": "Ukrainian",
        "step_accounts": {"ai": "x"}
    }
    create_resp = client.post("/pipelines", json=pipeline_data)
    pipeline_id = create_resp.json()["id"]

    response = client.delete(f"/pipelines/{pipeline_id}")
    assert response.status_code == 200

    # Verify it's gone
    get_resp = client.get(f"/pipelines/{pipeline_id}")
    assert get_resp.status_code == 404


def test_create_pipeline_preserves_custom_language_text():
    response = client.post(
        "/pipelines",
        json={
            "name": "Custom Language",
            "type": "story",
            "language": "abc",
            "step_accounts": {},
        },
    )

    assert response.status_code == 200
    assert response.json()["language"] == "abc"


def test_create_crawl_pipeline_accepts_empty_language_for_repost_original():
    response = client.post(
        "/pipelines",
        json={
            "name": "Repost Original",
            "type": "crawl",
            "language": "",
            "step_accounts": {},
        },
    )

    assert response.status_code == 200
    assert response.json()["language"] == ""


def test_create_story_pipeline_rejects_empty_language():
    response = client.post(
        "/pipelines",
        json={
            "name": "Story Needs Language",
            "type": "story",
            "language": "",
            "step_accounts": {},
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Language is required"


def test_existing_pipeline_can_keep_disabled_language():
    create_response = client.post(
        "/pipelines",
        json={
            "name": "Dutch Pipeline",
            "type": "story",
            "language": "Dutch",
            "step_accounts": {},
        },
    )
    pipeline = create_response.json()
    dutch = next(
        language for language in client.get("/languages").json()
        if language["code"] == "nl"
    )
    client.put(
        "/languages/nl",
        json={
            "display_name": dutch["display_name"],
            "is_active": False,
        },
    )

    response = client.put(
        f"/pipelines/{pipeline['id']}",
        json={
            "name": "Dutch Pipeline Updated",
            "type": "story",
            "language": "Dutch",
            "step_accounts": {},
        },
    )

    assert response.status_code == 200
    assert response.json()["language"] == "Dutch"
