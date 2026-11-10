import time
from collections import deque
from threading import Lock

# Failed sign-ins allowed inside the window, before the door closes for a while
MAX_FAILURES_PER_ACCOUNT = 5   # same email from the same address
MAX_FAILURES_PER_ADDRESS = 20  # any email from the same address
WINDOW_SECONDS = 15 * 60


class LoginThrottle:
    """Counts failed sign-ins in memory.

    Kept per process: with several workers or servers the counts move to Redis,
    otherwise each worker keeps its own count and the limit stops meaning anything.
    """

    def __init__(self, window_seconds: int = WINDOW_SECONDS):
        self.window_seconds = window_seconds
        self._failures: dict[str, deque[float]] = {}
        self._lock = Lock()

    def _recent(self, key: str, now: float) -> deque[float]:
        times = self._failures.get(key, deque())
        while times and now - times[0] >= self.window_seconds:
            times.popleft()
        if not times:
            # Forget quiet keys, so the dict does not grow with every email ever tried
            self._failures.pop(key, None)
        return times

    def retry_after(self, key: str, limit: int) -> int:
        """Seconds until the next attempt is allowed; 0 if it is allowed now."""
        now = time.monotonic()
        with self._lock:
            times = self._recent(key, now)
            if len(times) < limit:
                return 0
            return int(self.window_seconds - (now - times[0])) + 1

    def record_failure(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            times = self._recent(key, now)
            times.append(now)
            self._failures[key] = times

    def reset(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)


login_throttle = LoginThrottle()
