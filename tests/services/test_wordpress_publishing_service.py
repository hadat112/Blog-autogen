import requests
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import models
from app.db.session import Base
from app.integrations.wordpress.destination import AmbiguousWordPressResult
from app.services.wordpress_publishing_service import WordPressPublishingService, plain_text_to_html


class Gateway:
    posts = []
    def __init__(self, config): pass
    def upload_remote(self, source): return "9"
    def upload_file(self, source): return "8"
    def create_post(self, title, content, status, category_id, media_id):
        self.posts.append((title, content, status, category_id, media_id))
        return {"id": "42", "link": "https://wp.test/post", "status": status}


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    account = models.Account(id="wp", name="WP", type="wp", config={"url": "https://wp.test"})
    pipeline = models.Pipeline(id="pipeline", name="Publisher", type="wp_publish", language="", step_accounts={"wp": "wp"})
    session.add_all([account, pipeline]); session.commit()
    yield session
    session.close()


def test_strict_publisher_records_ids_and_prevents_duplicate(db):
    Gateway.posts.clear()
    draft = models.ContentDraft(id="draft", kind="manual", pipeline_id="pipeline", title="Title", content="Line 1\n\nLine 2", content_format="plain", wp_status="draft", state="ready_for_review", image_kind="url", image_source="https://img.test/a.jpg")
    db.add(draft); db.commit()
    result = WordPressPublishingService(db, Gateway).publish("draft")
    assert result.wp_post_id == "42" and result.wp_media_id == "9"
    assert Gateway.posts[0][1] == "<p>Line 1</p>\n<p>Line 2</p>"
    with pytest.raises(ValueError, match="already created"):
        WordPressPublishingService(db, Gateway).publish("draft")


def test_publish_now_requires_confirmation(db):
    db.add(models.ContentDraft(id="draft", kind="manual", pipeline_id="pipeline", title="Title", content="Body", wp_status="publish", state="ready_for_review")); db.commit()
    with pytest.raises(ValueError, match="confirmation"):
        WordPressPublishingService(db, Gateway).publish("draft", confirmed=False)


def test_ambiguous_result_is_terminal_until_reconciled(db):
    class AmbiguousGateway(Gateway):
        def create_post(self, *args, **kwargs): raise AmbiguousWordPressResult("verify WordPress")
    db.add(models.ContentDraft(id="draft", kind="manual", pipeline_id="pipeline", title="Title", content="Body", wp_status="draft", state="ready_for_review")); db.commit()
    with pytest.raises(AmbiguousWordPressResult):
        WordPressPublishingService(db, AmbiguousGateway).publish("draft")
    assert db.get(models.ContentDraft, "draft").state == "publish_unknown"
    with pytest.raises(ValueError, match="ambiguous"):
        WordPressPublishingService(db, Gateway).publish("draft")


def test_non_prefix_caption_does_not_block_wordpress_publication(db):
    Gateway.posts.clear()
    db.add(models.ContentDraft(
        id="draft",
        kind="manual",
        pipeline_id="pipeline",
        title="Title",
        content="Story opening",
        caption="Independent social caption",
        wp_status="draft",
        state="ready_for_review",
    ))
    db.commit()

    result = WordPressPublishingService(db, Gateway).publish("draft")
    assert result.state == "wordpress_created"
