"""Register Keycloak as the OAuth2 provider in ThingsBoard (M0.3). Idempotent.

Mapper: BASIC, tenantNameStrategy=EMAIL, allowUserCreation → every Keycloak login lands in its own
tenant as TENANT_ADMIN (D4). Domain `app.<DOMAIN>` gets oauth2Enabled with this client linked.
Uses raw REST here; M0.4 folds this into portal/app/tb_client.py.
"""

from __future__ import annotations

import os
import sys
from typing import Any

import httpx

TB = os.environ.get("TB_ADMIN_URL", "http://localhost:8080").rstrip("/")
KC_PUBLIC = os.environ["KC_HOSTNAME"].rstrip("/")
KC_INTERNAL = os.environ["KC_INTERNAL_URL"].rstrip("/")
REALM = os.environ["KC_REALM"]
DOMAIN_NAME = f"app.{os.environ['DOMAIN']}"
CLIENT_TITLE = "Keycloak (CHERT IoT)"


def tb_client() -> httpx.Client:
    r = httpx.post(
        f"{TB}/api/auth/login",
        json={
            "username": os.environ["TB_SYSADMIN_EMAIL"],
            "password": os.environ["TB_SYSADMIN_PASSWORD"],
        },
        timeout=30,
    )
    r.raise_for_status()
    return httpx.Client(
        base_url=f"{TB}/api", headers={"X-Authorization": f"Bearer {r.json()['token']}"}, timeout=30
    )


def oauth2_client_rep(existing_id: dict[str, Any] | None) -> dict[str, Any]:
    rep: dict[str, Any] = {
        "title": CLIENT_TITLE,
        "clientId": "thingsboard",
        "clientSecret": os.environ["KC_SECRET_THINGSBOARD"],
        "authorizationUri": f"{KC_PUBLIC}/realms/{REALM}/protocol/openid-connect/auth",
        "accessTokenUri": f"{KC_INTERNAL}/realms/{REALM}/protocol/openid-connect/token",
        "userInfoUri": f"{KC_INTERNAL}/realms/{REALM}/protocol/openid-connect/userinfo",
        "jwkSetUri": f"{KC_INTERNAL}/realms/{REALM}/protocol/openid-connect/certs",
        "scope": ["openid", "email", "profile"],
        "userNameAttributeName": "email",
        "clientAuthenticationMethod": "POST",
        "loginButtonLabel": "Sign in with CHERT IoT",
        "loginButtonIcon": None,
        "platforms": ["WEB"],
        "mapperConfig": {
            "allowUserCreation": True,
            "activateUser": True,
            "type": "BASIC",
            "basic": {
                "emailAttributeKey": "email",
                "firstNameAttributeKey": "given_name",
                "lastNameAttributeKey": "family_name",
                "tenantNameStrategy": "EMAIL",
                "tenantNamePattern": None,
                "customerNamePattern": None,
                "defaultDashboardName": None,
                "alwaysFullScreen": False,
            },
        },
    }
    if existing_id:
        rep["id"] = existing_id
    return rep


def ensure_oauth2_client(c: httpx.Client) -> str:
    infos = c.get("/oauth2/client/infos", params={"pageSize": 100, "page": 0}).json()["data"]
    existing = next((i for i in infos if i["title"] == CLIENT_TITLE), None)
    rep = oauth2_client_rep(existing["id"] if existing else None)
    r = c.post("/oauth2/client", json=rep)
    r.raise_for_status()
    cid = r.json()["id"]["id"]
    print(f"tb oauth2 client '{CLIENT_TITLE}': {'updated' if existing else 'created'} ({cid})")
    return cid


def ensure_domain(c: httpx.Client, client_uuid: str) -> None:
    infos = c.get("/domain/infos", params={"pageSize": 100, "page": 0}).json()["data"]
    existing = next((d for d in infos if d["name"] == DOMAIN_NAME), None)
    rep: dict[str, Any] = {"name": DOMAIN_NAME, "oauth2Enabled": True, "propagateToEdge": False}
    if existing:
        rep["id"] = existing["id"]
    r = c.post("/domain", json=rep)
    r.raise_for_status()
    did = r.json()["id"]["id"]
    c.put(f"/domain/{did}/oauth2Clients", json=[client_uuid]).raise_for_status()
    print(f"tb domain {DOMAIN_NAME}: {'updated' if existing else 'created'}, oauth2 client linked")


def main() -> int:
    c = tb_client()
    cid = ensure_oauth2_client(c)
    ensure_domain(c, cid)
    return 0


if __name__ == "__main__":
    sys.exit(main())
