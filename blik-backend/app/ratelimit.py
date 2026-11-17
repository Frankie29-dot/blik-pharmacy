import threading
import time
from collections import deque
from collections.abc import Callable

from fastapi import HTTPException, Request, status

from app.config import settings


class RateLimiter:
    """Sliding-window limiter per client IP, used as a FastAPI dependency.

    State is in memory, so each worker process counts separately. That is fine for
    one small server; move to Redis if you ever run several instances.
    Every attempt counts, including ones that later fail validation.
    """

    def __init__(self, get_limit: Callable[[], int], window_seconds: int = 60):
        self._get_limit = get_limit
        self._window = window_seconds
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()

    def _prune(self, now: float) -> None:
        stale = [ip for ip, hits in self._hits.items() if not hits or now - hits[-1] >= self._window]
        for ip in stale:
            del self._hits[ip]

    def __call__(self, request: Request) -> None:
        # Behind a reverse proxy, run uvicorn with --forwarded-allow-ips so that
        # request.client is the visitor's real IP (see README).
        client_ip = request.client.host if request.client else "unknown"
        now = time.monotonic()
        limit = self._get_limit()

        with self._lock:
            if len(self._hits) > 10_000:
                self._prune(now)
            hits = self._hits.setdefault(client_ip, deque())
            while hits and now - hits[0] >= self._window:
                hits.popleft()
            if len(hits) >= limit:
                retry_after = int(self._window - (now - hits[0])) + 1
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests. Please wait a moment and try again.",
                    headers={"Retry-After": str(retry_after)},
                )
            hits.append(now)


refill_limiter = RateLimiter(lambda: settings.refill_rate_limit_per_minute)
login_limiter = RateLimiter(lambda: settings.login_rate_limit_per_minute)
