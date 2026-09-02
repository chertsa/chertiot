from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app import flows
from app.audit import audit
from app.config import get_settings
from app.db import get_db
from app.i18n import translator
from app.models import FlowInstance
from app.student import load_user, require_provisioned
from app.templating import templates

router = APIRouter()


def _flows_host(request: Request) -> str:
    base = get_settings().domain
    scheme = "http" if get_settings().env == "dev" else "https"
    return f"{scheme}://flows.{base}"


@router.get("/flows")
def flows_page(request: Request, db: Session = Depends(get_db)) -> Any:
    user = require_provisioned(request, db)
    _ = translator(request)
    if not flows.enabled():
        ctx = {"user": user, "enabled": False, "state": "absent", "editor_url": ""}
        return templates.TemplateResponse(request, "flows.html", ctx)
    state = flows.status(user.id)
    ctx = {
        "user": user,
        "enabled": True,
        "state": state,
        "editor_url": f"{_flows_host(request)}/u/{user.id}/",
    }
    return templates.TemplateResponse(request, "flows.html", ctx)


@router.post("/flows/start")
def flows_start(request: Request, db: Session = Depends(get_db)) -> Any:
    user = require_provisioned(request, db)
    if not flows.enabled():
        return RedirectResponse("/flows", status_code=303)
    s = get_settings()
    flows.spawn(user, s.device_mqtt_host, s.mqtt_port)
    inst = db.get(FlowInstance, user.id) or FlowInstance(
        user_id=user.id, container_name=flows.container_name(user.id)
    )
    inst.state, inst.last_active = "running", datetime.now(UTC)
    db.add(inst)
    audit(db, user.email, "flows.start")
    db.commit()
    return RedirectResponse("/flows", status_code=303)


@router.post("/flows/stop")
def flows_stop(request: Request, db: Session = Depends(get_db)) -> Any:
    user = require_provisioned(request, db)
    flows.stop(user.id)
    inst = db.get(FlowInstance, user.id)
    if inst:
        inst.state = "stopped"
    audit(db, user.email, "flows.stop")
    db.commit()
    return RedirectResponse("/flows", status_code=303)


@router.get("/flows/auth")
def flows_auth(request: Request, db: Session = Depends(get_db)) -> Response:
    """Caddy forward_auth target: 200 only when the platform session owns the requested
    /u/<id>/ path.
    This is the whole isolation story for the editors — no cookie, wrong user, no access."""
    user = load_user(request, db)
    original = request.headers.get("x-forwarded-uri", "")
    if user is None:
        return Response(status_code=401)
    if not original.startswith(f"/u/{user.id}/") and original != f"/u/{user.id}":
        return Response(status_code=403)
    inst = db.get(FlowInstance, user.id)
    if inst:
        inst.last_active = datetime.now(UTC)
        db.commit()
    return Response(status_code=200, headers={"X-Flows-User": user.id})
