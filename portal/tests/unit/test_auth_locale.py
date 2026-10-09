"""Sign-in follows the portal language (v2.0.1).

The portal is the single source of truth for the UI language: /login hands it to Keycloak as the
OIDC `ui_locales` parameter, and the Keycloak page's language pill switches *through* the portal
(/lang/<code>?next=/login), so chertiot.com and the sign-in pages never disagree.
"""

from pathlib import Path
from typing import Any

import pytest
from fastapi.responses import RedirectResponse
from fastapi.testclient import TestClient

from app.auth import configure_oauth, oauth
from app.main import app

REPO = Path(__file__).resolve().parents[3]
TEMPLATE = REPO / "keycloak" / "theme" / "chertiot" / "login" / "template.ftl"


@pytest.mark.parametrize("lang", ["en", "ar"])
def test_login_passes_portal_language_to_keycloak(
    monkeypatch: pytest.MonkeyPatch, lang: str
) -> None:
    seen: dict[str, Any] = {}
    if "keycloak" not in oauth._registry:  # registered at app startup; no network until used
        configure_oauth()

    async def fake_authorize_redirect(request: Any, redirect_uri: str, **kw: Any) -> Any:
        seen.update(kw)
        return RedirectResponse("https://auth.example/realms/chertiot/auth", status_code=302)

    monkeypatch.setattr(oauth.keycloak, "authorize_redirect", fake_authorize_redirect)
    c = TestClient(app, follow_redirects=False)
    c.cookies.set("lang", lang)
    r = c.get("/login")
    assert r.status_code == 302
    assert seen.get("ui_locales") == lang


def test_lang_toggle_returns_to_next_path() -> None:
    c = TestClient(app, follow_redirects=False)
    r = c.get("/lang/ar", params={"next": "/login"}, headers={"referer": "/home"})
    assert r.status_code == 303 and r.headers["location"] == "/login"
    assert "lang=ar" in r.headers.get("set-cookie", "")


@pytest.mark.parametrize("bad", ["https://evil.example/", "//evil.example/x", "/\\evil.example"])
def test_lang_toggle_rejects_offsite_next(bad: str) -> None:
    c = TestClient(app, follow_redirects=False)
    r = c.get("/lang/en", params={"next": bad}, headers={"referer": "/home"})
    assert r.status_code == 303 and r.headers["location"] == "/home"


def test_keycloak_language_pill_routes_through_portal() -> None:
    ftl = TEMPLATE.read_text("utf-8")
    assert "login-select-toggle" not in ftl  # the stock <select> is replaced by the CHERT pill
    assert "/lang/${l.languageTag}?next=/login" in ftl
    assert 'pageId == "login" || pageId == "login-reset-password"' in ftl
