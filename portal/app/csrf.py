"""Centralized CSRF enforcement for cookie-authenticated browser mutations.

The portal session cookie is scoped to the parent domain (`.chertiot.com`) so it reaches sibling
subdomains, and `SameSite=Lax` is decided by the *registrable site* (chertiot.com), not the exact
origin. Neither is sufficient CSRF protection: a compromised or hostile sibling subdomain under
chertiot.com could submit an authenticated mutation. So every cookie-authenticated state-changing
request (POST/PUT/PATCH/DELETE carrying the session cookie) must prove it originates from the portal
itself, by an **exact** origin match — scheme + hostname + effective port — never substring/prefix/
suffix. Enforcement runs in middleware, before any route logic, and returns 403 on failure.

Policy (documented):
  * The request MUST carry an `Origin` header exactly equal to the configured portal origin.
  * If `Origin` is absent, `Referer` is accepted as the same exact match (browsers send Referer for
    same-origin requests under our `Referrer-Policy: same-origin`).
  * A missing/empty/malformed/multi-valued `Origin` — or, when `Origin` is absent, a missing or
    malformed `Referer` — is REJECTED.
Non-cookie APIs (shared-secret/bearer header, e.g. /internal/lab-token) carry no session cookie and
are therefore not CSRF-eligible; the middleware skips them (see is_cookie_authenticated).
"""

from __future__ import annotations

from urllib.parse import urlsplit

from fastapi import HTTPException, Request

from app.config import get_settings

SESSION_COOKIE = "chertiot_session"
_DEFAULT_PORTS = {"http": 80, "https": 443}

Origin = tuple[str, str, int]


def _parse_origin(value: str) -> Origin | None:
    """Parse a scheme://host[:port] value into (scheme, host, effective_port), or None if malformed
    or not an absolute origin. A comma/whitespace inside means multiple/garbled values → None."""
    v = (value or "").strip()
    if not v or "," in v or " " in v:
        return None
    try:
        p = urlsplit(v)
        host = p.hostname
        port = p.port  # raises ValueError on a bad port
    except ValueError:
        return None
    if not p.scheme or not host:
        return None
    scheme = p.scheme.lower()
    return (scheme, host.lower(), port or _DEFAULT_PORTS.get(scheme, 0))


def configured_origin() -> Origin | None:
    return _parse_origin(get_settings().portal_public_url)


def is_cookie_authenticated(request: Request) -> bool:
    """True when the request carries the portal session cookie (a browser-authenticated call)."""
    return SESSION_COOKIE in request.cookies


def check_csrf(request: Request) -> None:
    """Raise HTTPException(403) unless the request's Origin (or Referer fallback) exactly matches
    the configured portal origin. Call only for cookie-authenticated mutations."""
    expected = configured_origin()
    if expected is None:  # misconfiguration → fail closed
        raise HTTPException(status_code=403, detail="cross-origin request rejected")
    origin = request.headers.get("origin")
    if origin is not None:
        if _parse_origin(origin) != expected:
            raise HTTPException(status_code=403, detail="cross-origin request rejected")
        return
    referer = request.headers.get("referer")
    if referer is None or _parse_origin(referer) != expected:
        raise HTTPException(status_code=403, detail="cross-origin request rejected")
