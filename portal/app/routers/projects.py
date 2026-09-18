"""Project routes (D13/M5.1): create a project (→ a TB tenant), the project workspace, its live
dashboard fragment, and delete. Tools (devices, flows, alerts, lora) live under /projects/{id}/…."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.dashboard import dashboard_data
from app.db import get_db
from app.models import Project
from app.project import (
    as_project,
    create_project,
    delete_project,
    membership,
    require_membership,
    retry_provision,
)
from app.student import load_user
from app.templating import templates

router = APIRouter()


@router.get("/projects/new")
def new_project(request: Request, db: Session = Depends(get_db), error: str = "") -> Any:
    user = load_user(request, db)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    return templates.TemplateResponse(request, "project_new.html", {"user": user, "error": error})


@router.post("/projects")
def create(
    request: Request,
    name: Annotated[str, Form()],
    description: Annotated[str, Form()] = "",
    db: Session = Depends(get_db),
) -> Any:
    user = load_user(request, db)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    name = name.strip()
    if not (2 <= len(name) <= 120):
        return RedirectResponse("/projects/new?error=Give+your+project+a+name+(2-120+chars)", 303)
    project = create_project(db, user, name, description)
    return RedirectResponse(f"/projects/{project.id}", 303)


@router.get("/projects/{project_id}")
def workspace(request: Request, project_id: str, db: Session = Depends(get_db)) -> Any:
    """The project workspace. Renders even when provisioning failed (offers a retry)."""
    user = load_user(request, db)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    project = db.get(Project, project_id)
    member = membership(db, project_id, user.id) if project else None
    if project is None or member is None or member.status != "active":
        return RedirectResponse("/home", status_code=303)
    ctx = {"user": user, "project": project, "member": member, "is_owner": member.role == "owner"}
    return templates.TemplateResponse(request, "project.html", ctx)


@router.post("/projects/{project_id}/provision")
def provision(request: Request, project_id: str, db: Session = Depends(get_db)) -> Any:
    user = load_user(request, db)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    project = db.get(Project, project_id)
    member = membership(db, project_id, user.id) if project else None
    if project is None or member is None:
        return RedirectResponse("/home", status_code=303)
    retry_provision(db, project, user, member)
    return RedirectResponse(f"/projects/{project_id}", 303)


@router.get("/projects/{project_id}/panel")
def panel(request: Request, project_id: str, db: Session = Depends(get_db)) -> Any:
    """Live dashboard fragment (KPIs, chart, devices, alarms). Always 200 — degrades gracefully."""
    user, project, member = require_membership(request, db, project_id)
    ctx: dict[str, Any] = {"unavailable": False, "project": project}
    try:
        with as_project(member) as (sysadmin, session):
            ctx.update(dashboard_data(sysadmin, session))
    except Exception:  # noqa: BLE001 - upstream slow/down: degrade, don't 503
        ctx["unavailable"] = True
    return templates.TemplateResponse(request, "home_panel.html", ctx)


@router.post("/projects/{project_id}/delete")
def delete(request: Request, project_id: str, db: Session = Depends(get_db)) -> Any:
    user, project, member = require_membership(request, db, project_id)
    if member.role != "owner":
        raise HTTPException(status_code=403, detail="only the owner can delete a project")
    delete_project(db, project, user.email)
    return RedirectResponse("/home", status_code=303)
