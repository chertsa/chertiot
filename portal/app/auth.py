"""OIDC login against Keycloak (D3). Session = signed cookie holding {sub, email, name}."""

from __future__ import annotations

from typing import Any

from authlib.integrations.starlette_client import OAuth
from fastapi import HTTPException, Request, status

from app.config import Settings, get_settings

oauth = OAuth()


def configure_oauth(settings: Settings | None = None) -> None:
    s = settings or get_settings()
    oauth.register(
        name="keycloak",
        client_id="portal",
        client_secret=s.kc_secret_portal,
        server_metadata_url=f"{s.kc_issuer}/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )


def current_user(request: Request) -> dict[str, Any]:
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="login required")
    return dict(user)


def optional_user(request: Request) -> dict[str, Any] | None:
    user = request.session.get("user")
    return dict(user) if user else None
