from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import optional_user
from app.config import get_settings
from app.db import get_db
from app.models import PortalUser
from app.onboarding import ensure_provisioned, sysadmin_client
from app.templating import templates

router = APIRouter()


@router.get("/")
def index(request: Request) -> Any:
    if optional_user(request):
        return RedirectResponse("/home", status_code=303)
    return templates.TemplateResponse(request, "index.html")


def _load_user(request: Request, db: Session) -> PortalUser | None:
    session_user = optional_user(request)
    if not session_user:
        return None
    return db.scalar(select(PortalUser).where(PortalUser.kc_user_id == session_user["sub"]))


@router.get("/home")
def home(request: Request, db: Session = Depends(get_db)) -> Any:
    user = _load_user(request, db)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    s = get_settings()
    devices: list[dict[str, str]] = []
    dashboard_url = f"{s.tb_public_url}/dashboards"
    if user.provisioning_state == "provisioned" and user.tb_user_id:
        sysadmin = sysadmin_client()
        try:
            as_student = sysadmin.impersonate(user.tb_user_id)
            try:
                for d in as_student.list_devices():
                    if d.id:
                        creds = as_student.get_device_credentials(d.id.id)
                        devices.append(
                            {"name": d.name, "token": creds.credentials_id, "id": d.id.id}
                        )
                dash = as_student.find_dashboard("My devices")
                if dash and dash.id:
                    dashboard_url = f"{s.tb_public_url}/dashboards/{dash.id.id}"
            finally:
                as_student.close()
        finally:
            sysadmin.close()
    ctx = {"user": user, "devices": devices, "dashboard_url": dashboard_url, "mqtt_host": s.domain}
    return templates.TemplateResponse(request, "home.html", ctx)


@router.post("/home/provision")
def retry_provision(request: Request, db: Session = Depends(get_db)) -> Any:
    user = _load_user(request, db)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    ensure_provisioned(db, user)
    return RedirectResponse("/home", status_code=303)
