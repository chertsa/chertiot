"""In-network endpoints (never routed by Caddy). Guarded by a shared secret header."""

import hmac
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import PortalUser
from app.onboarding import sysadmin_client
from app.project import membership

router = APIRouter()


class LabTokenRequest(BaseModel):
    email: str
    project_id: str


@router.post("/internal/lab-token")
def lab_token(req: LabTokenRequest, request: Request, db: Session = Depends(get_db)) -> Any:
    """A notebook's TB JWT for ONE project (M5.3): the caller's own Tenant-Admin session in that
    project tenant, via sysadmin impersonation. Requires an active membership — this is the whole
    isolation story for per-project notebooks (D10/D13)."""
    secret = get_settings().lab_internal_secret
    given = request.headers.get("x-lab-secret", "")
    if not secret or not hmac.compare_digest(given, secret):
        raise HTTPException(status_code=403)
    user = db.scalar(select(PortalUser).where(PortalUser.email == req.email.lower()))
    if user is None:
        raise HTTPException(status_code=404, detail="unknown user")
    member = membership(db, req.project_id, user.id)
    if member is None or member.status != "active" or not member.tb_user_id:
        raise HTTPException(status_code=403, detail="not an active member of this project")
    sysadmin = sysadmin_client()
    try:
        session = sysadmin.impersonate(member.tb_user_id)
        try:
            token = session._tokens.token if session._tokens else ""  # noqa: SLF001
        finally:
            session.close()
    finally:
        sysadmin.close()
    return {"token": token}
