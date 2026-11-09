"""Bound real synchronous executions, including threads outliving cancellation."""
import asyncio
import threading

_slots = threading.BoundedSemaphore(8)


async def run_workflow_blocking(operation, *args, **kwargs):
    cancelled = threading.Event()
    def invoke():
        with _slots:
            if not cancelled.is_set():
                return operation(*args, **kwargs)
    task = asyncio.create_task(asyncio.to_thread(invoke))
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError:
        cancelled.set()
        # to_thread cannot stop an in-flight request. Its real slot stays held.
        def consume(done):
            if not done.cancelled():
                done.exception()
        task.add_done_callback(consume)
        raise
