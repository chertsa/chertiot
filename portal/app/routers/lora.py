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
from app.student import require_provisioned
from app.templating import templates

router = APIRouter()


@router.get("/lora")
def lora_page(request: Request, db: Session = Depends(get_db)) -> Any:
    user = require_provisioned(request, db)
    devices = list(db.scalars(select(LoraDevice).where(LoraDevice.user_id == user.id)))
    ctx = {
        "user": user,
        "enabled": lora_mod.enabled(),
        "devices": devices,
        "domain": get_settings().domain,
    }
    return templates.TemplateResponse(request, "lora.html", ctx)


@router.post("/lora")
def add_lora_device(request: Request, db: Session = Depends(get_db)) -> Any:
    user = require_provisioned(request, db)
    if lora_mod.enabled():
        mapping = lora_mod.register(db, user)
        audit(db, user.email, "lora.register", mapping.dev_eui)
        db.commit()
    return RedirectResponse("/lora", status_code=303)
