"""Centralized CSRF enforcement: exact-origin matcher, middleware behaviour, no-mutation-after-403,
non-cookie exemption, and a durable inventory that fails when a mutation route is unclassified."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import csrf
from app.config import get_settings
from app.csrf import _parse_origin, check_csrf
from app.db import get_engine
from app.models import Project, ProjectMember

PORTAL = "https://stage.chertiot.com"


@pytest.fixture
def portal_origin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "portal_public_url", PORTAL)


# ---- exact-origin parser ----
def test_parse_origin_effective_ports() -> None:
    assert _parse_origin("https://stage.chertiot.com") == ("https", "stage.chertiot.com", 443)
    assert _parse_origin("http://stage.chertiot.com") == ("http", "stage.chertiot.com", 80)
    assert _parse_origin("https://stage.chertiot.com:8443") == ("https", "stage.chertiot.com", 8443)


def test_parse_origin_malformed_is_none() -> None:
    for v in ["", "null", "not a url", "https://", "stage.chertiot.com", "https://a,https://b"]:
        assert _parse_origin(v) is None


REJECT = [
    "https://evil.example",
    "https://evil-stage.chertiot.com",  # prefix look-alike
    "https://stage.chertiot.com.evil.example",  # suffix look-alike
    "https://grafana.stage.chertiot.com",  # sibling subdomain
    "https://auth.stage.chertiot.com",  # sibling subdomain
    "http://stage.chertiot.com",  # wrong scheme
    "https://stage.chertiot.com:8443",  # wrong port
    "null",  # opaque origin
    "https://a.example, https://stage.chertiot.com",  # multiple values
]


@pytest.mark.parametrize("origin", REJECT)
def test_check_csrf_rejects_origin(portal_origin: None, origin: str) -> None:
    req = SimpleNamespace(headers={"origin": origin}, cookies={})
    with pytest.raises(HTTPException) as e:
        check_csrf(req)  # type: ignore[arg-type]
    assert e.value.status_code == 403


def test_check_csrf_accepts_exact_origin(portal_origin: None) -> None:
    check_csrf(SimpleNamespace(headers={"origin": PORTAL}, cookies={}))  # type: ignore[arg-type]


def test_check_csrf_referer_fallback(portal_origin: None) -> None:
    # Origin absent → Referer accepted only if it matches exactly
    check_csrf(SimpleNamespace(headers={"referer": PORTAL + "/projects/x"}, cookies={}))  # type: ignore[arg-type]
    with pytest.raises(HTTPException):
        check_csrf(SimpleNamespace(headers={"referer": "https://evil.example/x"}, cookies={}))  # type: ignore[arg-type]


def test_check_csrf_missing_origin_and_referer_rejected(portal_origin: None) -> None:
    with pytest.raises(HTTPException):
        check_csrf(SimpleNamespace(headers={}, cookies={}))  # type: ignore[arg-type]


# ---- middleware end-to-end + proof no mutation happens on 403 ----
def _seed_owner(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    called: list[int] = []
    monkeypatch.setattr("app.routers.projects.delete_project", lambda db, p, e: called.append(1))
    user = SimpleNamespace(id="u", email="o@x.io", role="student")
    monkeypatch.setattr("app.project.load_user", lambda request, db: user)
    with Session(get_engine()) as db:
        db.add_all(
            [
                Project(
                    id="pp",
                    slug="pp",
                    name="pp",
                    provisioning_state="provisioned",
                    tb_tenant_id="t",
                ),
                ProjectMember(
                    project_id="pp", user_id="u", role="owner", tb_user_id="tb", status="active"
                ),
            ]
        )
        db.commit()
    return called


def test_middleware_blocks_cross_origin_and_prevents_mutation(
    portal_origin: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    import app.main

    called = _seed_owner(monkeypatch)
    client = TestClient(app.main.app, follow_redirects=False)
    client.cookies.set("chertiot_session", "x")  # cookie-authenticated browser request
    # cross-origin cookie mutation → 403 at the middleware, delete_project NEVER called
    r = client.post("/projects/pp/delete", headers={"origin": "https://evil.example"})
    assert r.status_code == 403 and called == []
    # exact portal origin → passes CSRF, route runs, mutation happens (spy called), 303
    r = client.post("/projects/pp/delete", headers={"origin": PORTAL})
    assert r.status_code == 303 and called == [1]


def test_middleware_skips_requests_without_session_cookie(portal_origin: None) -> None:
    import app.main

    client = TestClient(app.main.app, follow_redirects=False)
    # no session cookie → CSRF not applicable; the route's own auth handles it (303 to /login)
    r = client.post("/projects/pp/delete", headers={"origin": "https://evil.example"})
    assert r.status_code == 303 and r.headers["location"].endswith("/login")


def test_internal_lab_token_is_not_csrf_eligible(portal_origin: None) -> None:
    import app.main

    client = TestClient(app.main.app, follow_redirects=False)
    # shared-secret API, no session cookie: CSRF middleware skips it (rejection here is the secret
    # gate, not CSRF) — a cross-origin header does not turn it into a CSRF 403 via the middleware
    r = client.post(
        "/internal/lab-token",
        json={"email": "x@y.io", "project_id": "p"},
        headers={"origin": "https://evil.example"},
    )
    assert r.status_code == 403  # its own secret check, reached because CSRF did not short-circuit


# ---- durable route inventory: every mutation route must be classified ----
COOKIE_MUTATIONS = {
    ("POST", "/signup"),
    ("POST", "/projects"),
    ("POST", "/projects/{project_id}/provision"),
    ("POST", "/projects/{project_id}/delete"),
    ("POST", "/projects/{project_id}/invite"),
    ("POST", "/projects/{project_id}/join"),
    ("POST", "/projects/{project_id}/requests/{req_id}/{decision}"),
    ("POST", "/projects/{project_id}/members/{member_id}/{action}"),
    ("POST", "/projects/{project_id}/devices"),
    ("POST", "/projects/{project_id}/devices/{device_id}/rename"),
    ("POST", "/projects/{project_id}/devices/{device_id}/revoke"),
    ("POST", "/projects/{project_id}/devices/{device_id}/delete"),
    ("POST", "/projects/{project_id}/dashboard/reset"),
    ("POST", "/projects/{project_id}/alerts"),
    ("POST", "/projects/{project_id}/alerts/{rule_id}/delete"),
    ("POST", "/projects/{project_id}/lora"),
    ("POST", "/projects/{project_id}/flows/start"),
    ("POST", "/projects/{project_id}/flows/stop"),
    ("POST", "/projects/{project_id}/monitoring/alarms/{alarm_id}/ack"),
    ("POST", "/teach/codes"),
    ("POST", "/teach/codes/{code}/deactivate"),
}
# Non-cookie APIs (shared-secret/bearer header) — documented as not CSRF-eligible.
EXEMPT_NON_COOKIE = {
    ("POST", "/internal/lab-token"),
}


def test_all_mutation_routes_are_classified() -> None:
    import app.main

    found: set[tuple[str, str]] = set()
    for route in app.main.app.routes:
        methods = getattr(route, "methods", None) or set()
        for m in methods & {"POST", "PUT", "PATCH", "DELETE"}:
            found.add((m, getattr(route, "path", "")))
    classified = COOKIE_MUTATIONS | EXEMPT_NON_COOKIE
    unclassified = found - classified
    assert not unclassified, (
        f"New cookie-authenticated mutation route(s) must be classified (CSRF-protected by the "
        f"central middleware) or explicitly exempted: {sorted(unclassified)}"
    )
    stale = classified - found
    assert not stale, f"Classified route(s) no longer exist — update the inventory: {sorted(stale)}"


def test_csrf_middleware_is_installed() -> None:
    assert any("csrf" in getattr(m, "__name__", str(m)).lower() for m in _middleware_names())
    assert csrf.SESSION_COOKIE == "chertiot_session"


def _middleware_names() -> list[Any]:
    import app.main

    names: list[Any] = []
    for m in app.main.app.user_middleware:
        fn = getattr(m, "kwargs", {}).get("dispatch") or getattr(m, "cls", None)
        names.append(fn)
    return names
