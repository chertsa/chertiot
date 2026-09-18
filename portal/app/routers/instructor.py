"""Instructor console (D6, D13): class codes + read-mostly project oversight — portal-only.

The platform is project-centric (D13): a project is an isolated ThingsBoard tenant, and humans
own or join projects. Instructor oversight here shows operational data only (project roster,
best-effort device counts), never telemetry.
"""

import logging
import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit import audit
from app.db import get_db
from app.models import ClassCode, PortalUser, Project, ProjectMember
from app.onboarding import sysadmin_client
from app.student import load_user
from app.templating import templates

log = logging.getLogger(__name__)

router = APIRouter(prefix="/teach")


def require_instructor(request: Request, db: Session) -> PortalUser:
    user = load_user(request, db)
    if user is None:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    if user.role not in ("instructor", "admin"):
        raise HTTPException(status_code=403, detail="instructor role required")
    return user


@router.get("")
def console(request: Request, db: Session = Depends(get_db)) -> Any:
    me = require_instructor(request, db)
    codes = list(db.scalars(select(ClassCode).where(ClassCode.instructor_email == me.email)))
    cohorts = [c.cohort for c in codes]
    counts: dict[str, int] = {
        str(cohort): int(n)
        for cohort, n in db.execute(
            select(PortalUser.cohort, func.count())
            .where(PortalUser.cohort.in_(cohorts or [""]))
            .group_by(PortalUser.cohort)
        ).all()
    }
    overview = {
        "projects": db.scalar(select(func.count()).select_from(Project)) or 0,
        "active_projects": db.scalar(
            select(func.count()).select_from(Project).where(Project.status == "active")
        )
        or 0,
        "members": db.scalar(
            select(func.count()).select_from(ProjectMember).where(ProjectMember.status == "active")
        )
        or 0,
    }
    ctx = {"user": me, "codes": codes, "counts": counts, "overview": overview}
    return templates.TemplateResponse(request, "teach/console.html", ctx)


@router.post("/codes")
def create_code(
    request: Request,
    cohort: Annotated[str, Form()],
    max_uses: Annotated[int, Form()] = 100,
    days: Annotated[int, Form()] = 180,
    db: Session = Depends(get_db),
) -> Any:
    me = require_instructor(request, db)
    cohort = cohort.strip().lower().replace(" ", "-")[:64]
    if not cohort:
        raise HTTPException(status_code=422, detail="cohort required")
    code = ClassCode(
        code=f"{cohort[:10].upper()}-{secrets.token_hex(2).upper()}",
        cohort=cohort,
        instructor_email=me.email,
        max_uses=max(1, min(max_uses, 500)),
        expires_at=datetime.now(UTC) + timedelta(days=max(1, min(days, 365))),
    )
    db.add(code)
    audit(db, me.email, "class_code.create", code.code, cohort=cohort)
    db.commit()
    return RedirectResponse("/teach", status_code=303)


@router.post("/codes/{code}/deactivate")
def deactivate_code(request: Request, code: str, db: Session = Depends(get_db)) -> Any:
    me = require_instructor(request, db)
    row = db.get(ClassCode, code)
    if row is None or row.instructor_email != me.email:
        raise HTTPException(status_code=404)
    row.active = False
    audit(db, me.email, "class_code.deactivate", code)
    db.commit()
    return RedirectResponse("/teach", status_code=303)


@router.get("/projects")
def projects_roster(request: Request, db: Session = Depends(get_db)) -> Any:
    """Read-only roster of every project (D6/D13): owner, active-member count, provisioning state
    and a best-effort device count (impersonate the owner's TB user). One TB failure per row is
    swallowed so the page never 500s."""
    me = require_instructor(request, db)
    projects = list(db.scalars(select(Project).order_by(Project.created_at.desc())))

    member_counts: dict[str, int] = {
        str(pid): int(n)
        for pid, n in db.execute(
            select(ProjectMember.project_id, func.count())
            .where(ProjectMember.status == "active")
            .group_by(ProjectMember.project_id)
        ).all()
    }
    owners: dict[str, tuple[ProjectMember, str]] = {
        m.project_id: (m, u.email)
        for m, u in db.execute(
            select(ProjectMember, PortalUser)
            .join(PortalUser, PortalUser.id == ProjectMember.user_id)
            .where(ProjectMember.role == "owner")
        ).all()
    }

    rows: list[dict[str, Any]] = []
    sysadmin = sysadmin_client()
    try:
        for p in projects:
            owner_member, owner_email = owners.get(p.id, (None, None))
            devices: int | None = None
            if owner_member is not None and owner_member.tb_user_id:
                try:
                    student_client = sysadmin.impersonate(owner_member.tb_user_id)
                    try:
                        devices = len(student_client.list_devices())
                    finally:
                        student_client.close()
                except Exception as e:  # noqa: BLE001 — roster stays usable if one project errors
                    log.debug("device count failed for project %s: %r", p.slug, e)
            rows.append(
                {
                    "name": p.name,
                    "slug": p.slug,
                    "owner_email": owner_email,
                    "members": member_counts.get(p.id, 0),
                    "state": p.provisioning_state,
                    "created_at": p.created_at,
                    "devices": devices,
                }
            )
    finally:
        sysadmin.close()
    ctx = {"user": me, "rows": rows}
    return templates.TemplateResponse(request, "teach/roster.html", ctx)


# TODO(D13): identity-level suspend (disable a Keycloak user via KeycloakAdmin().set_enabled) is
# still valid but no longer belongs to a cohort/tenant; wire it to a per-user admin view when the
# project-centric people-management surface lands. The old per-user-tenant suspend is gone.
