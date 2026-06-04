from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from infrastructure.db.session import Base, get_db
from apps.api.main import app
import pytest
import os

# Use a separate test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_api_execution.db"

@pytest.fixture(scope="module")
def db_session():
    from sqlalchemy import create_engine
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        if os.path.exists("./test_api_execution.db"):
            os.remove("./test_api_execution.db")

@pytest.fixture(scope="module")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    del app.dependency_overrides[get_db]

def test_run_pipeline_fail_404(client):
    # Test running a non-existent pipeline
    response = client.post("/pipelines/non-existent-id/run", json={"prompt": "Test prompt"})
    assert response.status_code == 404

def test_run_pipeline_success(client, db_session):
    from infrastructure.db import models
    # 1. Create a dummy pipeline
    pipeline = models.Pipeline(
        id="test-pipeline",
        name="Test Pipeline",
        type="standard",
        language="en",
        step_accounts={"ai": "ai-acc"}
    )
    db_session.add(pipeline)
    db_session.commit()

    # 2. Trigger run
    response = client.post("/pipelines/test-pipeline/run", json={"prompt": "Hello world"})
    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "queued"

    # 3. Verify job created in DB
    job_id = data["job_id"]
    job = db_session.query(models.Job).filter(models.Job.id == job_id).first()
    assert job is not None
    assert job.pipeline_id == "test-pipeline"
    assert job.input_text == "Hello world"
    assert job.input_type == "prompt"

def test_list_jobs(client, db_session):
    response = client.get("/jobs")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_get_job_status(client, db_session):
    from infrastructure.db import models
    job = models.Job(id="test-job", pipeline_id="test-pipeline", status="running")
    db_session.add(job)
    db_session.commit()

    response = client.get("/jobs/test-job")
    assert response.status_code == 200
    assert response.json()["id"] == "test-job"
    assert response.json()["status"] == "running"

def test_rerun_failed_job_marks_original(client, db_session, monkeypatch):
    from application import pipeline_service
    from infrastructure.db import models

    pipeline = models.Pipeline(
        id="rerun-pipeline",
        name="Rerun Pipeline",
        type="crawl",
        language="en",
        step_accounts={},
    )
    job = models.Job(
        id="failed-job",
        pipeline_id="rerun-pipeline",
        status="failed",
        input_text="https://example.com/story",
        input_type="url",
        logs=[],
    )
    db_session.add(pipeline)
    db_session.add(job)
    db_session.commit()

    async def fake_start_pipeline_run(pipeline_id, db, prompts_file="prompts.txt", prompt=None):
        assert pipeline_id == "rerun-pipeline"
        assert prompt == "https://example.com/story"
        return "new-rerun-job"

    monkeypatch.setattr(pipeline_service.worker_manager, "start_pipeline_run", fake_start_pipeline_run)

    response = client.post(
        "/pipelines/rerun-pipeline/run",
        json={
            "prompt": "https://example.com/story",
            "rerun_from_job_id": "failed-job",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"job_id": "new-rerun-job", "status": "queued"}

    db_session.refresh(job)
    assert job.rerun_job_id == "new-rerun-job"
    assert job.rerun_at is not None

def test_cancel_running_job(client, monkeypatch):
    from application import job_service

    async def fake_cancel_job(job_id):
        assert job_id == "running-job"
        return {"status": "cancelled"}

    monkeypatch.setattr(job_service.worker_manager, "cancel_job", fake_cancel_job)

    response = client.post("/jobs/running-job/cancel")

    assert response.status_code == 200
    assert response.json() == {"status": "cancelled"}
