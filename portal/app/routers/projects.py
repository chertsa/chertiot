"""Project routes (D13/M5.1): create a project (→ a TB tenant), the project workspace, its live
dashboard fragment, and delete. Tools (devices, flows, alerts, lora) live under /projects/{id}/…."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import permissions
from app.config import get_settings
from app.csrf import require_same_origin
from app.dashboard import alarm_history, dashboard_data
from app.db import get_db
from app.models import Project, ProjectJoinRequest, ProjectMember
from app.project import (
    accept_invite,
    as_project,
    create_invite,
    create_project,
    delete_project,
    join_requests,
    members,
    membership,
    pending_invites,
    remove_member,
    request_to_join,
    require_membership,
    resolve_join_request,
    retry_provision,
    set_member_status,
)
from app.student import load_user
from app.templating import templates

router = APIRouter()

# Portal locale → ThingsBoard UI locale (TB reads user.additionalInfo.lang).
_TB_LOCALE = {"ar": "ar_AR", "en": "en_US"}


def _require_owner(request: Request, db: Session, project_id: str) -> tuple[Project, ProjectMember]:
    user, project, member = require_membership(request, db, project_id)
    if not permissions.project_can(member, permissions.Cap.MEMBER_MANAGE):  # owner-only
        raise HTTPException(status_code=403, detail="owner only")
    return project, member


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
    """The project workspace. Non-members see a join page; the owner sees member management."""
    user = load_user(request, db)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    project = db.get(Project, project_id)
    if project is None:
        return RedirectResponse("/home", status_code=303)
    member = membership(db, project_id, user.id)
    if member is None or member.status != "active":
        # Not a member (or disabled): offer to request to join.
        pending = db.scalar(
            select(ProjectJoinRequest).where(
                ProjectJoinRequest.project_id == project_id,
                ProjectJoinRequest.user_id == user.id,
                ProjectJoinRequest.status == "pending",
            )
        )
        disabled = member is not None and member.status == "disabled"
        return templates.TemplateResponse(
            request,
            "project_join.html",
            {
                "user": user,
                "project": project,
                "requested": pending is not None,
                "disabled": disabled,
            },
        )
    is_owner = member.role == "owner"
    ctx = {
        "user": user,
        "project": project,
        "member": member,
        "is_owner": is_owner,
    }
    return templates.TemplateResponse(request, "project.html", ctx)


@router.get("/projects/{project_id}/settings")
def settings(request: Request, project_id: str, db: Session = Depends(get_db)) -> Any:
    """Members & settings: the protected home for member management, starter-dashboard reset and
    permanent deletion — kept off the operational Overview. Any active member sees it; destructive
    controls are owner-only (enforced again server-side on each action route)."""
    user, project, member = require_membership(request, db, project_id)
    is_owner = member.role == "owner"
    ctx = {
        "user": user,
        "project": project,
        "member": member,
        "is_owner": is_owner,
        "members": members(db, project_id),
        "invites": pending_invites(db, project_id) if is_owner else [],
        "requests": join_requests(db, project_id) if is_owner else [],
        "invite_base": str(request.base_url).rstrip("/"),
    }
    return templates.TemplateResponse(request, "project_settings.html", ctx)


@router.get("/projects/{project_id}/notebooks")
def notebooks(request: Request, project_id: str, db: Session = Depends(get_db)) -> Any:
    """Launch this project's notebook (per-project named server). Membership is enforced here (303
    for non-members) and again by the hub's pre_spawn_hook; if the lab is disabled or the hub is
    unreachable the user gets a controlled portal page, never a raw JupyterHub error."""
    from app import lab

    user, project, member = require_membership(request, db, project_id)
    if not lab.enabled() or not lab.healthy():
        return templates.TemplateResponse(
            request,
            "notebooks_unavailable.html",
            {
                "user": user,
                "project": project,
                "member": member,
                "is_owner": member.role == "owner",
            },
            status_code=503,
        )
    return RedirectResponse(lab.spawn_url(user.email, project.id), status_code=303)


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


@router.get("/projects/{project_id}/report")
def report(request: Request, project_id: str, db: Session = Depends(get_db)) -> Any:
    """A per-project lifecycle report: KPIs, device roster, alarm history, 24h chart, membership."""
    user, project, member = require_membership(request, db, project_id)
    ctx: dict[str, Any] = {
        "user": user,
        "project": project,
        "unavailable": False,
        "members": members(db, project_id),
        "alarm_history": [],
    }
    try:
        with as_project(member) as (sysadmin, session):
            ctx.update(dashboard_data(sysadmin, session))
            ctx["alarm_history"] = alarm_history(session)
    except Exception:  # noqa: BLE001
        ctx["unavailable"] = True
    return templates.TemplateResponse(request, "project_report.html", ctx)


@router.get("/projects/{project_id}/thingsboard")
def open_thingsboard(request: Request, project_id: str, db: Session = Depends(get_db)) -> Any:
    """Open the project's ThingsBoard console as this member: set the TB UI language to match the
    portal, mint their project-tenant session, and hand the JWT to the TB origin via /chert-login
    (fragment, never logged)."""
    from urllib.parse import quote

    from app.i18n import locale_of

    user, project, member = require_membership(request, db, project_id)
    s = get_settings()
    tb_lang = _TB_LOCALE.get(locale_of(request), "en_US")
    with as_project(member) as (_sysadmin, session):
        # TB reads user.additionalInfo.lang, so the console opens in the portal's language.
        try:
            me = session._get(f"/user/{member.tb_user_id}")  # noqa: SLF001
            cur = (me.get("additionalInfo") or {}).get("lang") if isinstance(me, dict) else None
            if isinstance(me, dict) and cur != tb_lang:
                me.setdefault("additionalInfo", {})["lang"] = tb_lang
                session._post("/user", me)  # noqa: SLF001
        except Exception:  # noqa: BLE001,S110 - never block opening the console
            pass
        jwt = session._tokens.token if session._tokens else ""  # noqa: SLF001
        refresh = session._tokens.refresh_token if session._tokens else ""  # noqa: SLF001
    url = f"{s.tb_public_url}/chert-login#jwt={quote(jwt)}&refresh={quote(refresh)}"
    return RedirectResponse(url, status_code=303)


@router.post("/projects/{project_id}/delete")
def delete(request: Request, project_id: str, db: Session = Depends(get_db)) -> Any:
    require_same_origin(request)
    user, project, member = require_membership(request, db, project_id)
    if not permissions.project_can(member, permissions.Cap.PROJECT_DELETE):
        raise HTTPException(status_code=403, detail="only the owner can delete a project")
    delete_project(db, project, user.email)
    return RedirectResponse("/home", status_code=303)


# ------------------------------------------------------------------------ collaboration (M5.6) ----
@router.post("/projects/{project_id}/invite")
def invite(
    request: Request,
    project_id: str,
    email: Annotated[str, Form()],
    db: Session = Depends(get_db),
) -> Any:
    require_same_origin(request)
    project, _owner = _require_owner(request, db, project_id)
    if "@" in email and len(email) <= 320:
        create_invite(db, project, load_user(request, db), email)  # type: ignore[arg-type]
    return RedirectResponse(f"/projects/{project_id}", status_code=303)


@router.get("/invite/{token}")
def accept_invite_link(request: Request, token: str, db: Session = Depends(get_db)) -> Any:
    """Open an invite link. Requires login (with the invited email); then joins and opens it."""
    user = load_user(request, db)
    if user is None:
        request.session["after_login"] = f"/invite/{token}"
        return RedirectResponse("/login", status_code=303)
    project = accept_invite(db, token, user)
    if project is None:
        return templates.TemplateResponse(
            request,
            "error.html",
            {
                "title": "Invite not valid",
                "message": "This invite has expired, was already used, "
                "or was sent to a different email address.",
            },
            status_code=404,
        )
    return RedirectResponse(f"/projects/{project.id}", status_code=303)


@router.post("/projects/{project_id}/join")
def join(request: Request, project_id: str, db: Session = Depends(get_db)) -> Any:
    user = load_user(request, db)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    project = db.get(Project, project_id)
    if project is None:
        return RedirectResponse("/home", status_code=303)
    if membership(db, project_id, user.id) is None:
        request_to_join(db, project, user)
    return RedirectResponse(f"/projects/{project_id}", status_code=303)


@router.post("/projects/{project_id}/requests/{req_id}/{decision}")
def resolve_request(
    request: Request, project_id: str, req_id: str, decision: str, db: Session = Depends(get_db)
) -> Any:
    require_same_origin(request)
    project, _owner = _require_owner(request, db, project_id)
    req = db.get(ProjectJoinRequest, req_id)
    if req and req.project_id == project_id and req.status == "pending":
        resolve_join_request(db, project, req, approve=(decision == "approve"))
    return RedirectResponse(f"/projects/{project_id}", status_code=303)


@router.post("/projects/{project_id}/members/{member_id}/{action}")
def manage_member(
    request: Request, project_id: str, member_id: str, action: str, db: Session = Depends(get_db)
) -> Any:
    require_same_origin(request)
    project, owner_member = _require_owner(request, db, project_id)
    target = db.get(ProjectMember, member_id)
    if target is None or target.project_id != project_id or target.role == "owner":
        # never disable/remove an owner through this path
        return RedirectResponse(f"/projects/{project_id}", status_code=303)
    if action == "disable":
        set_member_status(db, project, target, active=False)
    elif action == "enable":
        set_member_status(db, project, target, active=True)
    elif action == "remove":
        remove_member(db, project, target)
    return RedirectResponse(f"/projects/{project_id}", status_code=303)
