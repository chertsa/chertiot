"""Instructor console (M3.3, D6): class codes, roster, suspend/reactivate — portal-only.

Roster shows operational data only (last-seen, device count), never telemetry.
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
from app.keycloak_admin import KeycloakAdmin
from app.models import ClassCode, PortalUser
from app.onboarding import sysadmin_client
from app.provisioning import suspend_student
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
    ctx = {"user": me, "codes": codes, "counts": counts}
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


@router.get("/cohort/{cohort}")
def roster(request: Request, cohort: str, db: Session = Depends(get_db)) -> Any:
    me = require_instructor(request, db)
    owns = db.scalar(
        select(func.count())
        .select_from(ClassCode)
        .where(ClassCode.cohort == cohort, ClassCode.instructor_email == me.email)
    )
    if not owns and me.role != "admin":
        raise HTTPException(status_code=403)
    students = list(db.scalars(select(PortalUser).where(PortalUser.cohort == cohort)))
    rows: list[dict[str, Any]] = []
    sysadmin = sysadmin_client()
    try:
        for s in students:
            entry: dict[str, Any] = {
                "email": s.email,
                "state": s.provisioning_state,
                "last_login": s.last_login_at,
                "suspended": s.role == "suspended",
                "devices": None,
                "last_seen": None,
            }
            if s.tb_user_id:
                try:
                    student_client = sysadmin.impersonate(s.tb_user_id)
                    try:
                        devices = student_client.list_devices()
                        entry["devices"] = len(devices)
                        actives = []
                        for d in devices:
                            if d.id:
                                attrs = student_client.server_attributes(
                                    d.id.id, ["lastActivityTime"]
                                )
                                if attrs.get("lastActivityTime"):
                                    actives.append(int(attrs["lastActivityTime"]))
                        if actives:
                            entry["last_seen"] = datetime.fromtimestamp(max(actives) / 1000, UTC)
                    finally:
                        student_client.close()
                except Exception as e:  # noqa: BLE001 — roster stays usable if one student errors
                    log.debug("roster row failed for %s: %r", s.email, e)
            rows.append(entry)
    finally:
        sysadmin.close()
    ctx = {"user": me, "cohort": cohort, "rows": rows}
    return templates.TemplateResponse(request, "teach/roster.html", ctx)


@router.post("/cohort/{cohort}/suspend")
def toggle_suspend(
    request: Request,
    cohort: str,
    email: Annotated[str, Form()],
    action: Annotated[str, Form()],
    db: Session = Depends(get_db),
) -> Any:
    """Suspend = disable in Keycloak (authoritative) + TB credentials flag (belt and braces)."""
    me = require_instructor(request, db)
    target = db.scalar(select(PortalUser).where(PortalUser.email == email.lower()))
    if target is None or target.cohort != cohort:
        raise HTTPException(status_code=404)
    owns = db.scalar(
        select(func.count())
        .select_from(ClassCode)
        .where(ClassCode.cohort == cohort, ClassCode.instructor_email == me.email)
    )
    if not owns and me.role != "admin":
        raise HTTPException(status_code=403)
    suspend = action == "suspend"
    kc = KeycloakAdmin()
    if target.kc_user_id:
        kc.set_enabled(target.kc_user_id, not suspend)
    sysadmin = sysadmin_client()
    try:
        suspend_student(sysadmin, target.email, suspended=suspend)
    finally:
        sysadmin.close()
    target.role = "suspended" if suspend else "student"
    audit(db, me.email, f"student.{action}", target.email, cohort=cohort)
    db.commit()
    return RedirectResponse(f"/teach/cohort/{cohort}", status_code=303)
