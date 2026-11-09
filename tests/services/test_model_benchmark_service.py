import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import models
from app.db.session import Base
from app.integrations.ai.openai_compatible import AITextResult
from app.services.model_benchmark_service import ModelBenchmarkService
from app.services.workflow_job_service import WorkflowJobService


@pytest.fixture
def sessions(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'benchmark.db'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    monkeypatch.setattr("app.services.model_benchmark_service.SessionLocal", factory)
    with factory() as db:
        db.add(models.Account(id="ai", name="AI", type="ai", config={"api_key": "secret-key", "base_url": "http://local/v1"}))
        db.add(models.Job(id="job", workflow_type="model_benchmark", status="queued", outputs={
            "account_id": "ai", "sample_id": "ceo-ceremony-parts-1-2-v1",
            "model_ids": ["one", "two", "three"],
            "results": [{"model_id": m, "status": "waiting", "elapsed_seconds": None} for m in ("one", "two", "three")],
        }))
        db.commit()
    yield factory
    engine.dispose()


def test_sequential_calls_same_prompt_and_persists_only_metadata(sessions, monkeypatch):
    calls = []

    class FakeAI:
        text_model = ""

        def chat_with_meta(self, messages):
            calls.append((self.text_model, messages))
            if self.text_model == "two":
                raise RuntimeError("secret-key provider leaked translation")
            return AITextResult("Przetłumaczony tekst", self.text_model, "length", {})

    monkeypatch.setattr("app.services.model_benchmark_service.create_ai_client", lambda account: FakeAI())
    ModelBenchmarkService.execute("job")
    with sessions() as db:
        job = db.get(models.Job, "job")
        rows = job.outputs["results"]
        assert [model for model, _ in calls] == ["one", "two", "three"]
        assert calls[0][1] == calls[1][1] == calls[2][1]
        assert "PART 2" in calls[0][1][-1]["content"]
        assert [row["status"] for row in rows] == ["success", "error", "success"]
        assert all(isinstance(row["elapsed_seconds"], float) for row in rows)
        assert job.status == "partial_success"
        assert "secret-key" not in str(job.outputs) + str(job.logs)
        assert "Przetłumaczony" not in str(job.outputs) + str(job.logs)


def test_empty_response_fails_and_cancel_stops_next_model(sessions, monkeypatch):
    calls = []

    class FakeAI:
        text_model = ""

        def chat_with_meta(self, messages):
            calls.append(self.text_model)
            if self.text_model == "one":
                return AITextResult("   ", self.text_model, "stop", {})
            with sessions() as db:
                job = db.get(models.Job, "job")
                job.status = "cancelled"
                db.commit()
            return AITextResult("Text", self.text_model, "stop", {})

    monkeypatch.setattr("app.services.model_benchmark_service.create_ai_client", lambda account: FakeAI())
    ModelBenchmarkService.execute("job")
    with sessions() as db:
        job = db.get(models.Job, "job")
        assert calls == ["one", "two"]
        assert job.status == "cancelled"
        assert [row["status"] for row in job.outputs["results"]] == ["error", "cancelled", "cancelled"]


def test_restart_retains_completed_rows_and_closes_interrupted_rows(sessions):
    with sessions() as db:
        job = db.get(models.Job, "job")
        job.status = "running"
        job.outputs = {**job.outputs, "results": [
            {"model_id": "one", "status": "success", "elapsed_seconds": 1.5},
            {"model_id": "two", "status": "running", "elapsed_seconds": None},
            {"model_id": "three", "status": "waiting", "elapsed_seconds": None},
        ]}
        db.commit()
        assert WorkflowJobService(db).recover_interrupted() == 1
        db.refresh(job)
        assert job.status == "failed"
        assert [row["status"] for row in job.outputs["results"]] == ["success", "error", "cancelled"]
        assert job.outputs["results"][0]["elapsed_seconds"] == 1.5


@pytest.mark.parametrize('cancel_on_read', [2, 3, 8])
def test_concurrent_cancel_cannot_be_overwritten_by_worker(sessions, monkeypatch, cancel_on_read):
    """Cancel after a status read, or immediately after its fenced write commits."""
    session_class = sessions.class_
    original_get, original_commit = session_class.get, session_class.commit
    state = {'reads': 0, 'triggered': False, 'deferred': False, 'cancelled': False, 'rows': []}
    calls = []

    def cancel():
        state['triggered'] = True
        state['deferred'] = False
        with sessions() as other:
            job = other.query(models.Job).filter_by(id='job').one()
            state['rows'] = list(job.outputs['results'])
            changed = other.query(models.Job).filter(models.Job.id == 'job',
                models.Job.status.in_(['queued', 'running'])).update({'status': 'cancelled'}, synchronize_session=False)
            state['cancelled'] = changed == 1
            other.commit()

    def get(db, entity, ident, **kwargs):
        value = original_get(db, entity, ident, **kwargs)
        if entity is models.Job and ident == 'job' and not state['triggered']:
            state['reads'] += 1
            if state['reads'] == cancel_on_read:
                # SQLite cannot accept a competing cancellation while this
                # transaction owns the write lock: it linearizes after commit.
                if db.connection().connection.driver_connection.in_transaction:
                    state['deferred'] = True
                else:
                    cancel()
        return value

    def commit(db):
        original_commit(db)
        if state['deferred'] and not state['triggered']:
            cancel()

    class FakeAI:
        text_model = ''
        def chat_with_meta(self, messages):
            calls.append(self.text_model)
            return AITextResult('Test translation', self.text_model, 'stop', {})

    monkeypatch.setattr(session_class, 'get', get)
    monkeypatch.setattr(session_class, 'commit', commit)
    monkeypatch.setattr('app.services.model_benchmark_service.create_ai_client', lambda account: FakeAI())
    ModelBenchmarkService.execute('job')
    assert state['triggered']
    with sessions() as db:
        job = db.get(models.Job, 'job')
        assert job.status == ('cancelled' if state['cancelled'] else 'success')
        if state['cancelled']:
            expected = ['cancelled' if row['status'] in {'waiting', 'running'} else row['status'] for row in state['rows']]
            assert [row['status'] for row in job.outputs['results']] == expected
            if cancel_on_read < 8:
                assert calls in ([], ['one'])
