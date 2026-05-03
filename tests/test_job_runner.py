from unittest.mock import patch

from core.run_options import RunOptions
from core.job_runner import JobRunner


def test_submit_manual_run_enqueues_job():
    runner = JobRunner(config={})
    opts = RunOptions(limit=1, threads=1, language="en", debug=False, update=False, with_image=False, no_image=False)

    job_id = runner.submit_manual_run(options=opts)

    assert runner.queue.qsize() == 1
    queue_item = runner.queue.get_nowait()
    assert queue_item["job_id"] == job_id


def test_submit_manual_run_returns_job_id_and_tracks_queued_state():
    runner = JobRunner(config={})
    opts = RunOptions(limit=1, threads=1, language="en", debug=False, update=False, with_image=False, no_image=False)

    job_id = runner.submit_manual_run(options=opts)

    assert isinstance(job_id, str)

    state = runner.get_job_status(job_id)

    assert state["status"] == "queued"
    assert state["step_progress"] == 0


@patch("core.job_runner.Orchestrator")
def test_worker_executes_orchestrator_with_resolved_image_toggle(mock_orch_cls):
    config = {"enable_image_generation": False}
    runner = JobRunner(config=config)
    opts = RunOptions(limit=1, threads=1, language="en", debug=False, update=False, with_image=True, no_image=False)

    runner._execute_once(options=opts)

    assert mock_orch_cls.call_args.kwargs["enable_image_generation"] is True
