import pytest
import asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.session import Base
from app.db.models import Pipeline, Account, Job, Language
from app.domain.job_runner import JobRunner

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
async def test_job_runner_pipeline_run(db, mocker):
    # Mock SessionLocal in app.domain.job_runner to use our test DB
    mocker.patch("app.domain.job_runner.SessionLocal", TestingSessionLocal)
    
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
    
    # Mock StoryOrchestrator
    mock_story_orchestrator = mocker.patch("app.domain.job_runner.StoryOrchestrator")
    mock_instance = mock_story_orchestrator.return_value
    mock_instance.run.return_value = [{"status": "success"}]
    
    # 2. Run JobRunner
    wm = JobRunner()
    job_id = await wm.start_pipeline_run(pipeline.id, db)

    # 3. Verify Job creation and status
    job = db.query(Job).filter(Job.id == job_id).first()
    assert job is not None
    assert job.status in ["success", "running", "queued"]

    # Let's wait a bit longer for the background task to finish
    for _ in range(20): # increased to 2 seconds
        db.refresh(job)
        if job.status == "success":
            break
        await asyncio.sleep(0.1)

    assert job.status == "success"
    assert job.progress == 100

    assert mock_instance.run.called
    assert mock_story_orchestrator.call_args.kwargs["num_threads"] == 1

@pytest.mark.anyio
async def test_job_runner_uses_pipeline_wp_category(db, mocker):
    mocker.patch("app.domain.job_runner.SessionLocal", TestingSessionLocal)

    wp_account = Account(
        name="Test WP",
        type="wp",
        config={
            "url": "https://wp.example.com",
            "username": "user",
            "password": "pass",
            "category_id": "old-account-category",
        },
    )
    db.add(wp_account)
    db.commit()

    pipeline = Pipeline(
        name="Test Pipeline",
        type="story",
        step_accounts={"wp": wp_account.id},
        settings={"wp_category_id": "new-pipeline-category"},
    )
    db.add(pipeline)
    db.commit()

    mock_story_orchestrator = mocker.patch("app.domain.job_runner.StoryOrchestrator")
    mock_story_orchestrator.return_value.run.return_value = [{"status": "success"}]

    wm = JobRunner()
    await wm.start_pipeline_run(pipeline.id, db)

    wp_config = mock_story_orchestrator.call_args.kwargs["wp_config"]
    assert wp_config["category_id"] == "new-pipeline-category"


@pytest.mark.anyio
async def test_job_runner_uses_ai_account_fallback_text_model(db, mocker):
    mocker.patch("app.domain.job_runner.SessionLocal", TestingSessionLocal)

    ai_account = Account(
        name="Test AI",
        type="ai",
        config={
            "api_key": "test",
            "text_model": "primary-model",
            "fallback_text_model": "fallback-model",
        },
    )
    db.add(ai_account)
    db.commit()

    pipeline = Pipeline(
        name="Test Pipeline",
        type="story",
        step_accounts={"ai": ai_account.id},
        settings={"fallback_text_model": "pipeline-model"},
    )
    db.add(pipeline)
    db.commit()

    mock_story_orchestrator = mocker.patch("app.domain.job_runner.StoryOrchestrator")
    mock_story_orchestrator.return_value.run.return_value = [{"status": "success"}]

    await JobRunner().start_pipeline_run(pipeline.id, db)

    ai_config = mock_story_orchestrator.call_args.kwargs["ai_config"]
    assert ai_config["text_model"] == "primary-model"
    assert ai_config["fallback_text_model"] == "fallback-model"


@pytest.mark.anyio
async def test_job_runner_uses_configured_prompt_language(db, mocker):
    mocker.patch("app.domain.job_runner.SessionLocal", TestingSessionLocal)
    db.add(Language(
        code="nl",
        display_name="Nederlands",
        is_active=True,
    ))
    pipeline = Pipeline(
        name="Dutch Pipeline",
        type="story",
        language="Nederlands",
        step_accounts={},
    )
    db.add(pipeline)
    db.commit()

    mock_story_orchestrator = mocker.patch("app.domain.job_runner.StoryOrchestrator")
    mock_story_orchestrator.return_value.run.return_value = [{"status": "success"}]

    await JobRunner().start_pipeline_run(pipeline.id, db)

    assert mock_story_orchestrator.call_args.kwargs["language"] == "Nederlands"
    assert "language_name" not in mock_story_orchestrator.call_args.kwargs


@pytest.mark.anyio
async def test_original_crawl_pipeline_runs_without_queue_lock(db, mocker):
    mocker.patch("app.domain.job_runner.SessionLocal", TestingSessionLocal)
    pipeline = Pipeline(
        name="Original Repost",
        type="crawl",
        language="",
        step_accounts={},
    )
    db.add(pipeline)
    db.commit()

    mock_story_orchestrator = mocker.patch("app.domain.job_runner.StoryOrchestrator")
    mock_story_orchestrator.return_value.process_crawl.return_value = {"status": "success"}

    wm = JobRunner()
    lock = wm._get_run_lock()
    await lock.acquire()
    try:
        job_id = await wm.start_pipeline_run(
            pipeline.id,
            db,
            prompt="https://example.com/post",
        )

        job = db.query(Job).filter(Job.id == job_id).first()
        assert job.status == "running"

        for _ in range(20):
            db.refresh(job)
            if job.status == "success":
                break
            await asyncio.sleep(0.1)

        assert job.status == "success"
        assert mock_story_orchestrator.return_value.process_crawl.called
    finally:
        lock.release()
