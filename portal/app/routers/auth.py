from datetime import UTC, datetime
from typing import Any

from authlib.integrations.base_client.errors import OAuthError
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import audit
from app.auth import oauth
from app.config import get_settings
from app.db import get_db
from app.models import PortalUser
from app.onboarding import ensure_provisioned
from app.ratelimit import rate_limited
from app.templating import templates

router = APIRouter()


@router.get("/login", dependencies=[Depends(rate_limited("login", 30, 60))])
async def login(request: Request) -> Any:
    s = get_settings()
    return await oauth.keycloak.authorize_redirect(request, f"{s.portal_public_url}/auth/callback")


@router.get("/auth/callback", dependencies=[Depends(rate_limited("callback", 30, 60))])
async def callback(request: Request, db: Session = Depends(get_db)) -> Any:
    try:
        token = await oauth.keycloak.authorize_access_token(request)
    except OAuthError as e:
        # Stale/replayed state (back button, double click, expired session): start over cleanly.
        request.session.pop("user", None)
        return RedirectResponse(f"/login?reason={e.error}", status_code=303)
    claims = token.get("userinfo") or {}
    email = str(claims.get("email", "")).lower()
    sub = str(claims.get("sub", ""))
    if not email or not sub:
        return templates.TemplateResponse(
            request,
            "error.html",
            {"title": "Sign-in failed", "message": "No email in identity token."},
            status_code=400,
        )
    if not claims.get("email_verified"):
        return templates.TemplateResponse(
            request,
            "error.html",
            {
                "title": "Verify your email first",
                "message": f"We sent a verification link to {email}.",
            },
            status_code=403,
        )
    user = db.scalar(select(PortalUser).where(PortalUser.kc_user_id == sub)) or db.scalar(
        select(PortalUser).where(PortalUser.email == email)
    )
    if user is None:
        # Account created outside the portal (Keycloak admin, future self-registration): adopt it.
        user = PortalUser(email=email, kc_user_id=sub, cohort="community")
        db.add(user)
        audit(db, email, "user.adopted")
    user.kc_user_id = user.kc_user_id or sub
    user.last_login_at = datetime.now(UTC)
    db.commit()
    request.session["user"] = {"sub": sub, "email": email, "name": claims.get("name") or email}
    request.session["id_token"] = token.get("id_token")
    audit(db, email, "login")
    ensure_provisioned(db, user)  # idempotent; failures are recorded, not raised
    return RedirectResponse("/home", status_code=303)


@router.get("/auth/verified")
def verified(request: Request) -> Any:
    return templates.TemplateResponse(request, "verified.html")


@router.get("/logout")
def logout(request: Request) -> Any:
    s = get_settings()
    id_token = request.session.pop("id_token", None)
    request.session.clear()
    params = f"post_logout_redirect_uri={s.portal_public_url}/&client_id=portal"
    if id_token:
        params += f"&id_token_hint={id_token}"
    return RedirectResponse(
        f"{s.kc_issuer}/protocol/openid-connect/logout?{params}", status_code=303
    )
