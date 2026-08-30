"""Per-request access to the logged-in student's ThingsBoard tenant (D10: via REST, as them)."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from fastapi import HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import optional_user
from app.models import PortalUser
from app.onboarding import sysadmin_client
from app.tb_client import TbClient


def load_user(request: Request, db: Session) -> PortalUser | None:
    session_user = optional_user(request)
    if not session_user:
        return None
    return db.scalar(select(PortalUser).where(PortalUser.kc_user_id == session_user["sub"]))


def require_provisioned(request: Request, db: Session) -> PortalUser:
    user = load_user(request, db)
    if user is None:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    if user.provisioning_state != "provisioned" or not user.tb_user_id:
        raise HTTPException(status_code=303, headers={"Location": "/home"})
    return user


@contextmanager
def as_student(user: PortalUser) -> Iterator[tuple[TbClient, TbClient]]:
    """Yields (sysadmin, tenant-admin-as-student) clients; both closed afterwards."""
    if not user.tb_user_id:
        raise HTTPException(status_code=409, detail="not provisioned")
    sysadmin = sysadmin_client()
    try:
        student = sysadmin.impersonate(user.tb_user_id)
        try:
            yield sysadmin, student
        finally:
            student.close()
    finally:
        sysadmin.close()
