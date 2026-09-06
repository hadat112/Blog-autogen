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
