from typing import Any
from urllib.parse import quote, urlparse

import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.auth import optional_user
from app.config import get_settings
from app.db import get_db
from app.onboarding import ensure_provisioned
from app.student import as_student, load_user
from app.templating import templates

router = APIRouter()

# TB's OAuth2 authorization URL (…/oauth2/authorization/<id>), resolved once and cached.
# Routing "Open my dashboard" through it means students land via Keycloak SSO instead of TB's
# own login form (where a password attempt fails with "User account is not active" — D3, SSO-only).
_tb_sso_base: str | None = None


def _sso_authorization_url(s: Any) -> str | None:
    global _tb_sso_base
    if _tb_sso_base:
        return _tb_sso_base
    # TB only lists the client when the request Host matches its Domain record (app.<domain>).
    host = urlparse(s.tb_public_url).hostname
    try:
        r = httpx.post(
            f"{s.tb_admin_url}/api/noauth/oauth2Clients",
            json={},
            headers={"Host": host} if host else {},
            timeout=5,
        )
        clients = r.json() if r.status_code == 200 else []
        if clients:
            _tb_sso_base = f"{s.tb_public_url}{clients[0]['url']}"
    except Exception:
        _tb_sso_base = None
    return _tb_sso_base


@router.get("/lang/{code}")
def set_language(code: str, request: Request) -> Any:
    """Language toggle (Design System §7). Cookie-based; falls back to Accept-Language."""
    target = request.headers.get("referer") or "/"
    resp = RedirectResponse(target, status_code=303)
    if code in ("en", "ar"):
        resp.set_cookie("lang", code, max_age=365 * 24 * 3600, samesite="lax")
    return resp


@router.get("/")
def index(request: Request) -> Any:
    if optional_user(request):
        return RedirectResponse("/home", status_code=303)
    return templates.TemplateResponse(request, "index.html")


@router.get("/home")
def home(request: Request, db: Session = Depends(get_db)) -> Any:
    user = load_user(request, db)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    s = get_settings()
    dash_path = "/dashboards"
    device_count = 0
    if user.provisioning_state == "provisioned" and user.tb_user_id:
        with as_student(user) as (_sysadmin, student):
            device_count = len(student.list_devices())
            dash = student.find_dashboard("My devices")
            if dash and dash.id:
                dash_path = f"/dashboards/{dash.id.id}"
    sso = _sso_authorization_url(s)
    dashboard_url = (
        f"{sso}?prevUri={quote(dash_path, safe='')}" if sso else f"{s.tb_public_url}{dash_path}"
    )
    ctx = {"user": user, "device_count": device_count, "dashboard_url": dashboard_url}
    return templates.TemplateResponse(request, "home.html", ctx)


@router.post("/home/provision")
def retry_provision(request: Request, db: Session = Depends(get_db)) -> Any:
    user = load_user(request, db)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    ensure_provisioned(db, user)
    return RedirectResponse("/home", status_code=303)
