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
from app.project import membership, require_membership
from app.student import load_user
from app.templating import templates

router = APIRouter()


def _flows_host(request: Request) -> str:
    base = get_settings().domain
    scheme = "http" if get_settings().env == "dev" else "https"
    return f"{scheme}://flows.{base}"


@router.get("/projects/{project_id}/flows")
def flows_page(project_id: str, request: Request, db: Session = Depends(get_db)) -> Any:
    user, project, member = require_membership(request, db, project_id)
    _ = translator(request)
    if not flows.enabled():
        ctx = {
            "user": user,
            "project": project,
            "enabled": False,
            "state": "absent",
            "editor_url": "",
        }
        return templates.TemplateResponse(request, "flows.html", ctx)
    ctx = {
        "user": user,
        "project": project,
        "enabled": True,
        "state": flows.state(project.id),
        "editor_url": f"{_flows_host(request)}/u/{project.id}/",
    }
    return templates.TemplateResponse(request, "flows.html", ctx)


@router.get("/projects/{project_id}/flows/ready")
def flows_ready(project_id: str, request: Request, db: Session = Depends(get_db)) -> Any:
    """Polled by the 'building…' page; 200 {"ready": bool} once Node-RED is serving."""
    _user, project, _member = require_membership(request, db, project_id)
    return {"ready": flows.enabled() and flows.ready(project.id)}


@router.post("/projects/{project_id}/flows/start")
def flows_start(project_id: str, request: Request, db: Session = Depends(get_db)) -> Any:
    user, project, member = require_membership(request, db, project_id)
    if not flows.enabled():
        return RedirectResponse(f"/projects/{project.id}/flows", status_code=303)
    s = get_settings()
    flows.spawn(project, member, s.device_mqtt_host, s.mqtt_port)
    inst = db.get(FlowInstance, project.id) or FlowInstance(
        project_id=project.id, container_name=flows.container_name(project.id)
    )
    inst.state, inst.last_active = "running", datetime.now(UTC)
    db.add(inst)
    audit(db, user.email, "flows.start")
    db.commit()
    return RedirectResponse(f"/projects/{project.id}/flows", status_code=303)


@router.post("/projects/{project_id}/flows/stop")
def flows_stop(project_id: str, request: Request, db: Session = Depends(get_db)) -> Any:
    user, project, _member = require_membership(request, db, project_id)
    flows.stop(project.id)
    inst = db.get(FlowInstance, project.id)
    if inst:
        inst.state = "stopped"
    audit(db, user.email, "flows.stop")
    db.commit()
    return RedirectResponse(f"/projects/{project.id}/flows", status_code=303)


@router.get("/flows/auth")
def flows_auth(request: Request, db: Session = Depends(get_db)) -> Response:
    """Caddy forward_auth target: 200 only when the platform session belongs to an active member
    of the project whose /u/<project_id>/ path is requested.
    This is the whole isolation story for the editors — no cookie, no membership, no access."""
    user = load_user(request, db)
    if user is None:
        return Response(status_code=401)
    # Primary check: the project id Caddy captured from /u/<id>/ (reliable for WebSocket upgrades,
    # where X-Forwarded-Uri arrives empty). Fall back to the URI for plain requests.
    project_id = request.headers.get("x-flows-uid", "")
    if not project_id:
        original = request.headers.get("x-forwarded-uri", "")
        marker = "/u/"
        if original.startswith(marker):
            project_id = original[len(marker) :].split("/", 1)[0]
    member = membership(db, project_id, user.id) if project_id else None
    if member is None or member.status != "active":
        return Response(status_code=403)
    inst = db.get(FlowInstance, project_id)
    if inst:
        inst.last_active = datetime.now(UTC)
        db.commit()
    return Response(status_code=200, headers={"X-Flows-User": user.id})
