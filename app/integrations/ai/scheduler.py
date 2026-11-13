import threading
import time
import math
from collections import defaultdict, deque
from contextlib import contextmanager


class AIRequestScheduler:
    """Thread-safe admission control shared by legacy and workflow AI calls."""

    def __init__(self):
        self._limits = defaultdict(dict)
        self._cooldowns = defaultdict(float)
        self._condition = threading.Condition()
        self._active = defaultdict(int)
        self._queues = defaultdict(lambda: {"foreground": deque(), "background": deque()})
        self._foreground_streak = defaultdict(int)

    def unregister(self, owner):
        with self._condition:
            for limits in self._limits.values():
                limits.pop(owner, None)
            self._condition.notify_all()

    def register(self, key, owner, limit):
        with self._condition:
            # An account can change credentials; remove its old registration.
            for existing in self._limits.values():
                existing.pop(owner, None)
            self._limits[key][owner] = max(1, min(int(limit), 8))
            self._condition.notify_all()

    def capacity(self, key, fallback=2):
        with self._condition:
            return min(self._limits[key].values(), default=fallback)

    def cooldown(self, key, seconds):
        seconds = float(seconds)
        if not math.isfinite(seconds):
            raise ValueError("AI cooldown must be finite")
        with self._condition:
            self._cooldowns[key] = max(self._cooldowns[key], time.monotonic() + max(0, min(seconds, 30)))
            self._condition.notify_all()

    def snapshot(self, key, fallback=2):
        with self._condition:
            return {"active": self._active[key], "capacity": self.capacity(key, fallback),
                    "waiting": sum(len(q) for q in self._queues[key].values()),
                    "cooldown_seconds": max(0, self._cooldowns[key] - time.monotonic())}

    def _next_queue(self, account_key):
        queues = self._queues[account_key]
        if queues["background"] and (not queues["foreground"] or self._foreground_streak[account_key] >= 5):
            return "background"
        return "foreground" if queues["foreground"] else "background"

    @contextmanager
    def permit(self, account_key, limit=1, priority="foreground", cancelled=None,
               *, wait_timeout=300, on_wait=None):
        if priority not in {"foreground", "background"}:
            raise ValueError("Unsupported AI request priority")
        key = account_key or "default"
        capacity = max(1, min(int(limit or 1), 8))
        wait_timeout = float(wait_timeout)
        if not math.isfinite(wait_timeout) or wait_timeout <= 0:
            raise ValueError("AI queue timeout must be positive and finite")
        deadline = time.monotonic() + wait_timeout
        ticket = object()
        admitted = False
        next_notice = 0
        with self._condition:
            self._queues[key][priority].append(ticket)
        try:
            while True:
                # These callbacks may read/write the DB or raise. Never hold the
                # global scheduler lock while invoking user code.
                if cancelled and cancelled():
                    raise InterruptedError("AI request cancelled while waiting")
                now = time.monotonic()
                if now >= deadline:
                    state = self.snapshot(key, capacity)
                    raise TimeoutError(f"AI queue wait timed out after {wait_timeout:g}s "
                                       f"(active={state['active']}, waiting={state['waiting']}, "
                                       f"capacity={state['capacity']}); retry after active requests finish")
                with self._condition:
                    selected = self._next_queue(key)
                    own_turn = selected == priority and self._queues[key][priority][0] is ticket
                    if (own_turn and self._active[key] < self.capacity(key, capacity)
                            and now >= self._cooldowns[key]):
                        self._queues[key][priority].popleft()
                        self._active[key] += 1
                        admitted = True
                        if priority == "foreground":
                            self._foreground_streak[key] += 1
                        else:
                            self._foreground_streak[key] = 0
                        break
                if on_wait and now >= next_notice:
                    on_wait(self.snapshot(key, capacity))
                    next_notice = time.monotonic() + 5
                with self._condition:
                    self._condition.wait(timeout=min(.1, max(0, deadline - time.monotonic())))
            yield
        finally:
            with self._condition:
                if admitted:
                    self._active[key] -= 1
                else:
                    self._queues[key][priority].remove(ticket)
                self._condition.notify_all()


ai_request_scheduler = AIRequestScheduler()
