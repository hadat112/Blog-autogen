from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import models
from app.db.session import Base
from app.services.pattern_collection_service import PatternCollectionService


def test_collection_creates_child_job_without_changing_parent(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    pipeline = models.Pipeline(id="p", name="Crawl", type="crawl", language="English", step_accounts={"ai": "ai"})
    parent = models.Job(id="parent", pipeline_id="p", status="success", progress=100)
    rule = models.ThemeRule(tag="family", keywords=["mother"], is_active=True)
    db.add_all([pipeline, parent, rule]); db.commit()
    started = []
    monkeypatch.setattr("app.services.pattern_collection_service.threading.Thread.start", lambda self: started.append(True))
    article, child = PatternCollectionService(db).collect(
        {"source_url": "https://source.test/story", "title": "A mother returns", "content": "Full article"},
        "p", parent_job_id="parent", ai_account_id="ai",
    )
    assert article.theme_tags == ["family"]
    assert child.parent_job_id == "parent" and child.workflow_type == "pattern_analysis"
    assert db.get(models.Job, "parent").status == "success"
    assert started == [True]
    db.close()
