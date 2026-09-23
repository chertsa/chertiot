"""Idempotent Keycloak realm setup for CHERT IoT (M0.3).

Creates/updates realm `KC_REALM`, its OIDC clients (thingsboard, portal, jupyterhub, grafana),
the CHERT IoT login theme, SMTP (if configured) and — in ENV=dev only — a test user.
Safe to rerun. Source of truth for the realm; keycloak/realm/*.json is an export artifact.
"""

from __future__ import annotations

import os
import sys
from typing import Any

import httpx

from scripts.kc_roles import PLATFORM_ROLES, REALM, admin_client

ENV = os.environ.get("ENV", "dev")
TB_URL = os.environ["TB_PUBLIC_URL"].rstrip("/")
PORTAL_URL = os.environ["PORTAL_PUBLIC_URL"].rstrip("/")
DOMAIN = os.environ["DOMAIN"]
SCHEME = "http" if ENV == "dev" else "https"

CLIENTS: dict[str, dict[str, Any]] = {
    "thingsboard": {
        "secret": os.environ["KC_SECRET_THINGSBOARD"],
        "redirectUris": [f"{TB_URL}/login/oauth2/code/*"],
        "webOrigins": [TB_URL],
    },
    "portal": {
        "secret": os.environ["KC_SECRET_PORTAL"],
        "redirectUris": [f"{PORTAL_URL}/auth/callback", f"{PORTAL_URL}/auth/verified"],
        "webOrigins": [PORTAL_URL],
        # The portal creates users and triggers verification mails through the admin API using
        # its service account (least privilege: user management only, never realm admin).
        "serviceAccount": True,
        "realmManagementRoles": ["manage-users", "view-users", "query-users"],
    },
    "jupyterhub": {
        "secret": os.environ["KC_SECRET_JUPYTERHUB"],
        "redirectUris": [f"{SCHEME}://lab.{DOMAIN}/hub/oauth_callback"],
        "webOrigins": [f"{SCHEME}://lab.{DOMAIN}"],
    },
    "grafana": {
        "secret": os.environ["KC_SECRET_GRAFANA"],
        "redirectUris": [f"{SCHEME}://grafana.{DOMAIN}/login/generic_oauth"],
        "webOrigins": [f"{SCHEME}://grafana.{DOMAIN}"],
        # Emit the user's realm roles as a `roles` claim (userinfo + tokens) so Grafana's OAuth can
        # gate access by role (platform-admin/platform-instructor) with role_attribute_strict — a
        # student with no platform role is denied a Grafana session, not just the portal link.
        "mappers": [
            {
                "name": "realm roles",
                "protocol": "openid-connect",
                "protocolMapper": "oidc-usermodel-realm-role-mapper",
                "config": {
                    "claim.name": "roles",
                    "jsonType.label": "String",
                    "multivalued": "true",
                    "userinfo.token.claim": "true",
                    "access.token.claim": "true",
                    "id.token.claim": "false",
                },
            }
        ],
    },
}


def realm_representation() -> dict[str, Any]:
    rep: dict[str, Any] = {
        "realm": REALM,
        "enabled": True,
        "displayName": "CHERT IoT",
        "displayNameHtml": "CHERT IoT",
        "loginTheme": "chertiot",
        "emailTheme": "keycloak",
        "registrationAllowed": False,  # M1.1 decides self-registration vs portal-driven
        "registrationEmailAsUsername": True,
        "loginWithEmailAllowed": True,
        "duplicateEmailsAllowed": False,
        "verifyEmail": bool(os.environ.get("SMTP_HOST")),
        "resetPasswordAllowed": True,
        "rememberMe": True,
        "bruteForceProtected": True,
        "sslRequired": "none" if ENV == "dev" else "external",
        "ssoSessionIdleTimeout": 8 * 3600,
        "ssoSessionMaxLifespan": 24 * 3600,
        "accessTokenLifespan": 900,
        "internationalizationEnabled": True,
        "supportedLocales": ["en", "ar"],
        "defaultLocale": "en",
    }
    if os.environ.get("SMTP_HOST"):
        rep["smtpServer"] = {
            "host": os.environ["SMTP_HOST"],
            "port": os.environ.get("SMTP_PORT", "587"),
            "from": os.environ["SMTP_FROM"],
            "fromDisplayName": "CHERT IoT",
            "starttls": os.environ.get("SMTP_STARTTLS", "true"),
            "auth": "true" if os.environ.get("SMTP_USER") else "false",
            "user": os.environ.get("SMTP_USER", ""),
            "password": os.environ.get("SMTP_PASSWORD", ""),
        }
    return rep


def ensure_realm(c: httpx.Client) -> None:
    rep = realm_representation()
    r = c.get(f"/{REALM}")
    if r.status_code == 404:
        c.post("", json=rep).raise_for_status()
        print(f"realm {REALM}: created")
    else:
        r.raise_for_status()
        c.put(f"/{REALM}", json=rep).raise_for_status()
        print(f"realm {REALM}: updated")


def ensure_client(c: httpx.Client, client_id: str, spec: dict[str, Any]) -> None:
    rep = {
        "clientId": client_id,
        "name": f"CHERT IoT {client_id}",
        "protocol": "openid-connect",
        "publicClient": False,
        "standardFlowEnabled": True,
        "directAccessGrantsEnabled": False,
        "serviceAccountsEnabled": bool(spec.get("serviceAccount")),
        "secret": spec["secret"],
        "redirectUris": spec["redirectUris"],
        "webOrigins": spec["webOrigins"],
        # "+" allows the client's redirect URIs; also allow its root so a post-logout landing on
        # the app home (portal → https://chertiot.com/) is accepted, not "Invalid redirect uri".
        "attributes": {"post.logout.redirect.uris": "+##" + spec["webOrigins"][0] + "/"},
    }
    existing = c.get(f"/{REALM}/clients", params={"clientId": client_id}).json()
    if existing:
        internal_id = existing[0]["id"]
        c.put(f"/{REALM}/clients/{internal_id}", json=rep).raise_for_status()
        print(f"client {client_id}: updated")
    else:
        c.post(f"/{REALM}/clients", json=rep).raise_for_status()
        internal_id = c.get(f"/{REALM}/clients", params={"clientId": client_id}).json()[0]["id"]
        print(f"client {client_id}: created")
    if spec.get("realmManagementRoles"):
        ensure_service_account_roles(c, internal_id, client_id, spec["realmManagementRoles"])
    if spec.get("mappers"):
        ensure_client_mappers(c, internal_id, client_id, spec["mappers"])


def ensure_client_mappers(
    c: httpx.Client, internal_id: str, client_id: str, mappers: list[dict[str, Any]]
) -> None:
    existing = {
        m["name"]: m
        for m in c.get(f"/{REALM}/clients/{internal_id}/protocol-mappers/models").json()
    }
    for m in mappers:
        if m["name"] in existing:
            mid = existing[m["name"]]["id"]
            c.put(
                f"/{REALM}/clients/{internal_id}/protocol-mappers/models/{mid}",
                json={**existing[m["name"]], **m},
            ).raise_for_status()
        else:
            c.post(
                f"/{REALM}/clients/{internal_id}/protocol-mappers/models", json=m
            ).raise_for_status()
    print(f"client {client_id}: protocol mappers {[m['name'] for m in mappers]}")


def ensure_realm_roles(c: httpx.Client) -> None:
    for name in PLATFORM_ROLES:
        if c.get(f"/{REALM}/roles/{name}").status_code == 404:
            c.post(
                f"/{REALM}/roles",
                json={"name": name, "description": f"CHERT platform role: {name}"},
            ).raise_for_status()
            print(f"realm role {name}: created")
        else:
            print(f"realm role {name}: exists")


def ensure_service_account_roles(
    c: httpx.Client, internal_id: str, client_id: str, roles: list[str]
) -> None:
    sa_user = c.get(f"/{REALM}/clients/{internal_id}/service-account-user").json()
    rm = c.get(f"/{REALM}/clients", params={"clientId": "realm-management"}).json()[0]
    available = c.get(f"/{REALM}/clients/{rm['id']}/roles").json()
    wanted = [r for r in available if r["name"] in roles]
    missing = set(roles) - {r["name"] for r in wanted}
    if missing:
        raise SystemExit(f"realm-management roles not found: {sorted(missing)}")
    path = f"/{REALM}/users/{sa_user['id']}/role-mappings/clients/{rm['id']}"
    c.post(path, json=wanted).raise_for_status()  # idempotent: re-adding is a no-op
    print(f"client {client_id}: service account roles {roles}")


def ensure_user_profile(c: httpx.Client) -> None:
    """D11 minimal data: only email is required. Keycloak's default profile requires first/last
    name and would force an 'Update Account Information' step right after email verification."""
    profile = c.get(f"/{REALM}/users/profile").json()
    changed = False
    for attr in profile.get("attributes", []):
        if attr["name"] in ("firstName", "lastName") and attr.get("required"):
            attr.pop("required", None)
            changed = True
    if changed:
        c.put(f"/{REALM}/users/profile", json=profile).raise_for_status()
    print(f"user profile: first/last name optional ({'updated' if changed else 'already'})")


def ensure_dev_user(c: httpx.Client) -> None:
    email = os.environ.get("DEV_TEST_USER_EMAIL")
    password = os.environ.get("DEV_TEST_USER_PASSWORD")
    if ENV != "dev" or not email or not password:
        return
    rep = {
        "username": email,
        "email": email,
        "emailVerified": True,
        "enabled": True,
        "firstName": "Student",
        "lastName": "One",
        "credentials": [{"type": "password", "value": password, "temporary": False}],
    }
    existing = c.get(f"/{REALM}/users", params={"email": email, "exact": "true"}).json()
    if existing:
        uid = existing[0]["id"]
        c.put(f"/{REALM}/users/{uid}", json={k: v for k, v in rep.items() if k != "credentials"})
        c.put(f"/{REALM}/users/{uid}/reset-password", json=rep["credentials"][0]).raise_for_status()
        print(f"dev user {email}: updated")
    else:
        c.post(f"/{REALM}/users", json=rep).raise_for_status()
        print(f"dev user {email}: created")


def main() -> int:
    c = admin_client()
    ensure_realm(c)
    ensure_realm_roles(c)
    for client_id, spec in CLIENTS.items():
        ensure_client(c, client_id, spec)
    ensure_user_profile(c)
    ensure_dev_user(c)
    return 0


if __name__ == "__main__":
    sys.exit(main())
