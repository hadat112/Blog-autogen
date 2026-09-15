from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import models
from app.db.session import Base
from app.services.workflow_job_service import WorkflowJobService


def test_restart_recovery_marks_new_workflows_without_touching_legacy():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    pipeline = models.Pipeline(id="p", name="P", type="rewrite", language="English", step_accounts={})
    draft = models.ContentDraft(id="d", kind="rewrite", pipeline_id="p", state="generating")
    db.add_all([
        pipeline, draft,
        models.Job(id="new", pipeline_id="p", workflow_type="rewrite", status="running", draft_id="d"),
        models.Job(id="old", pipeline_id="p", workflow_type="legacy", status="running"),
        models.Article(id="a", source_url="https://source.test/a", analysis_status="processing"),
    ]); db.commit()
    assert WorkflowJobService(db).recover_interrupted() == 1
    assert db.get(models.Job, "new").status == "failed"
    assert db.get(models.Job, "old").status == "running"
    assert db.get(models.ContentDraft, "d").state == "generation_failed"
    assert db.get(models.Article, "a").analysis_status == "failed"


def test_terminal_job_cannot_be_revived_by_late_worker_result():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    pipeline = models.Pipeline(id="p", name="P", type="rewrite", language="English", step_accounts={})
    job = models.Job(id="j", pipeline_id="p", workflow_type="rewrite", status="cancelled", progress=25)
    db.add_all([pipeline, job])
    db.commit()

    service = WorkflowJobService(db)
    service.progress("j", "Late progress", 80)
    service.complete("j", {"draft_id": "late"})
    service.fail("j", "late error")

    db.refresh(job)
    assert job.status == "cancelled"
    assert job.progress == 25
    assert job.outputs == {}


def test_progress_records_current_step_detail_and_failed_step():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    job = models.Job(id="j", pipeline_id="p", workflow_type="rewrite", status="queued", logs=[], outputs={})
    db.add(job)
    db.commit()

    service = WorkflowJobService(db)
    service.progress("j", "rewrite_story", 42, "Rewriting chunk 2/4")
    service.fail("j", "AI returned an empty rewrite")

    db.refresh(job)
    assert job.status == "failed"
    assert job.current_step == "Failed"
    assert job.outputs == {"failed_step": "rewrite_story"}
    assert job.logs[-2]["step_name"] == "rewrite_story"
    assert job.logs[-2]["detail"] == "Rewriting chunk 2/4"
