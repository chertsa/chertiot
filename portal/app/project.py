"""Project domain logic (D13/M5.1): a project is an isolated ThingsBoard **tenant**; the owner and
members are Tenant-Admin users inside it. The portal is the identity broker — it creates a TB tenant
per project and one TB Tenant-Admin user per human per project, then opens per-project sessions via
sysadmin impersonation (never TB's DB — D10)."""

from __future__ import annotations

import logging
import re
import secrets
from collections.abc import Iterator
from contextlib import contextmanager

from fastapi import HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import audit
from app.models import (
    PortalUser,
    Project,
    ProjectInvite,
    ProjectJoinRequest,
    ProjectMember,
)
from app.onboarding import sysadmin_client
from app.provisioning import (
    ProvisioningError,
    ensure_starter_dashboard,
    ensure_student_profile,
    require_id,
)
from app.student import load_user
from app.tb_client import TbClient, Tenant, User

log = logging.getLogger(__name__)

# TB user emails are globally unique, so a human gets a synthetic per-project TB address. These
# accounts never receive mail or log in with a password — the portal brokers their sessions.
SYNTH_EMAIL_DOMAIN = "proj.chertiot.local"


def slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    return (s or "project")[:40]


def unique_slug(db: Session, name: str) -> str:
    base = slugify(name)
    slug, n = base, 1
    while db.scalar(select(Project.id).where(Project.slug == slug)):
        n += 1
        slug = f"{base}-{n}"
    return slug


def member_tb_email(project: Project, user: PortalUser) -> str:
    return f"{project.slug}-{user.id[:8]}@{SYNTH_EMAIL_DOMAIN}"


def projects_for(db: Session, user_id: str) -> list[tuple[Project, ProjectMember]]:
    """Active memberships → (project, membership), newest project first."""
    rows = db.execute(
        select(Project, ProjectMember)
        .join(ProjectMember, ProjectMember.project_id == Project.id)
        .where(ProjectMember.user_id == user_id, ProjectMember.status == "active")
        .order_by(Project.created_at.desc())
    ).all()
    return [(p, m) for p, m in rows]


def membership(db: Session, project_id: str, user_id: str) -> ProjectMember | None:
    return db.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id, ProjectMember.user_id == user_id
        )
    )


def require_membership(
    request: Request, db: Session, project_id: str
) -> tuple[PortalUser, Project, ProjectMember]:
    """Gate a project route: the caller must be a signed-in, active, provisioned member."""
    user = load_user(request, db)
    if user is None:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    project = db.get(Project, project_id)
    member = membership(db, project_id, user.id) if project else None
    if project is None or member is None or member.status != "active":
        raise HTTPException(status_code=303, headers={"Location": "/home"})
    if project.provisioning_state != "provisioned" or not member.tb_user_id:
        raise HTTPException(status_code=303, headers={"Location": f"/projects/{project_id}"})
    return user, project, member


# ---------------------------------------------------------------- provisioning (via sysadmin) ----
def _provision(sysadmin: TbClient, project: Project, owner: PortalUser) -> str:
    """Create the project's TB tenant + the owner's Tenant-Admin user + starter dashboard.
    Returns the owner's tb_user_id. Idempotent: reuses stored ids when present."""
    profile = ensure_student_profile(sysadmin)  # student quotas are the default profile
    if not project.tb_tenant_id:
        tenant = sysadmin.save_tenant(
            Tenant(
                title=project.name,
                email=f"{project.slug}@{SYNTH_EMAIL_DOMAIN}",
                tenantProfileId=profile.id,
            )
        )
        project.tb_tenant_id = require_id(tenant, "tenant")
    tb_user_id = ensure_member_user(sysadmin, project, owner)
    student = sysadmin.impersonate(tb_user_id)
    try:
        ensure_starter_dashboard(student)
    finally:
        student.close()
    return tb_user_id


def _activate_user(sysadmin: TbClient, user_id: str) -> None:
    """Give a portal-created TB user internal credentials so its JWT session can REFRESH — without
    this, TB returns 'User account is not active' on refresh and the console drops to /login on a
    profile save or when the short token expires. The random password is never exposed (members
    reach TB only via the portal's handoff). Best-effort; never blocks provisioning."""
    from urllib.parse import parse_qs, urlparse

    try:
        link = sysadmin.get_activation_link(user_id)
        token = parse_qs(urlparse(link).query).get("activateToken", [""])[0]
        if token:
            sysadmin.activate_user(token, secrets.token_urlsafe(18))
    except Exception:  # noqa: BLE001
        log.warning("could not activate TB user %s (refresh may be unavailable)", user_id)


def ensure_member_user(sysadmin: TbClient, project: Project, user: PortalUser) -> str:
    """Find-or-create this human's Tenant-Admin user inside the project tenant (activated so its
    session refreshes)."""
    if not project.tb_tenant_id:
        raise ProvisioningError("project has no tb_tenant_id")
    email = member_tb_email(project, user)
    existing = sysadmin.find_tenant_user(project.tb_tenant_id, email)
    if existing and existing.id:
        return existing.id.id
    created = sysadmin.save_user(
        User(
            email=email,
            authority="TENANT_ADMIN",
            tenantId={"entityType": "TENANT", "id": project.tb_tenant_id},
            firstName=(user.email.split("@")[0])[:40],
        )
    )
    user_id = require_id(created, "member user")
    _activate_user(sysadmin, user_id)
    return user_id


def create_project(db: Session, owner: PortalUser, name: str, description: str | None) -> Project:
    """Create the portal row, provision the TB tenant + owner membership, and commit. On a TB
    failure the project is saved as 'failed' so the workspace can offer a retry (never raises)."""
    project = Project(
        slug=unique_slug(db, name), name=name.strip()[:120], description=(description or "").strip()
    )
    db.add(project)
    db.flush()
    member = ProjectMember(project_id=project.id, user_id=owner.id, role="owner")
    db.add(member)
    sysadmin = sysadmin_client()
    try:
        member.tb_user_id = _provision(sysadmin, project, owner)
        project.provisioning_state, project.provisioning_error = "provisioned", None
        audit(db, owner.email, "project.create", project.slug, tb_tenant_id=project.tb_tenant_id)
    except Exception as e:  # noqa: BLE001 — record failure, let the UI retry
        log.exception("project provisioning failed for %s", project.slug)
        project.provisioning_state, project.provisioning_error = "failed", str(e)[:500]
    finally:
        sysadmin.close()
    db.commit()
    return project


def retry_provision(
    db: Session, project: Project, owner: PortalUser, member: ProjectMember
) -> bool:
    sysadmin = sysadmin_client()
    try:
        member.tb_user_id = _provision(sysadmin, project, owner)
        project.provisioning_state, project.provisioning_error = "provisioned", None
    except Exception as e:  # noqa: BLE001
        log.exception("project provisioning retry failed for %s", project.slug)
        project.provisioning_state, project.provisioning_error = "failed", str(e)[:500]
        db.commit()
        return False
    db.commit()
    return True


def delete_project(db: Session, project: Project, actor_email: str) -> None:
    """Irreversible: delete the TB tenant (devices, dashboards, telemetry) and portal rows."""
    if project.tb_tenant_id:
        sysadmin = sysadmin_client()
        try:
            sysadmin.delete_tenant(project.tb_tenant_id)
        finally:
            sysadmin.close()
    for m in db.scalars(select(ProjectMember).where(ProjectMember.project_id == project.id)):
        db.delete(m)
    audit(db, actor_email, "project.delete", project.slug)
    db.delete(project)
    db.commit()


@contextmanager
def as_project(member: ProjectMember) -> Iterator[tuple[TbClient, TbClient]]:
    """Yields (sysadmin, member-session) clients for the project tenant; both closed after."""
    if not member.tb_user_id:
        raise HTTPException(status_code=409, detail="project not provisioned")
    sysadmin = sysadmin_client()
    try:
        session = sysadmin.impersonate(member.tb_user_id)
        try:
            yield sysadmin, session
        finally:
            session.close()
    finally:
        sysadmin.close()


# ------------------------------------------------------------------------ collaboration (M5.6) ----
def members(db: Session, project_id: str) -> list[tuple[ProjectMember, PortalUser]]:
    """Every membership (any status) with its portal user, owners first."""
    rows = db.execute(
        select(ProjectMember, PortalUser)
        .join(PortalUser, PortalUser.id == ProjectMember.user_id)
        .where(ProjectMember.project_id == project_id)
        .order_by(ProjectMember.role.desc(), ProjectMember.added_at)
    ).all()
    return [(m, u) for m, u in rows]


def add_member(
    db: Session, project: Project, user: PortalUser, role: str = "member"
) -> ProjectMember:
    """Add (or reactivate) a human as a Tenant-Admin of the project tenant. Idempotent."""
    member = membership(db, project.id, user.id)
    if member is None:
        member = ProjectMember(project_id=project.id, user_id=user.id, role=role)
        db.add(member)
    member.status = "active"
    sysadmin = sysadmin_client()
    try:
        member.tb_user_id = ensure_member_user(sysadmin, project, user)
    finally:
        sysadmin.close()
    audit(db, user.email, "project.member.add", project.slug, role=role)
    db.commit()
    return member


def set_member_status(
    db: Session, project: Project, member: ProjectMember, *, active: bool
) -> None:
    """Enable/disable a member. Disabled members are blocked at the portal gate (the sole access
    path — D13), so their project data stays intact and re-enabling is instant."""
    member.status = "active" if active else "disabled"
    act = "project.member.enable" if active else "project.member.disable"
    audit(db, member.user_id, act, project.slug)
    db.commit()


def remove_member(db: Session, project: Project, member: ProjectMember) -> None:
    """Remove a member: delete their TB user in the project tenant and the portal row."""
    if member.tb_user_id:
        sysadmin = sysadmin_client()
        try:
            sysadmin.delete_user(member.tb_user_id)
        except Exception:  # noqa: BLE001
            log.info("member TB user %s already gone", member.tb_user_id)
        finally:
            sysadmin.close()
    audit(db, member.user_id, "project.member.remove", project.slug)
    db.delete(member)
    db.commit()


def create_invite(db: Session, project: Project, owner: PortalUser, email: str) -> ProjectInvite:
    invite = ProjectInvite(
        project_id=project.id, invited_email=email.strip().lower(), invited_by=owner.id
    )
    db.add(invite)
    audit(db, owner.email, "project.invite", project.slug, invited=invite.invited_email)
    db.commit()
    # Best-effort invite email (the link also shows in the owner's Members panel).
    from app.config import get_settings
    from app.email import send_email

    link = f"{get_settings().portal_public_url.rstrip('/')}/invite/{invite.token}"
    send_email(
        invite.invited_email,
        f"You're invited to the CHERT IoT project “{project.name}”",
        f"{owner.email} invited you to collaborate on the project “{project.name}”.\n\n"
        f"Open this link to join (sign in with this email address):\n{link}\n",
    )
    return invite


def accept_invite(db: Session, token: str, user: PortalUser) -> Project | None:
    """Accept an invite by token if it belongs to this user's email. Returns the project."""
    invite = db.scalar(select(ProjectInvite).where(ProjectInvite.token == token))
    if invite is None or invite.status != "pending":
        return None
    if invite.invited_email != user.email.lower():
        return None
    project = db.get(Project, invite.project_id)
    if project is None:
        return None
    add_member(db, project, user)
    invite.status = "accepted"
    db.commit()
    return project


def accept_pending_invites_for(db: Session, user: PortalUser) -> None:
    """On login: silently accept any pending invites addressed to this user's email."""
    pending = db.scalars(
        select(ProjectInvite).where(
            ProjectInvite.invited_email == user.email.lower(), ProjectInvite.status == "pending"
        )
    ).all()
    for invite in pending:
        project = db.get(Project, invite.project_id)
        if project and project.provisioning_state == "provisioned":
            add_member(db, project, user)
            invite.status = "accepted"
    if pending:
        db.commit()


def request_to_join(db: Session, project: Project, user: PortalUser) -> ProjectJoinRequest:
    existing = db.scalar(
        select(ProjectJoinRequest).where(
            ProjectJoinRequest.project_id == project.id,
            ProjectJoinRequest.user_id == user.id,
            ProjectJoinRequest.status == "pending",
        )
    )
    if existing:
        return existing
    req = ProjectJoinRequest(project_id=project.id, user_id=user.id)
    db.add(req)
    audit(db, user.email, "project.join_request", project.slug)
    db.commit()
    return req


def join_requests(db: Session, project_id: str) -> list[tuple[ProjectJoinRequest, PortalUser]]:
    rows = db.execute(
        select(ProjectJoinRequest, PortalUser)
        .join(PortalUser, PortalUser.id == ProjectJoinRequest.user_id)
        .where(ProjectJoinRequest.project_id == project_id, ProjectJoinRequest.status == "pending")
        .order_by(ProjectJoinRequest.created_at)
    ).all()
    return [(r, u) for r, u in rows]


def resolve_join_request(
    db: Session, project: Project, req: ProjectJoinRequest, *, approve: bool
) -> None:
    if approve:
        user = db.get(PortalUser, req.user_id)
        if user:
            add_member(db, project, user)
    req.status = "approved" if approve else "denied"
    db.commit()


def pending_invites(db: Session, project_id: str) -> list[ProjectInvite]:
    return list(
        db.scalars(
            select(ProjectInvite).where(
                ProjectInvite.project_id == project_id, ProjectInvite.status == "pending"
            )
        )
    )
