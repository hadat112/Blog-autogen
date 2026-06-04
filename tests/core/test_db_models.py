import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from infrastructure.db.session import Base
from infrastructure.db.models import Account, Pipeline, Job

# Use an in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

def test_create_account(db):
    account_data = {
        "name": "Test Account",
        "type": "facebook",
        "config": {"token": "test_token"}
    }
    account = Account(**account_data)
    db.add(account)
    db.commit()
    db.refresh(account)

    assert account.id is not None
    assert account.name == "Test Account"
    assert account.type == "facebook"
    assert account.config == {"token": "test_token"}
    assert account.created_at is not None

def test_create_pipeline(db):
    pipeline_data = {
        "name": "Test Pipeline",
        "type": "story",
        "language": "en",
        "step_accounts": {"step1": "account1"},
        "settings": {"wp_category_id": "7"}
    }
    pipeline = Pipeline(**pipeline_data)
    db.add(pipeline)
    db.commit()
    db.refresh(pipeline)

    assert pipeline.id is not None
    assert pipeline.name == "Test Pipeline"
    assert pipeline.type == "story"
    assert pipeline.language == "en"
    assert pipeline.step_accounts == {"step1": "account1"}
    assert pipeline.settings == {"wp_category_id": "7"}
    assert pipeline.is_active is True

def test_create_job(db):
    pipeline = Pipeline(name="Pipeline for Job", type="story", step_accounts={})
    db.add(pipeline)
    db.commit()
    db.refresh(pipeline)

    job = Job(pipeline_id=pipeline.id)
    db.add(job)
    db.commit()
    db.refresh(job)

    assert job.id is not None
    assert job.pipeline_id == pipeline.id
    assert job.status == "running"
    assert job.start_time is not None
    assert job.progress == 0
    assert job.logs == []
    assert job.input_text is None
    assert job.input_type is None
