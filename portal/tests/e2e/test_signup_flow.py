"""Acceptance (D13 project-centric): signup → verification email (Mailpit) → verify → Keycloak
login → portal home is the projects portfolio → create a project (provisions its own TB tenant,
owner as Tenant Admin, starter dashboard) → add a device; one login reaches portal AND TB;
provisioning is idempotent."""

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
PORTAL = os.environ.get("PORTAL_PUBLIC_URL", "http://localhost")


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


def signup(s: httpx.Client, email: str, password: str, first_name: str = "E2E") -> None:
    r = s.post(
        f"{PORTAL}/signup",
        data={
            "email": email,
            "password": password,
            "password_confirm": password,
            "age_attested": "yes",
            "first_name": first_name,
        },
    )
    assert r.status_code == 303 and "/signup/check-email" in r.headers["location"], r.text[:500]


def verify_email(s: httpx.Client, email: str) -> None:
    link = mailpit_link(
        email, r"https?://auth\.localhost/realms/chertiot/login-actions/action-token[^\s\"<]+"
    )
    r = follow(s, s.get(link))
    if (
        "Click here to proceed" in r.text
    ):  # interstitial when opened outside the originating session
        proceed = re.findall(r'href="(http[^"]*action-token[^"]*)"', r.text)[-1]
        r = follow(s, s.get(proceed.replace("&amp;", "&")))
    if "Back to Application" in r.text:  # "account updated" page links back to redirect_uri
        back = re.findall(r'href="(http[^"]+/auth/verified[^"]*)"', r.text)[-1]
        r = follow(s, s.get(back.replace("&amp;", "&")))
    assert r.status_code == 200 and "Email verified" in r.text, (r.status_code, r.text[:300])


def signup_verify_login(s: httpx.Client, email: str, password: str) -> None:
    """Full onboarding to a landed session on the portal home (the projects portfolio)."""
    signup(s, email, password)
    verify_email(s, email)
    r = keycloak_login(s, f"{PORTAL}/login", email, password)
    assert r.status_code == 303 and r.headers["location"] == "/home", (r.status_code, r.text[:300])


def create_project(s: httpx.Client, name: str, description: str = "") -> str:
    """Create a project via the portal; returns its id. Provisioning is synchronous (D13)."""
    r = s.post(f"{PORTAL}/projects", data={"name": name, "description": description})
    assert r.status_code == 303 and r.headers["location"].startswith("/projects/"), r.text[:300]
    return r.headers["location"].split("/projects/", 1)[1]


def first_tenant_admin(sysadmin: TbClient, tenant_id: str) -> str:
    """The id of the first TENANT_ADMIN user in a tenant (via the sysadmin tenant-users list)."""
    data = sysadmin._get(f"/tenant/{tenant_id}/users", pageSize=50, page=0)  # noqa: SLF001
    for u in data.get("data", []) if isinstance(data, dict) else []:
        if u.get("authority") == "TENANT_ADMIN":
            return u["id"]["id"]
    raise AssertionError(f"no TENANT_ADMIN user in tenant {tenant_id}")


@pytest.fixture
def sysadmin() -> TbClient:
    return TbClient(
        TB_ADMIN,
        username=os.environ["TB_SYSADMIN_EMAIL"],
        password=os.environ["TB_SYSADMIN_PASSWORD"],
    )


def test_signup_to_project_workspace(kc_url: str, tb_url: str, sysadmin: TbClient) -> None:
    email = f"e2e-{uuid.uuid4().hex[:8]}@test.chertiot.local"
    password = "correct-horse-battery-staple"  # noqa: S105
    pname = f"E2E Greenhouse {uuid.uuid4().hex[:6]}"

    with make_client(follow_redirects=False) as s:
        # 1. Signup → verify → login lands on the projects portfolio (no per-user tenant, D13).
        signup_verify_login(s, email, password)
        r = s.get(f"{PORTAL}/home")
        assert (
            r.status_code == 200
            and "My projects" in r.text
            and "Start your first project" in r.text
        )

        # 2. Create a project → its workspace is provisioned (own TB tenant + starter dashboard).
        pid = create_project(s, pname, "greenhouse")
        r = s.get(f"{PORTAL}/projects/{pid}")
        assert r.status_code == 200 and pname in r.text and "Setup failed" not in r.text

        # 3. Add a device inside the project (project-scoped route).
        r = s.post(f"{PORTAL}/projects/{pid}/devices", data={"name": "my-first-device"})
        assert r.status_code == 303 and r.headers["location"].startswith(
            f"/projects/{pid}/devices/"
        ), r.text[:300]
        device_url = f"{PORTAL}{r.headers['location']}"
        r = s.get(device_url)
        assert r.status_code == 200 and "my-first-device" in r.text
        assert re.search(r"data-device-token>([^<]+)<", r.text), "device token missing"
        r = s.get(f"{PORTAL}/projects/{pid}/devices")
        assert r.status_code == 200 and "my-first-device" in r.text and "devices used" in r.text

        # 4. TB state: the project has its own tenant on the student profile, owner is TENANT_ADMIN,
        #    starter dashboard present, and the device landed in that tenant.
        tenant = sysadmin.find_tenant(pname)
        assert tenant and tenant.id
        profile = sysadmin.find_tenant_profile("chertiot-student")
        assert profile and tenant.tenant_profile_id == profile.id
        owner = sysadmin.impersonate(first_tenant_admin(sysadmin, tenant.id.id))
        try:
            assert owner.find_dashboard("My devices") is not None
            assert [d.name for d in owner.list_devices()] == ["my-first-device"]
        finally:
            owner.close()

        # 5. The same login reaches ThingsBoard (no second credential prompt).
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

        # 6. Provisioning is idempotent: re-provision keeps the project provisioned and the device.
        r = s.post(f"{PORTAL}/projects/{pid}/provision")
        assert r.status_code == 303
        r = s.get(f"{PORTAL}/projects/{pid}")
        assert r.status_code == 200 and "Setup failed" not in r.text
        r = s.get(f"{PORTAL}/projects/{pid}/devices")
        assert "my-first-device" in r.text

    sysadmin.delete_tenant(tenant.id.id)  # cleanup
