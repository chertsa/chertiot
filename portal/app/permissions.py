"""Central authorization model (v2 Phase 4).

One source of truth for "who may do what", replacing per-route inline role checks. Behaviour is
identical to v1 (owner decision, recorded 2026-09-22) — this module makes it explicit and testable.

Two independent role axes:
  * **platform role** — `PortalUser.role` ∈ {student, instructor, admin}. Governs platform-wide
    capabilities (instructor console, platform monitoring). Default: student.
  * **project role** — `ProjectMember.role` ∈ {owner, member}, only for an *active* membership.
    Governs actions inside one project's tenant.

Permission matrix (allowed = ✓):

  Project capability            | member | owner | notes
  ------------------------------|--------|-------|-----------------------------------------
  view / telemetry / monitoring |   ✓    |  ✓    | any active member (membership gate)
  device manage, alert rules    |   ✓    |  ✓    | any active member
  flows edit, notebook launch   |   ✓    |  ✓    | any active member
  dashboard reset               |   ✓    |  ✓    | any active member
  open ThingsBoard console      |   ✓    |  ✓    | any active member
  alert ack (non-critical)      |   ✓    |  ✓    | any active member
  alert ack (CRITICAL)          |   ✗    |  ✓    | owner only
  member invite                 |   ✗    |  ✓    | owner only
  member manage (en/disable/rm) |   ✗    |  ✓    | owner only
  join-request resolve          |   ✗    |  ✓    | owner only
  project delete                |   ✗    |  ✓    | owner only

  Platform capability     | student | instructor | admin
  ------------------------|---------|------------|------
  instructor console      |   ✗     |     ✓      |  ✓
  platform monitoring     |   ✗     |     ✓      |  ✓
  (instructors see a read-only cohort roster only — never another project's contents.)

The server is the authority; templates only *hide* what `can_*` denies.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any


class Cap(StrEnum):
    # --- project capabilities (require an active membership) ---
    ALERT_ACK = "alert.ack"  # non-critical severities
    ALERT_ACK_CRITICAL = "alert.ack.critical"
    ALERT_MANAGE = "alert.manage"
    DEVICE_MANAGE = "device.manage"
    DASHBOARD_RESET = "dashboard.reset"
    FLOWS_EDIT = "flows.edit"
    NOTEBOOK_LAUNCH = "notebook.launch"
    THINGSBOARD_OPEN = "thingsboard.open"
    MEMBER_INVITE = "member.invite"
    MEMBER_MANAGE = "member.manage"
    JOIN_RESOLVE = "join.resolve"
    PROJECT_DELETE = "project.delete"
    # --- platform capabilities (platform role) ---
    INSTRUCTOR_CONSOLE = "instructor.console"
    PLATFORM_MONITORING = "platform.monitoring"


# Project capabilities that require the OWNER project-role; every other project cap is allowed to
# any active member.
_OWNER_ONLY: frozenset[Cap] = frozenset(
    {
        Cap.ALERT_ACK_CRITICAL,
        Cap.MEMBER_INVITE,
        Cap.MEMBER_MANAGE,
        Cap.JOIN_RESOLVE,
        Cap.PROJECT_DELETE,
    }
)
# Platform capabilities and the platform roles that hold them.
_STAFF_ROLES: frozenset[str] = frozenset({"instructor", "admin"})
_PLATFORM_CAPS: frozenset[Cap] = frozenset({Cap.INSTRUCTOR_CONSOLE, Cap.PLATFORM_MONITORING})


def project_can(member: Any, cap: Cap) -> bool:
    """True if this membership may perform `cap` in its project. `member` is a ProjectMember (or
    None). Requires an active membership; owner-only caps additionally require role == 'owner'."""
    if member is None or getattr(member, "status", None) != "active":
        return False
    if cap in _OWNER_ONLY:
        return getattr(member, "role", None) == "owner"
    return True  # any active member


def ack_cap(severity: str) -> Cap:
    """The capability required to acknowledge an alarm of this severity (CRITICAL is owner-only)."""
    return Cap.ALERT_ACK_CRITICAL if (severity or "").upper() == "CRITICAL" else Cap.ALERT_ACK


def platform_can(user: Any, cap: Cap) -> bool:
    """True if this user's platform role holds `cap`. `user` is a PortalUser (or None)."""
    if user is None or cap not in _PLATFORM_CAPS:
        return False
    return getattr(user, "role", "student") in _STAFF_ROLES


def is_staff(user: Any) -> bool:
    """Platform staff = instructor or admin (see platform capabilities)."""
    return getattr(user, "role", "student") in _STAFF_ROLES
