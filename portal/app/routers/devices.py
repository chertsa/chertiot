import re
import secrets
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import PlainTextResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.audit import audit
from app.config import get_settings
from app.db import get_db
from app.provisioning import ensure_starter_dashboard
from app.snippets import TRACKS, placeholders, render
from app.student import as_student, require_provisioned
from app.tb_client import Device, TbClient, TbError
from app.templating import templates

router = APIRouter()
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _-]{1,47}$")


def _device_rows(sysadmin: TbClient, student: TbClient) -> list[dict[str, Any]]:
    rows = []
    for d in student.list_devices():
        if not d.id:
            continue
        attrs = student.server_attributes(d.id.id, ["active", "lastActivityTime"])
        last = attrs.get("lastActivityTime")
        rows.append(
            {
                "id": d.id.id,
                "name": d.name,
                "label": d.label or "",
                "active": bool(attrs.get("active")),
                "last_seen": datetime.fromtimestamp(int(last) / 1000, UTC) if last else None,
            }
        )
    return rows


def _max_devices(sysadmin: TbClient, tenant_id: str | None) -> int | None:
    if not tenant_id:
        return None
    tenant = sysadmin.get_tenant(tenant_id)
    if not tenant.tenant_profile_id:
        return None
    profile = next(
        (p for p in sysadmin.list_tenant_profiles() if p.id == tenant.tenant_profile_id), None
    )
    limit = profile.profile_data.get("configuration", {}).get("maxDevices") if profile else None
    return int(limit) if limit else None  # 0 = unlimited in TB


@router.get("/devices")
def list_devices(request: Request, db: Session = Depends(get_db), error: str = "") -> Any:
    user = require_provisioned(request, db)
    with as_student(user) as (sysadmin, student):
        rows = _device_rows(sysadmin, student)
        limit = _max_devices(sysadmin, user.tb_tenant_id)
    ctx = {"user": user, "devices": rows, "limit": limit, "used": len(rows), "error": error}
    return templates.TemplateResponse(request, "devices.html", ctx)


@router.post("/devices")
def create_device(
    request: Request, name: Annotated[str, Form()], db: Session = Depends(get_db)
) -> Any:
    user = require_provisioned(request, db)
    name = name.strip()
    if not NAME_RE.match(name):
        return RedirectResponse(
            "/devices?error=Device+names+are+2-48+letters,+digits,+spaces,+_+or+-", 303
        )
    with as_student(user) as (sysadmin, student):
        limit = _max_devices(sysadmin, user.tb_tenant_id)
        if limit and len(student.list_devices()) >= limit:
            return RedirectResponse(
                f"/devices?error=You+have+reached+your+limit+of+{limit}+devices", 303
            )
        try:
            device = student.save_device(Device(name=name, type="default"))
        except TbError as e:
            msg = "A device with that name already exists" if "exists" in e.message else e.message
            return RedirectResponse(f"/devices?error={msg.replace(' ', '+')}", 303)
    audit(db, user.email, "device.create", name)
    db.commit()
    return RedirectResponse(f"/devices/{device.id.id if device.id else ''}", 303)


@router.get("/devices/{device_id}")
def device_detail(request: Request, device_id: str, db: Session = Depends(get_db)) -> Any:
    user = require_provisioned(request, db)
    s = get_settings()
    with as_student(user) as (sysadmin, student):
        try:
            device = student.get_device(device_id)  # 404/403 if not in this tenant
        except TbError as e:
            raise HTTPException(status_code=404, detail="device not found") from e
        creds = student.get_device_credentials(device_id)
        attrs = student.server_attributes(device_id, ["active", "lastActivityTime"])
    last = attrs.get("lastActivityTime")
    ctx = {
        "user": user,
        "device": device,
        "token": creds.credentials_id,
        "active": bool(attrs.get("active")),
        "last_seen": datetime.fromtimestamp(int(last) / 1000, UTC) if last else None,
        "tracks": list(TRACKS.values()),
        "snippets": {k: render(k, device.name, creds.credentials_id, s) for k in TRACKS},
        "conn": placeholders(device.name, creds.credentials_id, s),
    }
    return templates.TemplateResponse(request, "device.html", ctx)


@router.get("/devices/{device_id}/snippet/{track}")
def download_snippet(
    request: Request, device_id: str, track: str, db: Session = Depends(get_db)
) -> Any:
    user = require_provisioned(request, db)
    if track not in TRACKS:
        raise HTTPException(status_code=404)
    with as_student(user) as (sysadmin, student):
        try:
            device = student.get_device(device_id)
        except TbError as e:
            raise HTTPException(status_code=404) from e
        creds = student.get_device_credentials(device_id)
    body = render(track, device.name, creds.credentials_id)
    headers = {"Content-Disposition": f'attachment; filename="{TRACKS[track].filename}"'}
    return PlainTextResponse(body, headers=headers)


@router.post("/devices/{device_id}/rename")
def rename_device(
    request: Request, device_id: str, name: Annotated[str, Form()], db: Session = Depends(get_db)
) -> Any:
    user = require_provisioned(request, db)
    name = name.strip()
    if not NAME_RE.match(name):
        raise HTTPException(status_code=422, detail="invalid name")
    with as_student(user) as (sysadmin, student):
        device = student.get_device(device_id)
        old = device.name
        device.name = name
        student.save_device(device)
    audit(db, user.email, "device.rename", name, old=old)
    db.commit()
    return RedirectResponse(f"/devices/{device_id}", 303)


@router.post("/devices/{device_id}/revoke")
def revoke_token(request: Request, device_id: str, db: Session = Depends(get_db)) -> Any:
    """Rotate the access token: the old one stops working immediately (lost/leaked token)."""
    user = require_provisioned(request, db)
    with as_student(user) as (sysadmin, student):
        student.get_device(device_id)
        student.rotate_device_token(device_id, secrets.token_urlsafe(15)[:20])
    audit(db, user.email, "device.token_rotated", device_id)
    db.commit()
    return RedirectResponse(f"/devices/{device_id}", 303)


@router.post("/devices/{device_id}/delete")
def delete_device(request: Request, device_id: str, db: Session = Depends(get_db)) -> Any:
    user = require_provisioned(request, db)
    with as_student(user) as (sysadmin, student):
        device = student.get_device(device_id)
        student.delete_device(device_id)
    audit(db, user.email, "device.delete", device.name)
    db.commit()
    return RedirectResponse("/devices", 303)


@router.post("/dashboard/reset")
def reset_dashboard(request: Request, db: Session = Depends(get_db)) -> Any:
    """Re-import the starter dashboard over the student's copy (D5)."""
    user = require_provisioned(request, db)
    with as_student(user) as (sysadmin, student):
        ensure_starter_dashboard(student, reset=True)
    audit(db, user.email, "dashboard.reset")
    db.commit()
    return RedirectResponse("/home", 303)
