import threading
import time

from app.integrations.ai.scheduler import AIRequestScheduler


def test_scheduler_limits_same_account_and_isolates_accounts():
    scheduler = AIRequestScheduler()
    active = {"a": 0, "b": 0}
    peaks = {"a": 0, "b": 0}
    lock = threading.Lock()

    def work(account):
        with scheduler.permit(account, 2):
            with lock:
                active[account] += 1
                peaks[account] = max(peaks[account], active[account])
            time.sleep(0.03)
            with lock:
                active[account] -= 1

    threads = [threading.Thread(target=work, args=("a",)) for _ in range(5)] + [threading.Thread(target=work, args=("b",)) for _ in range(3)]
    for thread in threads: thread.start()
    for thread in threads: thread.join()
    assert peaks == {"a": 2, "b": 2}


def test_scheduler_releases_permit_after_error():
    scheduler = AIRequestScheduler()
    try:
        with scheduler.permit("a", 1):
            raise RuntimeError("boom")
    except RuntimeError:
        pass
    with scheduler.permit("a", 1):
        assert True


def test_scheduler_prioritizes_foreground_but_does_not_starve_background():
    scheduler = AIRequestScheduler()
    order = []
    threads = []

    def work(name, priority):
        with scheduler.permit("a", 1, priority):
            order.append(name)
            time.sleep(0.005)

    with scheduler.permit("a", 1, "background"):
        background = threading.Thread(target=work, args=("background", "background"))
        background.start()
        threads.append(background)
        while len(scheduler._queues["a"]["background"]) < 1:
            time.sleep(0.001)
        for index in range(6):
            thread = threading.Thread(target=work, args=(f"foreground-{index}", "foreground"))
            thread.start()
            threads.append(thread)
            while len(scheduler._queues["a"]["foreground"]) < index + 1:
                time.sleep(0.001)

    for thread in threads:
        thread.join()

    assert order[:5] == [f"foreground-{index}" for index in range(5)]
    assert order[5] == "background"
    assert order[6] == "foreground-5"


def test_status_callback_exception_cleans_ticket_and_next_request_runs():
    import pytest
    scheduler = AIRequestScheduler()
    def broken():
        raise RuntimeError('status DB failed')
    with pytest.raises(RuntimeError, match='status DB failed'):
        with scheduler.permit('a', cancelled=broken):
            pass
    assert not scheduler._queues['a']['foreground']
    with scheduler.permit('a', wait_timeout=.2):
        pass


def test_slow_status_check_does_not_block_other_accounts():
    scheduler = AIRequestScheduler()
    checking, release, other_entered = threading.Event(), threading.Event(), threading.Event()
    errors = []
    def slow_check():
        checking.set()
        release.wait(2)
        return True
    def waiter():
        try:
            with scheduler.permit('a', cancelled=slow_check):
                pass
        except InterruptedError:
            pass
        except Exception as exc:
            errors.append(exc)
    def other():
        with scheduler.permit('b'):
            other_entered.set()
    first = threading.Thread(target=waiter)
    second = threading.Thread(target=other)
    first.start()
    try:
        assert checking.wait(1)
        second.start()
        assert other_entered.wait(.5)
    finally:
        release.set()
        first.join(2)
        if second.ident:
            second.join(2)
    assert not errors


def test_admission_timeout_removes_waiter_and_reports_capacity():
    import pytest
    scheduler = AIRequestScheduler()
    with scheduler.permit('a', 1):
        with pytest.raises(TimeoutError, match='AI queue wait timed out'):
            with scheduler.permit('a', 1, wait_timeout=.02):
                pass
        snapshot = scheduler.snapshot('a')
        assert snapshot['active'] == 1
        assert snapshot['waiting'] == 0
    with scheduler.permit('a', 1, wait_timeout=.1):
        pass


def test_cooldown_is_finite_and_capped():
    import pytest
    scheduler = AIRequestScheduler()
    for value in (float('inf'), float('nan')):
        with pytest.raises(ValueError):
            scheduler.cooldown('a', value)
    scheduler.cooldown('a', 86400)
    assert 0 < scheduler.snapshot('a')['cooldown_seconds'] <= 30


def test_admission_progress_callback_error_cleans_ticket():
    import pytest
    scheduler = AIRequestScheduler()
    def broken(snapshot):
        raise RuntimeError('progress DB failed')
    with scheduler.permit('a', 1):
        with pytest.raises(RuntimeError, match='progress DB failed'):
            with scheduler.permit('a', 1, on_wait=broken):
                pass
        assert not scheduler._queues['a']['foreground']


def test_cancelled_waiter_does_not_block_the_next_request():
    scheduler = AIRequestScheduler()
    cancelled = threading.Event()
    waiting = threading.Event()
    stopped = threading.Event()
    def work():
        try:
            with scheduler.permit('a', 1, cancelled=cancelled.is_set,
                                  on_wait=lambda state: waiting.set()):
                raise AssertionError('cancelled request must not be admitted')
        except InterruptedError:
            stopped.set()
    with scheduler.permit('a', 1):
        thread = threading.Thread(target=work)
        thread.start()
        try:
            assert waiting.wait(1)
            cancelled.set()
            assert stopped.wait(1)
        finally:
            cancelled.set()
            thread.join(2)
    with scheduler.permit('a', 1, wait_timeout=.1):
        assert scheduler.snapshot('a')['active'] == 1
    assert scheduler.snapshot('a')['waiting'] == 0
