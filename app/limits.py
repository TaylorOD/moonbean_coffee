import threading
import time
from collections import defaultdict, deque


class RateLimiter:
    """Allows `limit` hits per key in a rolling window. Lives in memory, so it
    resets on restart and only works with a single server process."""

    def __init__(self, limit, window_seconds, clock=time.monotonic):
        self.limit = limit
        self.window = window_seconds
        self.clock = clock
        self.hits = defaultdict(deque)
        self.lock = threading.Lock()

    def _prune(self, key):
        hits = self.hits[key]
        cutoff = self.clock() - self.window
        while hits and hits[0] <= cutoff:
            hits.popleft()
        if not hits:
            del self.hits[key]
            return deque()
        return hits

    def is_blocked(self, key):
        with self.lock:
            return len(self._prune(key)) >= self.limit

    def record(self, key):
        with self.lock:
            self.hits[key].append(self.clock())

    def clear(self, key):
        with self.lock:
            self.hits.pop(key, None)
