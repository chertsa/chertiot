"""M1.1 acceptance: signup → verification email (Mailpit) → verify → Keycloak login → portal
home with own TB tenant, starter dashboard and device; one login reaches portal AND TB; drift
repaired."""

import os
import re
import time
import uuid

import httpx
import pytest

from app.tb_client import TbClient
from tests.e2e.conftest import make_client

MAILPIT = os.environ.get("MAILPIT_API", "http://127.0.0.1:18025")
TB_ADMIN = os.environ.get("TB_ADMIN_URL", "http://127.0.0.1:18080")


def mailpit_link(email: str, pattern: str, timeout: float = 20) -> str:
    deadline = time.time() + timeout
    while time.time() < deadline:
        msgs = httpx.get(
            f"{MAILPIT}/api/v1/search", params={"query": f"to:{email}"}, timeout=10
        ).json()
        for m in msgs.get("messages", []):
            body = httpx.get(f"{MAILPIT}/api/v1/message/{m['ID']}", timeout=10).json()
            text = (body.get("Text") or "") + (body.get("HTML") or "")
            found = re.search(pattern, text.replace("&amp;", "&"))
            if found:
                return found.group(0)
        time.sleep(1)
    raise AssertionError(f"no email matching {pattern!r} for {email} within {timeout}s")


def _abs(r: httpx.Response) -> str:
    return str(r.url.join(r.headers["location"]))


def follow(s: httpx.Client, r: httpx.Response, limit: int = 8) -> httpx.Response:
    while r.status_code in (301, 302, 303, 307) and limit:
        r = s.get(_abs(r))
        limit -= 1
    return r


def keycloak_login(s: httpx.Client, start_url: str, email: str, password: str) -> httpx.Response:
    """Follow redirects from a portal /login to Keycloak, submit the form, return the response of
    the first request back on the portal (the /auth/callback result)."""
    r = s.get(start_url)
    hops = 0
    while r.status_code in (302, 303) and hops < 8:
        location = _abs(r)
        if "/auth/callback" in location:
            return s.get(location)  # SSO: Keycloak session still valid, no form shown
        r = s.get(location)
        hops += 1
    form = re.search(r'action="([^"]+)"', r.text)
    assert form, r.text[:300]
    r = s.post(form.group(1).replace("&amp;", "&"), data={"username": email, "password": password})
    assert r.status_code in (302, 303), r.text[:500]
    return s.get(_abs(r))  # portal /auth/callback


@pytest.fixture
def sysadmin() -> TbClient:
    return TbClient(
        TB_ADMIN,
        username=os.environ["TB_SYSADMIN_EMAIL"],
        password=os.environ["TB_SYSADMIN_PASSWORD"],
    )


def test_signup_to_live_lab(kc_url: str, tb_url: str, sysadmin: TbClient) -> None:
    portal = os.environ.get("PORTAL_PUBLIC_URL", "http://localhost")
    email = f"e2e-{uuid.uuid4().hex[:8]}@test.chertiot.local"
    password = "correct-horse-battery-staple"  # noqa: S105

    with make_client(follow_redirects=False) as s:
        # 1. Sign up.
        r = s.post(
            f"{portal}/signup",
            data={
                "email": email,
                "password": password,
                "password_confirm": password,
                "age_attested": "yes",
                "first_name": "E2E",
            },
        )
        assert r.status_code == 303, r.text[:500]
        assert "/signup/check-email" in r.headers["location"]

        # 2. Verification email → click link (Keycloak action token) → lands on /auth/verified.
        link = mailpit_link(
            email, r"https?://auth\.localhost/realms/chertiot/login-actions/action-token[^\s\"<]+"
        )
        r = follow(s, s.get(link))
        if "Click here to proceed" in r.text:
            # Keycloak's interstitial when the link is opened outside the originating browser
            # session (mail clients do this) — the user clicks "proceed", so do we.
            proceed = re.findall(r'href="(http[^"]*action-token[^"]*)"', r.text)[-1]
            r = follow(s, s.get(proceed.replace("&amp;", "&")))
        if "Back to Application" in r.text:
            # Keycloak's "Your account has been updated" page links back to redirect_uri.
            back = re.findall(r'href="(http[^"]+/auth/verified[^"]*)"', r.text)[-1]
            r = follow(s, s.get(back.replace("&amp;", "&")))
        assert r.status_code == 200 and "Email verified" in r.text, (r.status_code, r.text[:300])

        # 3. Sign in once via Keycloak → portal callback provisions → /home.
        r = keycloak_login(s, f"{portal}/login", email, password)
        assert r.status_code == 303 and r.headers["location"] == "/home", (
            r.status_code,
            r.text[:300],
        )
        r = s.get(f"{portal}/home")
        assert r.status_code == 200 and "/dashboards/" in r.text and "1 device" in r.text
        r = s.get(f"{portal}/devices")
        assert r.status_code == 200 and "my-first-device" in r.text
        device_path = re.search(r'href="(/devices/[0-9a-f-]+)"', r.text)
        assert device_path
        r = s.get(f"{portal}{device_path.group(1)}")
        token = re.search(r"data-device-token>([^<]+)<", r.text)
        assert token, "device token missing on device page"

        # 4. The same login reaches ThingsBoard (no second credential prompt): TB's OAuth2 flow
        #    to the already-authenticated Keycloak session yields a TB token immediately.
        clients = s.post(f"{tb_url}/api/noauth/oauth2Clients", params={"platform": "WEB"}).json()
        r = s.get(f"{tb_url}{clients[0]['url']}")
        hops = 0
        while (
            r.status_code in (302, 303)
            and "accessToken=" not in r.headers.get("location", "")
            and hops < 6
        ):
            r = s.get(r.headers["location"])
            hops += 1
        assert "accessToken=" in r.headers.get("location", ""), (r.status_code, r.text[:300])

        # 5. TB state: own tenant, starter dashboard + device, quotas profile.
        tenant = sysadmin.find_tenant(email)
        assert tenant and tenant.id
        profile = sysadmin.find_tenant_profile("chertiot-student")
        assert profile and tenant.tenant_profile_id == profile.id
        user = sysadmin.find_tenant_user(tenant.id.id, email)
        assert user and user.id and user.authority == "TENANT_ADMIN"
        as_student = sysadmin.impersonate(user.id.id)
        devices = as_student.list_devices()
        assert [d.name for d in devices] == ["my-first-device"]
        assert as_student.find_dashboard("My devices") is not None

        # 6. Drift repair: device deleted behind our back → next portal visit recreates it.
        as_student.delete_device(devices[0].id.id)  # type: ignore[union-attr]
        r = keycloak_login(s, f"{portal}/login", email, password)  # SSO: no form → fine either way
        assert r.status_code == 303
        assert any(d.name == "my-first-device" for d in as_student.list_devices())

    # cleanup
    sysadmin.delete_tenant(tenant.id.id)
