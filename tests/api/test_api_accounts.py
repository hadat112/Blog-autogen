import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from infrastructure.db.session import Base, get_db
from apps.api.main import app
import uuid

# Test database setup
TEST_DB_PATH = "./test_api.db"
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

def test_list_accounts_empty():
    response = client.get("/accounts")
    assert response.status_code == 200
    assert response.json() == []

def test_create_account():
    account_data = {
        "name": "Test Account",
        "type": "wp",
        "config": {
            "url": "https://example.com",
            "username": "admin",
            "app_password": "password"
        }
    }
    response = client.post("/accounts", json=account_data)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Account"
    assert "id" in data
    assert data["type"] == "wp"

def test_get_account():
    # First create one
    account_data = {
        "name": "Test Account",
        "type": "wp",
        "config": {"url": "x"}
    }
    create_resp = client.post("/accounts", json=account_data)
    account_id = create_resp.json()["id"]

    response = client.get(f"/accounts/{account_id}")
    assert response.status_code == 200
    assert response.json()["id"] == account_id

def test_update_account():
    # First create one
    account_data = {
        "name": "Old Name",
        "type": "wp",
        "config": {"url": "x"}
    }
    create_resp = client.post("/accounts", json=account_data)
    account_id = create_resp.json()["id"]

    update_data = {
        "name": "New Name",
        "type": "wp",
        "config": {"url": "y"}
    }
    response = client.put(f"/accounts/{account_id}", json=update_data)
    assert response.status_code == 200
    assert response.json()["name"] == "New Name"

def test_delete_account():
    # First create one
    account_data = {
        "name": "Delete Me",
        "type": "wp",
        "config": {"url": "x"}
    }
    create_resp = client.post("/accounts", json=account_data)
    account_id = create_resp.json()["id"]

    response = client.delete(f"/accounts/{account_id}")
    assert response.status_code == 200

    # Verify it's gone
    get_resp = client.get(f"/accounts/{account_id}")
    assert get_resp.status_code == 404

def test_verify_account_wp_fail(mocker):
    # Create a WP account
    account_data = {
        "name": "WP Test",
        "type": "wp",
        "config": {
            "url": "https://test.wp",
            "username": "user",
            "app_password": "pass"
        }
    }
    create_resp = client.post("/accounts", json=account_data)
    account_id = create_resp.json()["id"]

    # Mock requests.get
    mock_get = mocker.patch("requests.get")
    mock_get.return_value.status_code = 401
    mock_get.return_value.raise_for_status.side_effect = Exception("Unauthorized")

    response = client.post("/accounts/test", json={"id": account_id})
    assert response.status_code == 400
    assert "detail" in response.json()

def test_verify_account_wp_success(mocker):
    # Create a WP account
    account_data = {
        "name": "WP Test",
        "type": "wp",
        "config": {
            "url": "https://test.wp",
            "username": "user",
            "app_password": "pass"
        }
    }
    create_resp = client.post("/accounts", json=account_data)
    account_id = create_resp.json()["id"]

    # Mock requests.get
    mock_get = mocker.patch("requests.get")
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {"id": 123}

    response = client.post("/accounts/test", json={"id": account_id})
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "message": "Credentials verified"}

def test_verify_account_fb_success(mocker):
    # Create a FB account
    account_data = {
        "name": "FB Test",
        "type": "fb",
        "config": {
            "page_id": "12345",
            "access_token": "token"
        }
    }
    create_resp = client.post("/accounts", json=account_data)
    account_id = create_resp.json()["id"]

    # Mock requests.get
    mock_get = mocker.patch("requests.get")
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {"id": "12345"}

    response = client.post("/accounts/test", json={"id": account_id})
    assert response.status_code == 200

def test_verify_account_ai_success(mocker):
    # Create an AI account
    account_data = {
        "name": "AI Test",
        "type": "ai",
        "config": {
            "api_key": "key",
            "base_url": "http://ai.test/v1"
        }
    }
    create_resp = client.post("/accounts", json=account_data)
    account_id = create_resp.json()["id"]

    # Mock requests.get
    mock_get = mocker.patch("requests.get")
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {"data": []}

    response = client.post("/accounts/test", json={"id": account_id})
    assert response.status_code == 200


def test_fetch_ai_models(mocker):
    mock_get = mocker.patch("requests.get")
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {
        "object": "list",
        "data": [
            {
                "id": "gemini-cli/gemini-2.0-flash",
                "name": "Gemini 2.0 Flash",
                "owned_by": "gemini-cli",
                "context_length": 1048576,
            },
            {
                "id": "oc/deepseek-v4-flash-free",
                "name": "DeepSeek V4 Flash Free",
                "owned_by": "opencode",
                "context_length": 1000000,
            },
        ],
    }

    response = client.post(
        "/accounts/ai-models",
        json={
            "base_url": "http://localhost:20128/v1",
            "api_key": "test_key",
        },
    )

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": "gemini-cli/gemini-2.0-flash",
            "name": "Gemini 2.0 Flash",
            "owned_by": "gemini-cli",
            "context_length": 1048576,
            "type": None,
        },
        {
            "id": "oc/deepseek-v4-flash-free",
            "name": "DeepSeek V4 Flash Free",
            "owned_by": "opencode",
            "context_length": 1000000,
            "type": None,
        },
    ]
    mock_get.assert_called_once()
    args, kwargs = mock_get.call_args
    assert args[0] == "http://localhost:20128/v1/models"
    assert kwargs["headers"] == {
        "ngrok-skip-browser-warning": "true",
        "Authorization": "Bearer test_key",
    }
