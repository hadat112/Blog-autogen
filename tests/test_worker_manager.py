import pytest
import asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from core.db import Base
from core.models import Pipeline, Account, Job
from core.worker_manager import WorkerManager

# Use in-memory SQLite for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)

@pytest.mark.anyio
async def test_worker_manager_pipeline_run(db, mocker):
    # Mock SessionLocal in core.worker_manager to use our test DB
    mocker.patch("core.worker_manager.SessionLocal", TestingSessionLocal)
    
    # 1. Setup Data
    account = Account(name="Test AI", type="ai", config={"api_key": "test"})
    db.add(account)
    db.commit()
    
    pipeline = Pipeline(
        name="Test Pipeline",
        type="story",
        step_accounts={"ai": account.id}
    )
    db.add(pipeline)
    db.commit()
    
    # Mock Orchestrator
    mock_orchestrator = mocker.patch("core.worker_manager.Orchestrator")
    mock_instance = mock_orchestrator.return_value
    mock_instance.run.return_value = [{"status": "success"}]
    
    # 2. Run WorkerManager
    wm = WorkerManager()
    job_id = await wm.start_pipeline_run(pipeline.id, db)

    # 3. Verify Job creation and status
    job = db.query(Job).filter(Job.id == job_id).first()
    assert job is not None
    assert job.status in ["success", "running"]

    # Let's wait a bit longer for the background task to finish
    for _ in range(20): # increased to 2 seconds
        db.refresh(job)
        if job.status == "success":
            break
        await asyncio.sleep(0.1)

    assert job.status == "success"
    assert job.progress == 100

    assert mock_instance.run.called
