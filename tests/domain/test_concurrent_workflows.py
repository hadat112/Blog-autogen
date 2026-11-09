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
