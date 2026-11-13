import asyncio
from app.domain.workflow_runner import WorkflowRunner


def test_two_workflows_start_before_either_finishes():
    async def run():
        runner = WorkflowRunner()
        entered = []
        both = asyncio.Event()
        async def work(name):
            entered.append(name)
            if len(entered) == 2:
                both.set()
            await asyncio.wait_for(both.wait(), timeout=.3)
        runner.start('first', lambda: work('first'))
        runner.start('second', lambda: work('second'))
        await runner.worker_task
        assert entered == ['first', 'second']
    asyncio.run(run())


def test_new_workflow_wakes_dispatcher_while_another_is_running():
    async def run():
        runner = WorkflowRunner()
        first_entered, release, second_entered = asyncio.Event(), asyncio.Event(), asyncio.Event()
        async def first():
            first_entered.set()
            await release.wait()
        async def second():
            second_entered.set()
        runner.start('first', first)
        await first_entered.wait()
        runner.start('second', second)
        try:
            await asyncio.wait_for(second_entered.wait(), timeout=.3)
        finally:
            release.set()
            await runner.worker_task
    asyncio.run(run())


def test_cancelling_async_wrappers_does_not_release_real_thread_slots():
    from app.domain.workflow_threads import run_workflow_blocking
    import threading
    async def run():
        release = threading.Event()
        lock = threading.Lock()
        state = {'active':0, 'peak':0}
        def work():
            with lock:
                state['active'] += 1
                state['peak'] = max(state['peak'],state['active'])
            release.wait(timeout=3)
            with lock:
                state['active'] -= 1
        first = [asyncio.create_task(run_workflow_blocking(work)) for _ in range(8)]
        second = []
        try:
            for _ in range(300):
                if state['active'] == 8:
                    break
                await asyncio.sleep(.005)
            assert state['active'] == 8
            for task in first:
                task.cancel()
            await asyncio.gather(*first,return_exceptions=True)
            second = [asyncio.create_task(run_workflow_blocking(work)) for _ in range(8)]
            await asyncio.sleep(.1)
            assert state['peak'] == 8
        finally:
            release.set()
            await asyncio.gather(*second,return_exceptions=True)
    asyncio.run(run())


def test_worker_admission_timeout_does_not_start_network_operation(monkeypatch):
    import threading
    import pytest
    import app.domain.workflow_threads as module
    slots = threading.BoundedSemaphore(1)
    slots.acquire()
    release = threading.Timer(.2, slots.release)
    release.start()
    monkeypatch.setattr(module, '_slots', slots)
    entered = []
    async def run():
        with pytest.raises(TimeoutError, match='Workflow worker wait timed out'):
            await module.run_workflow_blocking(lambda: entered.append(True), worker_wait_timeout=.02)
    try:
        asyncio.run(run())
        assert not entered
    finally:
        release.join(1)
    assert slots.acquire(blocking=False)
    slots.release()


def test_failure_before_workflow_starts_marks_job_failed(tmp_path, monkeypatch):
    import app.domain.workflow_runner as module
    from app.db import models
    from app.db.session import Base
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    engine = create_engine(f'sqlite:///{tmp_path / "runner.db"}')
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    monkeypatch.setattr(module, 'SessionLocal', factory)
    with factory() as db:
        db.add(models.Job(id='waiting', workflow_type='article_v1', status='queued', draft_id='draft'))
        db.add(models.ContentDraft(id='draft', kind='article', state='generating'))
        db.commit()
    async def fail():
        raise TimeoutError('Workflow worker wait timed out')
    async def run():
        runner = module.WorkflowRunner()
        runner.start('waiting', fail)
        await runner.worker_task
    asyncio.run(run())
    with factory() as db:
        job = db.get(models.Job, 'waiting')
        assert job.status == 'failed'
        assert 'worker wait timed out' in job.logs[-1]['detail']
        assert db.get(models.ContentDraft, 'draft').state == 'generation_failed'
    engine.dispose()
