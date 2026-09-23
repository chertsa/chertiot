"""CLI: grant/revoke portal roles.  make grant-role EMAIL=x@y ROLE=instructor

Also syncs the matching Keycloak realm role so Grafana (which authenticates against Keycloak, not
the portal DB) can gate platform monitoring by role:
  admin      -> platform-admin
  instructor -> platform-instructor
  student    -> (neither)
Run inside the portal container for staging/prod so KC_INTERNAL_URL resolves.
"""

from __future__ import annotations

import argparse
import sys

from sqlalchemy import select

from app.db import session_factory
from app.models import PortalUser

_ROLE_TO_REALM = {"admin": "platform-admin", "instructor": "platform-instructor", "student": None}


def sync_keycloak_role(kc_user_id: str, portal_role: str) -> str:
    """Assign the matching platform realm role and remove the others. Returns a status string.
    Best-effort: never blocks the portal-DB change (returns an error string instead of raising)."""
    from scripts.kc_roles import PLATFORM_ROLES, REALM, admin_client

    want = _ROLE_TO_REALM[portal_role]
    try:
        c = admin_client()
        for rname in PLATFORM_ROLES:
            rep = c.get(f"/{REALM}/roles/{rname}")
            if rep.status_code == 404:
                continue
            role = rep.json()
            path = f"/{REALM}/users/{kc_user_id}/role-mappings/realm"
            if rname == want:
                c.post(path, json=[role]).raise_for_status()  # idempotent
            else:
                c.request("DELETE", path, json=[role])  # idempotent (no-op if absent)
        return f"keycloak realm role -> {want or 'none'}"
    except Exception as e:  # noqa: BLE001
        return f"keycloak sync FAILED ({str(e)[:120]}) — run inside the portal container"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("email")
    p.add_argument("role", choices=["student", "instructor", "admin"])
    a = p.parse_args()
    with session_factory()() as db:
        user = db.scalar(select(PortalUser).where(PortalUser.email == a.email.lower()))
        if user is None:
            print("no such user", file=sys.stderr)
            return 1
        user.role = a.role
        db.commit()
        status = sync_keycloak_role(user.kc_user_id, a.role) if user.kc_user_id else "no kc_user_id"
        print(f"{user.email} -> {a.role} ({status})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
