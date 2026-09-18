from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import lora as lora_mod
from app.audit import audit
from app.config import get_settings
from app.db import get_db
from app.models import LoraDevice
from app.project import require_membership
from app.templating import templates

router = APIRouter()


@router.get("/projects/{project_id}/lora")
def lora_page(request: Request, project_id: str, db: Session = Depends(get_db)) -> Any:
    user, project, member = require_membership(request, db, project_id)
    devices = list(db.scalars(select(LoraDevice).where(LoraDevice.project_id == project.id)))
    ctx = {
        "user": user,
        "project": project,
        "enabled": lora_mod.enabled(),
        "devices": devices,
        "domain": get_settings().domain,
    }
    return templates.TemplateResponse(request, "lora.html", ctx)


@router.post("/projects/{project_id}/lora")
def add_lora_device(request: Request, project_id: str, db: Session = Depends(get_db)) -> Any:
    user, project, member = require_membership(request, db, project_id)
    if lora_mod.enabled():
        mapping = lora_mod.register(db, project, member)
        audit(db, user.email, "lora.register", mapping.dev_eui)
        db.commit()
    return RedirectResponse(f"/projects/{project.id}/lora", status_code=303)
