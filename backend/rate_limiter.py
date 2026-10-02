import threading
import time
from collections import defaultdict, deque
from typing import DefaultDict, Deque

from fastapi import HTTPException, Request


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._requests: DefaultDict[str, Deque[float]] = defaultdict(deque)

    def check(self, key: str, *, limit: int, window_seconds: int) -> None:
        if limit <= 0:
            return
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            bucket = self._requests[key]
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if len(bucket) >= limit:
                raise HTTPException(429, "Too many requests. Please try again shortly.")
            bucket.append(now)


RATE_LIMITER = InMemoryRateLimiter()


def enforce_rate_limit(request: Request | None, *, name: str, limit: int, window_seconds: int = 60) -> None:
    if request is None or not hasattr(request, "client"):
        return
    if not request.client:
        key = name
    else:
        key = f"{name}:{request.client.host}"
    RATE_LIMITER.check(key, limit=limit, window_seconds=window_seconds)
