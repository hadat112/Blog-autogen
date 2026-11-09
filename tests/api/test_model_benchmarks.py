import pytest
import requests
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.main import app
from app.db import models
from app.db.session import Base, get_db


@pytest.fixture
def api(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'api.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)

    def override_db():
        with sessions() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    monkeypatch.setattr("app.api.routes.model_benchmarks.fetch_ai_models", lambda config: [{"id": f"m{i}", "name": f"Model {i}"} for i in range(1, 7)])
    scheduled = []
    monkeypatch.setattr("app.api.routes.model_benchmarks.workflow_runner.start", lambda job_id, operation: scheduled.append(job_id))
    with sessions() as db:
        db.add(models.Account(id="ai", name="AI", type="ai", config={"base_url": "http://local/v1", "api_key": "secret"}))
        db.add(models.Account(id="wp", name="WP", type="wp", config={}))
        db.commit()
    yield TestClient(app), sessions, scheduled
    app.dependency_overrides.clear()
    engine.dispose()


def test_sample_and_model_discovery(api):
    client, _, _ = api
    sample = client.get("/model-benchmarks/sample")
    assert sample.status_code == 200
    assert sample.json()["id"] == "ceo-ceremony-parts-1-2-v1"
    assert sample.json()["target_language"] == "Polish"
    assert sample.json()["text"].startswith("PART 1\nAt my husband’s CEO ceremony")
    assert sample.json()["text"].endswith("“Security should remove her.”")
    models_response = client.get("/model-benchmarks/accounts/ai/models")
    assert models_response.status_code == 200
    assert [item["id"] for item in models_response.json()] == [f"m{i}" for i in range(1, 7)]
    assert client.get("/model-benchmarks/accounts/wp/models").status_code == 404


@pytest.mark.parametrize("account_id,model_ids,status", [
    ("missing", ["m1", "m2"], 404), ("wp", ["m1", "m2"], 404),
    ("ai", ["m1"], 422), ("ai", ["m1"] * 6, 422),
    ("ai", ["m1", "m1"], 400), ("ai", ["m1", " "], 400),
    ("ai", ["m1", "unknown"], 400),
])
def test_rejects_invalid_selection_before_job(api, account_id, model_ids, status):
    client, sessions, scheduled = api
    response = client.post("/model-benchmarks", json={"account_id": account_id, "model_ids": model_ids})
    assert response.status_code == status
    with sessions() as db:
        assert db.query(models.Job).count() == 0
    assert scheduled == []


def test_creates_queued_job_with_metadata_only(api):
    client, sessions, scheduled = api
    response = client.post("/model-benchmarks", json={"account_id": "ai", "model_ids": ["m3", "m1"]})
    assert response.status_code == 200
    job_id = response.json()["job_id"]
    assert scheduled == [job_id]
    with sessions() as db:
        job = db.get(models.Job, job_id)
        assert job.status == "queued"
        assert job.workflow_type == "model_benchmark"
        assert job.outputs["model_ids"] == ["m3", "m1"]
        assert [row["status"] for row in job.outputs["results"]] == ["waiting", "waiting"]
        assert "secret" not in str(job.outputs)
        assert job.input_text is None


@pytest.mark.parametrize("failure,expected", [
    (requests.Timeout("secret"), "Timed out while fetching models from AI account"),
    (requests.ConnectionError("secret"), "Could not connect to AI account Base URL"),
    (requests.HTTPError("secret", response=type("Response", (), {"status_code": 401})()), "AI account returned HTTP 401 while fetching models"),
])
def test_model_discovery_reports_safe_actionable_error(api, monkeypatch, failure, expected):
    client, _, _ = api
    def fail(config):
        raise failure
    monkeypatch.setattr("app.api.routes.model_benchmarks.fetch_ai_models", fail)
    response = client.get("/model-benchmarks/accounts/ai/models")
    assert response.status_code == 502
    assert response.json()["detail"] == expected
    assert "secret" not in str(response.json())
