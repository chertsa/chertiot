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

router = APIRouter()


class LabTokenRequest(BaseModel):
    email: str


@router.post("/internal/lab-token")
def lab_token(req: LabTokenRequest, request: Request, db: Session = Depends(get_db)) -> Any:
    """The student's own TB JWT for notebook use (M3.2). Same impersonation mechanism the portal
    uses for every tenant-scoped action; isolation is ThingsBoard's own (D10)."""
    secret = get_settings().lab_internal_secret
    given = request.headers.get("x-lab-secret", "")
    if not secret or not hmac.compare_digest(given, secret):
        raise HTTPException(status_code=403)
    user = db.scalar(select(PortalUser).where(PortalUser.email == req.email.lower()))
    if user is None or not user.tb_user_id:
        raise HTTPException(status_code=404, detail="no provisioned user")
    sysadmin = sysadmin_client()
    try:
        student = sysadmin.impersonate(user.tb_user_id)
        try:
            token = student._tokens.token if student._tokens else ""
        finally:
            student.close()
    finally:
        sysadmin.close()
    return {"token": token}
