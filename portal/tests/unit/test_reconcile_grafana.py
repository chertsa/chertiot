"""Grafana reconciliation: decisions, dry-run plan, idempotency, break-glass, PII mask."""

from __future__ import annotations

from typing import Any

from scripts import reconcile_grafana as rg


def test_target_role_from_keycloak() -> None:
    assert rg.target_role(True, True, {"platform-admin"}) == "Admin"
    assert rg.target_role(True, True, {"platform-instructor"}) == "Viewer"
    assert rg.target_role(True, True, {"default-roles-chertiot", "offline_access"}) == "REMOVE"
    assert rg.target_role(False, False, set()) == "REMOVE"  # no KC user
    assert rg.target_role(True, False, {"platform-admin"}) == "REMOVE"  # disabled KC user
    # admin beats instructor if somehow both present
    assert rg.target_role(True, True, {"platform-admin", "platform-instructor"}) == "Admin"


def test_mask_is_pii_safe() -> None:
    assert rg.mask("alice@chertiot.dev") == "a***@chertiot.dev"
    assert "lice" not in rg.mask("alice@chertiot.dev")


# a small in-memory Grafana org + Keycloak resolver
ORG_USERS = [
    {"userId": 1, "login": "admin", "email": "admin@localhost", "role": "Admin"},  # break-glass
    {"userId": 2, "login": "legacy-student@x", "email": "legacy-student@x", "role": "Viewer"},
    {"userId": 3, "login": "instructor@x", "email": "instructor@x", "role": "Viewer"},
    {"userId": 4, "login": "admin-user@x", "email": "admin-user@x", "role": "Viewer"},  # under-priv
    {"userId": 5, "login": "demoted-admin@x", "email": "demoted-admin@x", "role": "Admin"},
    {"userId": 6, "login": "deleted@x", "email": "deleted@x", "role": "Viewer"},  # gone from KC
]
KC = {
    "legacy-student@x": (True, True, {"default-roles-chertiot"}),  # no platform role → REMOVE
    "instructor@x": (True, True, {"platform-instructor"}),  # → Viewer (already) noop
    "admin-user@x": (True, True, {"platform-admin"}),  # → Admin (promote)
    "demoted-admin@x": (True, True, {"platform-instructor"}),  # Admin→Viewer (demotion)
    # deleted@x absent → REMOVE
}


def _resolve(email: str) -> tuple[bool, bool, set[str]]:
    return KC.get(email, (False, False, set()))


def test_build_plan_actions_and_breakglass() -> None:
    plan = {p["login"]: p for p in rg.build_plan(ORG_USERS, _resolve)}
    assert plan["admin"]["action"] == "preserve"  # break-glass never touched
    assert plan["legacy-student@x"]["action"] == "remove"
    assert plan["instructor@x"]["action"] == "noop"  # already Viewer
    assert plan["admin-user@x"]["action"] == "set" and plan["admin-user@x"]["target"] == "Admin"
    d = plan["demoted-admin@x"]
    assert d["action"] == "set" and d["target"] == "Viewer" and d["demotion"] is True
    assert plan["deleted@x"]["action"] == "remove"  # deleted KC user → removed


def test_plan_is_idempotent_after_convergence() -> None:
    # simulate the org AFTER applying the plan, then re-plan → all noop/preserve
    converged: list[dict[str, Any]] = [
        {"userId": 1, "login": "admin", "email": "admin@localhost", "role": "Admin"},
        {"userId": 3, "login": "instructor@x", "email": "instructor@x", "role": "Viewer"},
        {"userId": 4, "login": "admin-user@x", "email": "admin-user@x", "role": "Admin"},
        {"userId": 5, "login": "demoted-admin@x", "email": "demoted-admin@x", "role": "Viewer"},
        # removed users (2, 6) are no longer org members
    ]
    actions = {p["action"] for p in rg.build_plan(converged, _resolve)}
    assert actions <= {"noop", "preserve"}  # nothing left to change
