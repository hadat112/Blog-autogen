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
