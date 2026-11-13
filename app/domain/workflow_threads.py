"""Bound real synchronous executions, including threads outliving cancellation."""
import asyncio
import threading
import time

_slots = threading.BoundedSemaphore(8)


async def run_workflow_blocking(operation, *args, worker_wait_timeout=300, **kwargs):
    # Wait cooperatively, without filling the default executor with threads
    # blocked on a semaphore. Cancelled waiters must not consume real workers.
    deadline = time.monotonic() + worker_wait_timeout
    while not _slots.acquire(blocking=False):
        if time.monotonic() >= deadline:
            raise TimeoutError("Workflow worker wait timed out; previous network requests are still finishing")
        await asyncio.sleep(min(.05, max(0, deadline - time.monotonic())))
    cancelled = threading.Event()
    def invoke():
        try:
            if not cancelled.is_set():
                return operation(*args, **kwargs)
        finally:
            _slots.release()
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
