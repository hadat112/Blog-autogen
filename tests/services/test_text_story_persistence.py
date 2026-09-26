import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import models
from app.db.session import Base
from app.services.content_draft_service import ContentDraftService


@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        yield db
    engine.dispose()


def test_composition_is_unique_per_draft_and_deleted_with_it(test_db):
    draft = models.ContentDraft(kind="text_story", state="generating")
    test_db.add(draft)
    test_db.flush()
    record = models.TextStoryComposition(
        draft_id=draft.id,
        source_text="source",
        prompt_version="text-story-v1",
        stage_status={"rewrite": "pending", "title": "pending", "image_prompt": "pending", "enhance": "pending"},
    )
    test_db.add(record)
    test_db.commit()
    assert test_db.query(models.TextStoryComposition).filter_by(draft_id=draft.id).one().source_text == "source"

    test_db.add(models.TextStoryComposition(
        draft_id=draft.id,
        source_text="duplicate",
        prompt_version="text-story-v1",
        stage_status={},
    ))
    with pytest.raises(IntegrityError):
        test_db.commit()
    test_db.rollback()

    assert ContentDraftService(test_db).delete(draft.id) is True
    assert test_db.query(models.TextStoryComposition).filter_by(draft_id=draft.id).count() == 0
