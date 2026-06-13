import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from apps.api.main import app
from infrastructure.db.session import Base, get_db


TEST_DB_PATH = "./test_api_languages.db"
engine = create_engine(
    f"sqlite:///{TEST_DB_PATH}",
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
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


def test_list_languages_seeds_defaults():
    response = client.get("/languages")

    assert response.status_code == 200
    languages = {language["code"]: language for language in response.json()}
    assert len(languages) == 11
    assert languages["nl"]["display_name"] == "Dutch"
    assert languages["cs"]["display_name"] == "Czech"
    assert "prompt_name" not in languages["nl"]


def test_create_edit_and_disable_language():
    create_response = client.post(
        "/languages",
        json={
            "code": "de",
            "display_name": "German",
            "is_active": True,
        },
    )
    assert create_response.status_code == 200
    assert create_response.json()["code"] == "de"

    update_response = client.put(
        "/languages/de",
        json={
            "display_name": "Deutsch",
            "is_active": False,
        },
    )
    assert update_response.status_code == 200
    assert update_response.json()["display_name"] == "Deutsch"
    assert update_response.json()["is_active"] is False


def test_create_language_rejects_duplicate_code():
    client.get("/languages")

    response = client.post(
        "/languages",
        json={
            "code": "NL",
            "display_name": "Duplicate Dutch",
            "is_active": True,
        },
    )

    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]
