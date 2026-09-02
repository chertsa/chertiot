"""M3.1 acceptance over the internet: spawn a Node-RED instance through the portal, reach the
editor with the owner's session, and prove another authenticated user is rejected (403).

    ENV_BASE=stage.chertiot.com uv run python -m scripts.flows_smoke
"""

from __future__ import annotations

import os
import re
import sys
import time
import uuid

import httpx

BASE = os.environ.get("ENV_BASE", "stage.chertiot.com")
PORTAL, AUTH, FLOWS = f"https://{BASE}", f"https://auth.{BASE}", f"https://flows.{BASE}"


def check(name: str, cond: bool, detail: str = "") -> bool:
    print(f"  {'✓' if cond else '✗ FAIL'} {name} {detail}")
    return cond


def portal_login(kc, email: str, password: str) -> httpx.Client:  # noqa: ANN001
    uid = kc.create_user(email, password, first_name="Flow")
    kc._req("PUT", f"/users/{uid}", json={"emailVerified": True, "requiredActions": []})
    s = httpx.Client(follow_redirects=False, timeout=40)
    r = s.get(f"{PORTAL}/login")
    hops = 0
    while r.status_code in (302, 303) and hops < 8:
        loc = str(httpx.URL(str(r.url)).join(r.headers["location"]))
        if "/auth/callback" in loc:
            r = s.get(loc)
            break
        r = s.get(loc)
        hops += 1
        if r.status_code == 200 and "login-actions/authenticate" in r.text:
            action = re.search(r'action="([^"]+)"', r.text)
            if action is None:
                raise RuntimeError("Keycloak login form not found")
            r = s.post(
                action.group(1).replace("&amp;", "&"),
                data={"username": email, "password": password},
            )
    while r.status_code in (302, 303):
        r = s.get(str(httpx.URL(str(r.url)).join(r.headers["location"])))
    return s


def main() -> int:
    os.environ.setdefault("KC_INTERNAL_URL", AUTH)
    os.environ.setdefault("KC_HOSTNAME", AUTH)
    from app.keycloak_admin import KeycloakAdmin  # noqa: E402

    kc = KeycloakAdmin()
    ok = True
    email_a = f"flow-a-{uuid.uuid4().hex[:6]}@test.chertiot.local"
    email_b = f"flow-b-{uuid.uuid4().hex[:6]}@test.chertiot.local"
    pw = "flows-" + uuid.uuid4().hex  # noqa: S105

    a = portal_login(kc, email_a, pw)
    r = a.get(f"{PORTAL}/flows")
    ok &= check(
        "flows page",
        r.status_code == 200 and ("Start my Node-RED" in r.text or "Open the editor" in r.text),
    )
    r = a.post(f"{PORTAL}/flows/start")
    ok &= check("spawn", r.status_code == 303, str(r.status_code))
    uid_a = re.search(r"/u/([0-9a-f-]+)/", a.get(f"{PORTAL}/flows").text)
    ok &= check("editor url on page", bool(uid_a))
    if not uid_a:
        return 1
    editor = f"{FLOWS}/u/{uid_a.group(1)}/"
    deadline = time.time() + 90
    code, body = 0, ""
    while time.time() < deadline:
        rr = a.get(editor, follow_redirects=True)
        code, body = rr.status_code, rr.text
        if code == 200 and "Node-RED" in body:
            break
        time.sleep(5)
    ok &= check("editor reachable by owner", code == 200 and "Node-RED" in body, str(code))

    b = portal_login(kc, email_b, pw)
    rb = b.get(editor)
    ok &= check("other user rejected", rb.status_code == 403, str(rb.status_code))
    anon = httpx.get(editor, timeout=30)
    ok &= check("anonymous rejected", anon.status_code in (401, 403), str(anon.status_code))

    a.post(f"{PORTAL}/flows/stop")
    print("== PASS" if ok else "== FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
