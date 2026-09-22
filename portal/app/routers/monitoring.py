"""v2 Project Monitoring routes (portal-native, ThingsBoard-REST, tenant-scoped).

Every request: membership gate (403 non-member) → feature-flag guard (404 when off) → validated
query params → cache lookup only AFTER authorisation → tenant-scoped snapshot via the member's
impersonated session. Ack loads the alarm through that session (out-of-tenant → 404, proven),
determines severity server-side, applies the owner/critical policy, then acks. No `tb_tenant_id`
is ever serialised to the browser.
"""

from typing import Any
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from app import flows, monitoring
from app.audit import audit
from app.config import get_settings
from app.db import get_db
from app.project import as_project, require_api_membership, require_membership
from app.ratelimit import rate_limited
from app.tb_client import TbError
from app.templating import templates

router = APIRouter()


def _require_flag() -> None:
    if not get_settings().monitoring_enabled:
        raise HTTPException(status_code=404)


def _require_telemetry_flag() -> None:
    if not get_settings().telemetry_enabled:
        raise HTTPException(status_code=404)


def _node_red_state(project_id: str) -> str:
    try:
        if not flows.enabled():
            return "unknown"
        return "ok" if flows.ready(project_id) else "stopped"
    except Exception:  # noqa: BLE001
        return "unknown"


def _origin_ok(request: Request) -> None:
    """Lightweight same-origin (CSRF) guard for the ack mutation, on top of the SameSite=lax cookie:
    if the browser sent an Origin/Referer, its host must match the request host."""
    ref = request.headers.get("origin") or request.headers.get("referer") or ""
    host = request.headers.get("host", "")
    o = urlparse(ref).netloc
    if o and host and o != host:
        raise HTTPException(status_code=403, detail="cross-origin request rejected")


def _build(
    project: Any,
    member: Any,
    rng: str,
    device: str | None,
    key: str | None,
    with_activity: bool = False,
) -> Any:
    """Build (or return cached) snapshot. Caller MUST have authorised membership first.
    `with_activity` adds per-device throughput (Telemetry only) and caches separately."""
    nr = _node_red_state(project.id)
    ttl = get_settings().monitoring_cache_ttl
    cache_key = (project.id, rng, device or "", (key or "") + ("|act" if with_activity else ""))

    def builder() -> monitoring.MonitoringSnapshot:
        with as_project(member) as (sysadmin, session):
            return monitoring.snapshot(
                sysadmin,
                session,
                project.tb_tenant_id,
                rng,
                device,
                key,
                nr,
                with_activity=with_activity,
            )

    return monitoring.cached_snapshot(ttl, cache_key, builder)  # only reached after authorisation


@router.get("/projects/{project_id}/monitoring")
def monitoring_page(request: Request, project_id: str, db: Session = Depends(get_db)) -> Any:
    _require_flag()
    user, project, member = require_membership(request, db, project_id)  # non-member → 303 /home
    snap = _build(project, member, monitoring.DEFAULT_RANGE, None, None)
    audit(db, user.email, "monitoring.view", project.slug)
    db.commit()
    return templates.TemplateResponse(
        request,
        "monitoring.html",
        {
            "user": user,
            "project": project,
            "member": member,
            "is_owner": member.role == "owner",
            "snapshot": snap.model_dump(),
            "ranges": list(monitoring.RANGES),
        },
    )


@router.get(
    "/projects/{project_id}/monitoring/data",
    dependencies=[Depends(rate_limited("monitoring", 60, 60))],
)
def monitoring_data(
    request: Request,
    project_id: str,
    range: str = monitoring.DEFAULT_RANGE,
    device: str | None = None,
    key: str | None = None,
    db: Session = Depends(get_db),
) -> Any:
    _require_flag()
    if range not in monitoring.RANGES:
        raise HTTPException(status_code=400, detail="invalid range")
    _u, project, member = require_api_membership(request, db, project_id)  # non-member → 403
    snap = _build(project, member, range, device, key)
    return JSONResponse(snap.model_dump())


@router.get("/projects/{project_id}/telemetry")
def telemetry_page(
    request: Request,
    project_id: str,
    range: str = monitoring.DEFAULT_RANGE,
    device: str | None = None,
    key: str | None = None,
    db: Session = Depends(get_db),
) -> Any:
    _require_telemetry_flag()
    user, project, member = require_membership(request, db, project_id)  # non-member → 303 /home
    rng = range if range in monitoring.RANGES else monitoring.DEFAULT_RANGE
    snap = _build(project, member, rng, device, key, with_activity=True)
    audit(db, user.email, "telemetry.view", project.slug)
    db.commit()
    return templates.TemplateResponse(
        request,
        "telemetry.html",
        {
            "user": user,
            "project": project,
            "member": member,
            "snapshot": snap.model_dump(),
            "ranges": list(monitoring.RANGES),
        },
    )


@router.post(
    "/projects/{project_id}/monitoring/alarms/{alarm_id}/ack",
    dependencies=[Depends(rate_limited("monitoring-ack", 20, 60))],
)
def ack_alarm(
    request: Request, project_id: str, alarm_id: str, db: Session = Depends(get_db)
) -> Any:
    _require_flag()
    _origin_ok(request)
    user, project, member = require_api_membership(request, db, project_id)  # non-member → 403
    with as_project(member) as (_sysadmin, session):
        try:
            alarm = session._get(f"/alarm/info/{alarm_id}")  # noqa: SLF001 — 404/403 out-of-tenant
        except TbError as e:
            raise HTTPException(status_code=404) from e  # out-of-tenant / missing
        severity = (alarm or {}).get("severity", "") if isinstance(alarm, dict) else ""
        if severity == "CRITICAL" and member.role != "owner":
            raise HTTPException(
                status_code=403, detail="only the owner can acknowledge critical alarms"
            )
        session._post(f"/alarm/{alarm_id}/ack")  # noqa: SLF001
    monitoring.invalidate(project.id)
    audit(db, user.email, "alarm.ack", project.slug, alarm_id=alarm_id, severity=severity)
    db.commit()
    return RedirectResponse(f"/projects/{project.id}/monitoring", status_code=303)
