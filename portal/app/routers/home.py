from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.auth import optional_user
from app.config import get_settings
from app.db import get_db
from app.onboarding import ensure_provisioned
from app.student import as_student, load_user
from app.templating import templates

router = APIRouter()


@router.get("/")
def index(request: Request) -> Any:
    if optional_user(request):
        return RedirectResponse("/home", status_code=303)
    return templates.TemplateResponse(request, "index.html")


@router.get("/home")
def home(request: Request, db: Session = Depends(get_db)) -> Any:
    user = load_user(request, db)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    s = get_settings()
    dashboard_url = f"{s.tb_public_url}/dashboards"
    device_count = 0
    if user.provisioning_state == "provisioned" and user.tb_user_id:
        with as_student(user) as (_sysadmin, student):
            device_count = len(student.list_devices())
            dash = student.find_dashboard("My devices")
            if dash and dash.id:
                dashboard_url = f"{s.tb_public_url}/dashboards/{dash.id.id}"
    ctx = {"user": user, "device_count": device_count, "dashboard_url": dashboard_url}
    return templates.TemplateResponse(request, "home.html", ctx)


@router.post("/home/provision")
def retry_provision(request: Request, db: Session = Depends(get_db)) -> Any:
    user = load_user(request, db)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    ensure_provisioned(db, user)
    return RedirectResponse("/home", status_code=303)
