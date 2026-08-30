"""Small per-process sliding-window rate limiter for auth endpoints (M1.3).

Keyed by client IP (uvicorn --proxy-headers restores the real IP behind Caddy). Single portal
instance today; swap the store for Redis if the portal is ever scaled out (BACKLOG)."""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable

from fastapi import HTTPException, Request


class SlidingWindow:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str, limit: int, window_s: float, now: float | None = None) -> bool:
        now = now if now is not None else time.monotonic()
        with self._lock:
            q = self._hits[key]
            while q and q[0] <= now - window_s:
                q.popleft()
            if len(q) >= limit:
                return False
            q.append(now)
            return True

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


limiter = SlidingWindow()


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def rate_limited(name: str, limit: int, window_s: float) -> Callable[[Request], None]:
    def dependency(request: Request) -> None:
        if not limiter.allow(f"{name}:{client_ip(request)}", limit, window_s):
            raise HTTPException(
                status_code=429,
                detail="Too many attempts. Wait a while and try again.",
                headers={"Retry-After": str(int(window_s))},
            )

    return dependency
