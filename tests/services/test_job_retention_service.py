from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import models
from app.services.job_retention_service import JobRetentionService


@pytest.fixture
def db():
    from app.db.session import Base

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


def test_prune_keeps_500_newest_jobs_and_does_not_delete_active_jobs(db):
    now = datetime.utcnow()
    db.add_all([
        models.Job(id=f"job-{index}", status="success", start_time=now - timedelta(seconds=index))
        for index in range(501)
    ])
    db.add(models.Job(id="old-running", status="running", start_time=now - timedelta(days=1)))
    db.commit()

    deleted = JobRetentionService(db).prune()

    assert deleted == 2
    assert db.query(models.Job).count() == 500
    assert db.get(models.Job, "old-running") is not None


def test_prune_compacts_old_successful_draft_bodies_but_keeps_metadata(db):
    now = datetime.utcnow()
    db.add_all([
        models.ContentDraft(
            id=f"draft-{index}",
            kind="article_v2",
            title=f"Story {index}",
            content="large generated story",
            caption="teaser",
            state="wordpress_created",
            wp_post_id=str(index),
            updated_at=now - timedelta(seconds=index),
        )
        for index in range(101)
    ])
    db.commit()

    JobRetentionService(db).prune()

    assert db.get(models.ContentDraft, "draft-0").content == "large generated story"
    assert db.get(models.ContentDraft, "draft-100").content == ""
    assert db.get(models.ContentDraft, "draft-100").wp_post_id == "100"
