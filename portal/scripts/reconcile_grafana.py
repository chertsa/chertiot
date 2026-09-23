"""Deterministic Grafana access reconciliation (v2 Phase 4 closure).

Brings every Grafana org user's role in line with the authority of record — the user's **Keycloak
platform realm role** — using only supported Grafana + Keycloak admin APIs. Never writes to a
database, never touches dashboards/datasources/project data, never assumes anything from email
domains, and preserves the break-glass local admin and service accounts.

Mapping (authority = Keycloak realm role):
    platform-admin       -> Grafana Admin
    platform-instructor  -> Grafana Viewer
    anyone else / no KC user / disabled KC user -> removed from the org (+ sessions revoked)

Usage (run inside the portal container so grafana:3000 / keycloak:8080 resolve):
    python -m scripts.reconcile_grafana --dry-run     # report only, change nothing
    python -m scripts.reconcile_grafana --apply       # perform the reconciliation
Idempotent: a second --apply run makes no changes. Logs are PII-safe (emails masked).
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Callable
from typing import Any

import httpx

from scripts.kc_roles import admin_client as kc_admin

# Grafana org logins that are never reconciled (break-glass local admin + any configured service).
PRESERVE_LOGINS = {"admin"} | {
    x.strip() for x in os.environ.get("GRAFANA_PRESERVE_LOGINS", "").split(",") if x.strip()
}
REALM = os.environ.get("KC_REALM", "chertiot")


def mask(email: str) -> str:
    """PII-safe rendering for logs: first char + domain only."""
    if "@" not in email:
        return (email[:1] or "?") + "***"
    local, _, domain = email.partition("@")
    return f"{local[:1]}***@{domain}"


def target_role(kc_exists: bool, kc_enabled: bool, realm_roles: set[str]) -> str:
    """Authoritative Grafana role from the user's Keycloak state. 'REMOVE' = no access."""
    if not kc_exists or not kc_enabled:
        return "REMOVE"
    if "platform-admin" in realm_roles:
        return "Admin"
    if "platform-instructor" in realm_roles:
        return "Viewer"
    return "REMOVE"


def build_plan(
    org_users: list[dict[str, Any]], resolve: Callable[[str], tuple[bool, bool, set[str]]]
) -> list[dict[str, Any]]:
    """Pure planning: for each org user, decide the change. `resolve(email)` returns
    (kc_exists, kc_enabled, realm_roles). Preserved logins are skipped."""
    plan: list[dict[str, Any]] = []
    for u in org_users:
        login = u.get("login") or u.get("email") or ""
        if login in PRESERVE_LOGINS:
            plan.append({"userId": u["userId"], "login": login, "action": "preserve"})
            continue
        email = u.get("email") or login
        exists, enabled, roles = resolve(email)
        target = target_role(exists, enabled, roles)
        current = u.get("role")
        if target == "REMOVE":
            action = "remove" if current is not None else "noop"
        elif target != current:
            action = "set"
        else:
            action = "noop"
        plan.append(
            {
                "userId": u["userId"],
                "login": login,
                "current": current,
                "target": target,
                "action": action,
                "demotion": action in ("remove", "set")
                and _rank(target) < _rank(current or "None"),
            }
        )
    return plan


_ORDER = {"Admin": 3, "Editor": 2, "Viewer": 1, "None": 0, "REMOVE": 0}


def _rank(role: str) -> int:
    return _ORDER.get(role, 0)


class Grafana:
    def __init__(self) -> None:
        self.base = os.environ.get("GRAFANA_INTERNAL_URL", "http://grafana:3000").rstrip("/")
        self.auth = (
            os.environ.get("GRAFANA_ADMIN_USER", "admin"),
            os.environ["GRAFANA_ADMIN_PASSWORD"],
        )
        self._c = httpx.Client(timeout=30)

    def org_users(self) -> list[dict[str, Any]]:
        r = self._c.get(f"{self.base}/api/org/users", auth=self.auth)
        r.raise_for_status()
        return list(r.json())

    def set_role(self, user_id: int, role: str) -> None:
        self._c.patch(
            f"{self.base}/api/org/users/{user_id}", json={"role": role}, auth=self.auth
        ).raise_for_status()

    def remove_from_org(self, user_id: int) -> None:
        self._c.delete(f"{self.base}/api/org/users/{user_id}", auth=self.auth).raise_for_status()

    def revoke_sessions(self, user_id: int) -> None:
        # supported server-admin endpoint: log the user out of all devices (invalidates sessions)
        self._c.post(f"{self.base}/api/admin/users/{user_id}/logout", auth=self.auth)


def kc_resolver() -> Callable[[str], tuple[bool, bool, set[str]]]:
    c = kc_admin()

    def resolve(email: str) -> tuple[bool, bool, set[str]]:
        users = c.get(f"/{REALM}/users", params={"email": email, "exact": "true"}).json()
        if not users:
            return (False, False, set())
        u = users[0]
        roles = c.get(f"/{REALM}/users/{u['id']}/role-mappings/realm").json()
        return (True, bool(u.get("enabled", True)), {r["name"] for r in roles})

    return resolve


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true", help="report actions, change nothing")
    g.add_argument("--apply", action="store_true", help="perform the reconciliation")
    a = ap.parse_args()

    gf = Grafana()
    plan = build_plan(gf.org_users(), kc_resolver())
    summary = {"preserve": 0, "noop": 0, "set": 0, "remove": 0, "sessions_revoked": 0}
    for p in plan:
        act = p["action"]
        summary[act] = summary.get(act, 0) + 1
        line = f"{'DRY' if a.dry_run else 'APPLY'} {act:8} {mask(p['login'])}"
        if act in ("set", "remove"):
            line += f" {p.get('current')}→{p['target']}"
        print(line)
        if a.apply and act == "set":
            gf.set_role(p["userId"], p["target"])
            if p["demotion"]:
                gf.revoke_sessions(p["userId"])
                summary["sessions_revoked"] += 1
        elif a.apply and act == "remove":
            gf.remove_from_org(p["userId"])
            gf.revoke_sessions(p["userId"])
            summary["sessions_revoked"] += 1
    print("RECONCILE_SUMMARY=" + str(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main())
