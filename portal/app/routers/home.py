from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app import permissions
from app.auth import optional_user
from app.config import get_settings
from app.db import get_db
from app.i18n import translator
from app.project import projects_for
from app.site_content import site_content
from app.student import load_user
from app.templating import templates

router = APIRouter()


def _safe_next(value: str | None) -> str | None:
    """Only same-site relative paths ("/login"), never "//host" or absolute URLs (open redirect)."""
    if value and value.startswith("/") and not value.startswith("//") and "\\" not in value:
        return value
    return None


@router.get("/lang/{code}")
def set_language(code: str, request: Request, next: str | None = None) -> Any:
    """Language toggle (Design System §7). Cookie-based; falls back to Accept-Language.
    `next` (relative path) lets the Keycloak sign-in page switch language through the portal and
    come straight back to /login in the new language."""
    target = _safe_next(next) or request.headers.get("referer") or "/"
    resp = RedirectResponse(target, status_code=303)
    if code in ("en", "ar"):
        resp.set_cookie("lang", code, max_age=365 * 24 * 3600, samesite="lax")
    return resp


@router.get("/grafana")
def grafana_launch(request: Request, db: Session = Depends(get_db)) -> Any:
    """Server-side authorisation for platform Grafana: only instructors/admins may launch it (the
    home card is also hidden for students, but this route is the enforced boundary). Grafana itself
    is reached via CHERT SSO at grafana.<domain>."""
    user = load_user(request, db)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    if not permissions.platform_can(user, permissions.Cap.PLATFORM_MONITORING):
        return templates.TemplateResponse(
            request,
            "error.html",
            {
                "user": user,
                "title": "Platform monitoring is staff-only",
                "message": "Grafana shows platform-wide infrastructure metrics and is available to "
                "instructors and administrators. For your project's devices, telemetry and alarms, "
                "open Monitoring inside your project.",
            },
            status_code=403,
        )
    # Land directly on the platform overview dashboard (by UID; Grafana resolves the slug),
    # not the Grafana home page. `kiosk` shows only the dashboard body (panels + time
    # controls), with no nav/menu chrome.
    dash = "/d/chert-device-traffic?orgId=1&from=now-6h&to=now&timezone=browser&refresh=30s&kiosk"
    return RedirectResponse(f"https://grafana.{get_settings().domain}{dash}", status_code=303)


@router.get("/")
def index(request: Request) -> Any:
    if optional_user(request):
        return RedirectResponse("/home", status_code=303)
    return templates.TemplateResponse(
        request, "index.html", {"site": site_content(translator(request))}
    )


@router.get("/home")
def home(request: Request, db: Session = Depends(get_db)) -> Any:
    """The projects portfolio: the user's projects, each opening into its own workspace."""
    user = load_user(request, db)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    projects = [{"project": p, "role": m.role} for p, m in projects_for(db, user.id)]
    summary = {
        "total": len(projects),
        "owned": sum(1 for p in projects if p["role"] == "owner"),
        "member": sum(1 for p in projects if p["role"] != "owner"),
    }
    return templates.TemplateResponse(
        request,
        "home.html",
        {
            "user": user,
            "projects": projects,
            "summary": summary,
            "is_staff": permissions.is_staff(user),  # platform Grafana card is staff-only
        },
    )


def N_(message: str) -> str:  # noqa: N802 — gettext's conventional marker; Babel extracts N_()
    """Mark a string for catalog extraction without translating it here (translated per request)."""
    return message


# --- Explore the lab: every engine that powers CHERT IoT, grouped like the systems poster. ---
# access: open=live student link · admin=SSO/admin UI · lora=via the portal /lora flow ·
#         internal=runs only on the private Docker network (shown for learning) · dev=not in prod.
_SYSTEMS: list[dict[str, Any]] = [
    {
        "group": N_("Core platform"),
        "items": [
            {
                "name": "ThingsBoard CE",
                "ver": "4.3.1.4",
                "lic": "Apache-2.0",
                "access": "open",
                "url": "https://app.{d}",
                "desc": N_(
                    "The IoT core — devices, telemetry, dashboards, "
                    "rule chains, alarms. One tenant per project."
                ),
            },
            {
                "name": "Keycloak",
                "ver": "26.7.2",
                "lic": "Apache-2.0",
                "access": "admin",
                "url": "https://auth.{d}",
                "desc": N_("Identity & single sign-on for every app."),
            },
            {
                "name": "Portal (FastAPI)",
                "ver": "app",
                "lic": "—",
                "access": "open",
                "url": "https://{d}",
                "desc": N_("This site: devices, flows, lab, alerts, teach."),
            },
            {
                "name": "Docs (MkDocs)",
                "ver": "app",
                "lic": "—",
                "access": "open",
                "url": "https://{d}/docs/",
                "desc": N_("Getting-started guides (English & Arabic)."),
            },
            {
                "name": "Caddy + layer4",
                "ver": "2.11.4",
                "lic": "Apache-2.0",
                "access": "internal",
                "url": "",
                "desc": N_("Edge reverse proxy: TLS, routing, MQTTS on :8883."),
            },
        ],
    },
    {
        "group": N_("Observability & monitoring"),
        "items": [
            {
                "name": "Prometheus",
                "ver": "3.14.0",
                "lic": "Apache-2.0",
                "access": "internal",
                "url": "",
                "desc": N_("Collects metrics and evaluates alert rules."),
            },
            {
                "name": "Grafana",
                "ver": "13.1.4",
                "lic": "AGPL-3.0",
                "access": "open",
                "url": "https://grafana.{d}/d/chert-device-traffic?orgId=1&refresh=30s&kiosk",
                "desc": N_(
                    "Monitoring dashboards over Prometheus. Opens with your "
                    "CHERT sign-in — no separate password."
                ),
            },
            {
                "name": "Alertmanager",
                "ver": "0.34.0",
                "lic": "Apache-2.0",
                "access": "internal",
                "url": "",
                "desc": N_("Routes platform alerts to email."),
            },
            {
                "name": "Uptime Kuma",
                "ver": "1.23.17",
                "lic": "MIT",
                "access": "open",
                "url": "https://status.{d}/status/chert-iot",
                "desc": N_("Public status & uptime page."),
            },
            {
                "name": "node-exporter",
                "ver": "1.12.1",
                "lic": "Apache-2.0",
                "access": "internal",
                "url": "",
                "desc": N_("Host CPU/RAM/disk metrics."),
            },
            {
                "name": "cAdvisor",
                "ver": "0.55.1",
                "lic": "Apache-2.0",
                "access": "internal",
                "url": "",
                "desc": N_("Per-container metrics."),
            },
            {
                "name": "postgres-exporter",
                "ver": "0.20.1",
                "lic": "Apache-2.0",
                "access": "internal",
                "url": "",
                "desc": N_("Database metrics."),
            },
        ],
    },
    {
        "group": N_("IoT & LoRaWAN stack"),
        "items": [
            {
                "name": "ChirpStack",
                "ver": "4.19.1",
                "lic": "MIT",
                "access": "lora",
                "url": "https://{d}/lora",
                "desc": N_(
                    "LoRaWAN network server. Register devices from a project's LoRaWAN tab."
                ),
            },
            {
                "name": "ChirpStack Gateway Bridge",
                "ver": "4.1.2",
                "lic": "MIT",
                "access": "internal",
                "url": "",
                "desc": N_("Gateways send here: {d}:1700/udp (Semtech UDP, EU868)."),
            },
            {
                "name": "Eclipse Mosquitto",
                "ver": "2.0.22",
                "lic": "EPL-2.0",
                "access": "internal",
                "url": "",
                "desc": N_("MQTT broker between ChirpStack and the bridge."),
            },
            {
                "name": "Redis",
                "ver": "7.4.11",
                "lic": "BSD-3",
                "access": "internal",
                "url": "",
                "desc": N_("ChirpStack device-session & metrics store."),
            },
            {
                "name": "lora-bridge",
                "ver": "app",
                "lic": "—",
                "access": "internal",
                "url": "",
                "desc": N_("Forwards LoRa uplinks to your ThingsBoard device by DevEUI."),
            },
        ],
    },
    {
        "group": N_("Student tools — flows & lab"),
        "items": [
            {
                "name": "Node-RED",
                "ver": "5.0.6",
                "lic": "Apache-2.0",
                "access": "open",
                "url": "https://{d}/flows",
                "desc": N_("Your private low-code flow editor."),
            },
            {
                "name": "JupyterHub",
                "ver": "5.5.1",
                "lic": "BSD-3",
                "access": "open",
                "url": "https://lab.{d}",
                "desc": N_("Your Python notebooks — plot your own telemetry."),
            },
            {
                "name": "docker-socket-proxy",
                "ver": "0.5.0",
                "lic": "GPL-3.0",
                "access": "internal",
                "url": "",
                "desc": N_("Least-privilege Docker API used to spawn your flows/notebooks."),
            },
        ],
    },
    {
        "group": N_("Backup & dev"),
        "items": [
            {
                "name": "restic",
                "ver": "0.16",
                "lic": "BSD-2",
                "access": "internal",
                "url": "",
                "desc": N_("Nightly encrypted off-box backups."),
            },
            {
                "name": "Mailpit",
                "ver": "1.31.0",
                "lic": "MIT",
                "access": "dev",
                "url": "",
                "desc": N_("Local email capture for development only."),
            },
        ],
    },
]


@router.get("/explore")
def explore(request: Request, db: Session = Depends(get_db)) -> Any:
    """The lab hub: every open-source engine that powers CHERT IoT, with links where reachable."""
    user = load_user(request, db)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    d = get_settings().domain
    staff = permissions.is_staff(user)
    tr = translator(request)  # not `_`: Babel would extract the dict keys below as msgids
    groups = []
    for g in _SYSTEMS:
        items = []
        for it in g["items"]:
            # Platform Grafana is staff-only: students see the card (for learning) but not a link.
            staff_only = it["name"] == "Grafana" and not staff
            items.append(
                {
                    **it,
                    "href": "" if staff_only else (it["url"].format(d=d) if it["url"] else ""),
                    "hint": tr(it["desc"]).format(d=d),
                    "access": "admin" if staff_only else it["access"],
                }
            )
        groups.append({"group": tr(g["group"]), "items": items})
    total = sum(len(g["items"]) for g in _SYSTEMS)
    return templates.TemplateResponse(
        request, "explore.html", {"user": user, "groups": groups, "total": total}
    )
