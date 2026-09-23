"""Keycloak admin connection + platform realm-role helpers (connection env only — no client
secrets), shared by scripts.setup_keycloak and scripts.grant_role."""

from __future__ import annotations

import os

import httpx

KC = os.environ.get("KC_ADMIN_URL", os.environ.get("KC_INTERNAL_URL", "http://localhost:8080"))
REALM = os.environ["KC_REALM"]

# Realm roles that mark platform staff (kept in sync from the portal role by scripts.grant_role).
PLATFORM_ROLES = ["platform-admin", "platform-instructor"]


def admin_client() -> httpx.Client:
    """A master-realm admin httpx client scoped to /admin/realms (full realm admin)."""
    r = httpx.post(
        f"{KC}/realms/master/protocol/openid-connect/token",
        data={
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": os.environ["KEYCLOAK_ADMIN"],
            "password": os.environ["KEYCLOAK_ADMIN_PASSWORD"],
        },
        timeout=30,
    )
    r.raise_for_status()
    return httpx.Client(
        base_url=f"{KC}/admin/realms",
        headers={"Authorization": f"Bearer {r.json()['access_token']}"},
        timeout=30,
    )
