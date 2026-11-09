import asyncio

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import models
from app.db.session import Base
from app.domain.workflow_runner import WorkflowRunner


def test_cancel_queued_benchmark_marks_unstarted_rows(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'cancel.db'}")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    monkeypatch.setattr("app.domain.workflow_runner.SessionLocal", sessions)
    with sessions() as db:
        db.add(models.Job(id="benchmark", workflow_type="model_benchmark", status="queued", outputs={
            "results": [{"model_id": "a", "status": "waiting", "elapsed_seconds": None}],
        }))
        db.commit()
    runner = WorkflowRunner()
    runner.queue.append(("benchmark", lambda: None))
    assert asyncio.run(runner.cancel("benchmark")) == {"status": "cancelled"}
    with sessions() as db:
        job = db.get(models.Job, "benchmark")
        assert job.status == "cancelled"
        assert job.outputs["results"][0]["status"] == "cancelled"
    engine.dispose()
