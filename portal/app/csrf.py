"""Same-origin (CSRF) guard for state-changing POSTs, layered on the SameSite=lax session cookie.

The session cookie is `SameSite=lax`, so a cross-site POST does not carry it (baseline CSRF
defense). This adds a second check: when the browser sends an Origin/Referer, its host must equal
the request host — a cross-origin POST is rejected even if a cookie somehow rode along.
"""

from __future__ import annotations

from urllib.parse import urlparse

from fastapi import HTTPException, Request


def require_same_origin(request: Request) -> None:
    ref = request.headers.get("origin") or request.headers.get("referer") or ""
    host = request.headers.get("host", "")
    origin_host = urlparse(ref).netloc
    if origin_host and host and origin_host != host:
        raise HTTPException(status_code=403, detail="cross-origin request rejected")
