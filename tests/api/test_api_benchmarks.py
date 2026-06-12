import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from apps.api.main import app
from infrastructure.db.models import Account
from infrastructure.db.session import Base, get_db


TEST_DB_PATH = "./test_api_benchmarks.db"
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


def _create_ai_accounts():
    with TestingSessionLocal() as db:
        first = Account(
            name="Model A",
            type="ai",
            config={
                "api_key": "a",
                "base_url": "https://ai-a.test/v1",
                "text_model": "model-a",
            },
        )
        second = Account(
            name="Model B",
            type="ai",
            config={
                "api_key": "b",
                "base_url": "https://ai-b.test/v1",
                "text_model": "model-b",
            },
        )
        db.add_all([first, second])
        db.commit()
        db.refresh(first)
        db.refresh(second)
        return first.id, second.id


def test_create_benchmark_requires_two_accounts():
    response = client.post(
        "/translation-benchmarks",
        json={
            "account_ids": ["only-one"],
            "target_language": "Italian",
            "suite": "standard",
        },
    )

    assert response.status_code == 400
    assert "at least two" in response.json()["detail"]


def test_create_benchmark_rejects_duplicate_account():
    first_id, _ = _create_ai_accounts()

    response = client.post(
        "/translation-benchmarks",
        json={
            "account_ids": [first_id, first_id],
            "target_language": "Italian",
            "suite": "standard",
        },
    )

    assert response.status_code == 400
    assert "at least two" in response.json()["detail"]


def test_create_and_rate_benchmark(mocker):
    first_id, second_id = _create_ai_accounts()
    execute = mocker.patch(
        "apps.api.routes.benchmarks.execute_benchmark_run",
        return_value=None,
    )

    response = client.post(
        "/translation-benchmarks",
        json={
            "account_ids": [first_id, second_id],
            "target_language": "Italian",
            "suite": "standard",
        },
    )

    assert response.status_code == 200
    run = response.json()
    assert run["status"] == "queued"
    assert run["selected_account_ids"] == [first_id, second_id]

    rating_response = client.post(
        f"/translation-benchmarks/{run['id']}/ratings",
        json={"account_id": first_id, "score": 5},
    )

    assert rating_response.status_code == 200
    assert rating_response.json()["manual_ratings"][first_id]["score"] == 5
    execute.assert_called_once_with(run["id"])


def test_custom_benchmark_requires_content(mocker):
    first_id, second_id = _create_ai_accounts()
    mocker.patch("apps.api.routes.benchmarks.execute_benchmark_run")

    response = client.post(
        "/translation-benchmarks",
        json={
            "account_ids": [first_id, second_id],
            "target_language": "Polish",
            "suite": "custom",
            "custom_content": " ",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Custom content is required"
