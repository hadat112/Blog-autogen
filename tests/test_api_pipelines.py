import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from core.db import Base, get_db
from api.main import app

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_api_pipelines.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

client = TestClient(app)

def test_list_pipelines_empty():
    response = client.get("/pipelines")
    assert response.status_code == 200
    assert response.json() == []

def test_create_pipeline():
    pipeline_data = {
        "name": "Test Pipeline",
        "type": "story",
        "language": "uk",
        "step_accounts": {
            "ai": "ai_account_id",
            "wp": "wp_account_id"
        },
        "schedule": "0 10 * * *",
        "is_active": True
    }
    response = client.post("/pipelines", json=pipeline_data)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Pipeline"
    assert "id" in data
    assert data["step_accounts"]["ai"] == "ai_account_id"

def test_get_pipeline():
    # First create one
    pipeline_data = {
        "name": "Get Pipeline",
        "type": "story",
        "language": "uk",
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
        "language": "uk",
        "step_accounts": {"ai": "x"}
    }
    create_resp = client.post("/pipelines", json=pipeline_data)
    pipeline_id = create_resp.json()["id"]

    update_data = {
        "name": "New Name",
        "type": "story",
        "language": "en",
        "step_accounts": {"ai": "y"},
        "schedule": "0 12 * * *",
        "is_active": False
    }
    response = client.put(f"/pipelines/{pipeline_id}", json=update_data)
    assert response.status_code == 200
    assert response.json()["name"] == "New Name"
    assert response.json()["language"] == "en"
    assert response.json()["is_active"] is False

def test_delete_pipeline():
    # First create one
    pipeline_data = {
        "name": "Delete Me",
        "type": "story",
        "language": "uk",
        "step_accounts": {"ai": "x"}
    }
    create_resp = client.post("/pipelines", json=pipeline_data)
    pipeline_id = create_resp.json()["id"]

    response = client.delete(f"/pipelines/{pipeline_id}")
    assert response.status_code == 200

    # Verify it's gone
    get_resp = client.get(f"/pipelines/{pipeline_id}")
    assert get_resp.status_code == 404
