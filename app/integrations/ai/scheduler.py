import threading
import time
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
        with self._condition:
            self._cooldowns[key] = max(self._cooldowns[key], time.monotonic() + max(0, seconds))
            self._condition.notify_all()

    def _next_queue(self, account_key):
        queues = self._queues[account_key]
        if queues["background"] and (not queues["foreground"] or self._foreground_streak[account_key] >= 5):
            return "background"
        return "foreground" if queues["foreground"] else "background"

    @contextmanager
    def permit(self, account_key, limit=1, priority="foreground", cancelled=None):
        if priority not in {"foreground", "background"}:
            raise ValueError("Unsupported AI request priority")
        key = account_key or "default"
        capacity = max(1, min(int(limit or 1), 8))
        ticket = object()
        with self._condition:
            self._queues[key][priority].append(ticket)
            while True:
                if cancelled and cancelled():
                    self._queues[key][priority].remove(ticket)
                    self._condition.notify_all()
                    raise InterruptedError("AI request cancelled while waiting")
                selected = self._next_queue(key)
                own_turn = selected == priority and self._queues[key][priority][0] is ticket
                if (own_turn and self._active[key] < self.capacity(key, capacity)
                        and time.monotonic() >= self._cooldowns[key]):
                    self._queues[key][priority].popleft()
                    self._active[key] += 1
                    if priority == "foreground":
                        self._foreground_streak[key] += 1
                    else:
                        self._foreground_streak[key] = 0
                    break
                self._condition.wait(timeout=0.1)
        try:
            yield
        finally:
            with self._condition:
                self._active[key] -= 1
                self._condition.notify_all()


ai_request_scheduler = AIRequestScheduler()
