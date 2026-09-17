from typing import Any
from urllib.parse import quote, urlparse

import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.auth import optional_user
from app.config import get_settings
from app.db import get_db
from app.i18n import locale_of
from app.onboarding import ensure_provisioned
from app.student import as_student, load_user
from app.templating import templates

# Portal locale → ThingsBoard UI locale. TB reads user.additionalInfo.lang first when authenticated.
_TB_LOCALE = {"ar": "ar_AE", "en": "en_US"}

router = APIRouter()

# TB's OAuth2 authorization URL (…/oauth2/authorization/<id>), resolved once and cached.
# Routing "Open my dashboard" through it means students land via Keycloak SSO instead of TB's
# own login form (where a password attempt fails with "User account is not active" — D3, SSO-only).
_tb_sso_base: str | None = None


def _sso_authorization_url(s: Any) -> str | None:
    global _tb_sso_base
    if _tb_sso_base:
        return _tb_sso_base
    # TB only lists the client when the request Host matches its Domain record (app.<domain>).
    host = urlparse(s.tb_public_url).hostname
    try:
        r = httpx.post(
            f"{s.tb_admin_url}/api/noauth/oauth2Clients",
            json={},
            headers={"Host": host} if host else {},
            timeout=5,
        )
        clients = r.json() if r.status_code == 200 else []
        if clients:
            _tb_sso_base = f"{s.tb_public_url}{clients[0]['url']}"
    except Exception:
        _tb_sso_base = None
    return _tb_sso_base


@router.get("/lang/{code}")
def set_language(code: str, request: Request) -> Any:
    """Language toggle (Design System §7). Cookie-based; falls back to Accept-Language."""
    target = request.headers.get("referer") or "/"
    resp = RedirectResponse(target, status_code=303)
    if code in ("en", "ar"):
        resp.set_cookie("lang", code, max_age=365 * 24 * 3600, samesite="lax")
    return resp


@router.get("/")
def index(request: Request) -> Any:
    if optional_user(request):
        return RedirectResponse("/home", status_code=303)
    return templates.TemplateResponse(request, "index.html")


@router.get("/home")
def home(request: Request, db: Session = Depends(get_db)) -> Any:
    """Fast shell: renders instantly. The live panel loads async via /home/panel so a slow
    ThingsBoard never 503s the page."""
    user = load_user(request, db)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    # "Open full dashboard" goes through /dashboard/open so TB opens in the portal's language.
    return templates.TemplateResponse(request, "home.html", {"user": user})


@router.get("/dashboard/open")
def open_dashboard(request: Request, db: Session = Depends(get_db)) -> Any:
    """Set the student's ThingsBoard UI language to match the portal, then SSO into their dashboard.
    TB reads user.additionalInfo.lang first, so the console opens in the portal language."""
    user = load_user(request, db)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    s = get_settings()
    tb_lang = _TB_LOCALE.get(locale_of(request), "en_US")
    dash_path = "/dashboards"
    if user.provisioning_state == "provisioned" and user.tb_user_id:
        try:
            with as_student(user) as (_sysadmin, student):
                me = student._get(f"/user/{user.tb_user_id}")  # noqa: SLF001
                cur = (me.get("additionalInfo") or {}).get("lang") if isinstance(me, dict) else None
                if isinstance(me, dict) and cur != tb_lang:
                    me.setdefault("additionalInfo", {})["lang"] = tb_lang
                    student._post("/user", me)  # noqa: SLF001
                dash = student.find_dashboard("My devices")
                if dash and dash.id:
                    dash_path = f"/dashboards/{dash.id.id}"
        except Exception:  # noqa: BLE001,S110 - never block opening the dashboard
            pass
    sso = _sso_authorization_url(s)
    url = f"{sso}?prevUri={quote(dash_path, safe='')}" if sso else f"{s.tb_public_url}{dash_path}"
    return RedirectResponse(url, status_code=303)


@router.get("/home/panel")
def home_panel(request: Request, db: Session = Depends(get_db)) -> Any:
    """Live dashboard fragment (KPIs, chart, devices, alarms). Always returns 200 — on any upstream
    trouble it renders a small 'live data unavailable' state instead of taking the page down."""
    user = load_user(request, db)
    if user is None or user.provisioning_state != "provisioned" or not user.tb_user_id:
        return templates.TemplateResponse(request, "home_panel.html", {"unavailable": True})
    ctx: dict[str, Any] = {
        "device_count": 0,
        "online_count": 0,
        "max_devices": None,
        "alarm_count": 0,
        "devices": [],
        "alarms": [],
        "chart": None,
        "unavailable": False,
    }
    try:
        with as_student(user) as (sysadmin, student):
            ctx.update(_dashboard_data(sysadmin, student, user))
    except Exception:  # noqa: BLE001 - upstream slow/down: degrade, don't 503
        ctx["unavailable"] = True
    return templates.TemplateResponse(request, "home_panel.html", ctx)


# Common numeric telemetry keys we surface on the dashboard (one Entity Data Query, not N calls).
_TS_KEYS = [
    "temperature",
    "humidity",
    "soil_moisture",
    "level_pct",
    "power_w",
    "wind_speed",
    "battery",
]
_max_devices_cache: dict[str, Any] = {"ts": 0.0, "value": None}


def _dashboard_data(sysadmin: Any, student: Any, user: Any) -> dict[str, Any]:
    """Gather live metrics in a few calls (Entity Data Query for devices+status+latest, one
    alarms call, one chart call) to stay well under the tenant REST rate limit. Defensive."""
    import json
    import time as _time
    from datetime import UTC, datetime

    out: dict[str, Any] = {}
    # 1) devices + active/lastActivityTime + latest telemetry in ONE query
    query = {
        "entityFilter": {"type": "entityType", "entityType": "DEVICE"},
        "pageLink": {
            "pageSize": 30,
            "page": 0,
            "sortOrder": {"key": {"type": "ENTITY_FIELD", "key": "name"}, "direction": "ASC"},
        },
        "entityFields": [
            {"type": "ENTITY_FIELD", "key": "name"},
            {"type": "ENTITY_FIELD", "key": "label"},
        ],
        "latestValues": [
            {"type": "ATTRIBUTE", "key": "active"},
            {"type": "ATTRIBUTE", "key": "lastActivityTime"},
            *[{"type": "TIME_SERIES", "key": k} for k in _TS_KEYS],
        ],
    }
    try:
        res = student._post("/entitiesQuery/find", query)  # noqa: SLF001 - typed client session
    except Exception:
        return out
    items = res.get("data", []) if isinstance(res, dict) else []
    out["device_count"] = (
        res.get("totalElements", len(items)) if isinstance(res, dict) else len(items)
    )
    rows: list[dict[str, Any]] = []
    online = 0
    chart_did = None
    for it in items[:12]:
        latest = it.get("latest", {})
        fields = latest.get("ENTITY_FIELD", {})
        attrs = latest.get("ATTRIBUTE", {})
        tsv = latest.get("TIME_SERIES", {})
        name = (fields.get("name") or {}).get("value", "?")
        active = str((attrs.get("active") or {}).get("value", "")).lower() == "true"
        online += 1 if active else 0
        last_seen = None
        lt = (attrs.get("lastActivityTime") or {}).get("value")
        if lt:
            try:
                last_seen = datetime.fromtimestamp(int(lt) / 1000, UTC).strftime("%Y-%m-%d %H:%M")
            except Exception:  # noqa: S110
                pass
        reading = ", ".join(
            f"{k} {tsv[k]['value']}"
            for k in _TS_KEYS
            if k in tsv and tsv[k].get("value") not in (None, "")
        )
        did = (it.get("entityId") or {}).get("id")
        rows.append(
            {
                "name": name,
                "label": (fields.get("label") or {}).get("value", ""),
                "active": active,
                "last_seen": last_seen,
                "reading": reading[:60],
            }
        )
        if chart_did is None and did and ("temperature" in tsv or "humidity" in tsv):
            chart_did = did
    out["devices"] = rows
    out["online_count"] = online

    # 2) quota (cached 10 min — rarely changes)
    now = _time.time()
    if now - _max_devices_cache["ts"] > 600:
        try:
            from app.routers.devices import _max_devices

            tid = None
            devs = student.list_devices()
            if devs and devs[0].tenant_id:
                tid = devs[0].tenant_id.id
            _max_devices_cache.update(ts=now, value=_max_devices(sysadmin, tid))
        except Exception:  # noqa: S110
            pass
    out["max_devices"] = _max_devices_cache["value"]

    # 3) active alarms
    try:
        data = student._get(  # noqa: SLF001
            "/alarms",
            pageSize=10,
            page=0,
            searchStatus="ACTIVE",
            sortProperty="createdTime",
            sortOrder="DESC",
        )
        alarms = data.get("data", []) if isinstance(data, dict) else []
        out["alarm_count"] = len(alarms)
        out["alarms"] = [
            {
                "type": a.get("type"),
                "severity": a.get("severity", ""),
                "device": a.get("originatorName", ""),
                "time": datetime.fromtimestamp(a.get("createdTime", 0) / 1000, UTC).strftime(
                    "%H:%M"
                ),
            }
            for a in alarms
        ]
    except Exception:  # noqa: S110 - alarms are optional
        pass

    # 4) 24h chart for the primary device (temperature + humidity)
    if chart_did:
        try:
            end = int(_time.time() * 1000)
            # 30-min averages → a smooth, professional 24h line (not raw jitter)
            ts = student._get(  # noqa: SLF001
                f"/plugins/telemetry/DEVICE/{chart_did}/values/timeseries",
                keys="temperature,humidity",
                startTs=end - 24 * 3600 * 1000,
                endTs=end,
                interval=1800000,
                agg="AVG",
                limit=50,
            )
            ts = ts if isinstance(ts, dict) else {}
            series = {}
            for key in ("temperature", "humidity"):
                pts = sorted(ts.get(key, []), key=lambda p: p["ts"])
                series[key] = [
                    {
                        "t": datetime.fromtimestamp(p["ts"] / 1000, UTC).strftime("%H:%M"),
                        "v": float(p["value"]),
                    }
                    for p in pts
                    if p.get("value") is not None
                ]
            if series.get("temperature") or series.get("humidity"):
                out["chart"] = json.dumps(series)
        except Exception:  # noqa: S110 - chart is optional
            pass
    return out


@router.post("/home/provision")
def retry_provision(request: Request, db: Session = Depends(get_db)) -> Any:
    user = load_user(request, db)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    ensure_provisioned(db, user)
    return RedirectResponse("/home", status_code=303)


# --- Explore the lab: every engine that powers CHERT IoT, grouped like the systems poster. ---
# access: open=live student link · admin=SSO/admin UI · lora=via the portal /lora flow ·
#         internal=runs only on the private Docker network (shown for learning) · dev=not in prod.
_SYSTEMS: list[dict[str, Any]] = [
    {
        "group": "Core platform",
        "items": [
            {
                "name": "ThingsBoard CE",
                "ver": "4.3.1.4",
                "lic": "Apache-2.0",
                "access": "open",
                "url": "https://app.{d}",
                "desc": "The IoT core — devices, telemetry, dashboards, "
                "rule chains, alarms. Your own tenant.",
            },
            {
                "name": "Keycloak",
                "ver": "26.7.2",
                "lic": "Apache-2.0",
                "access": "admin",
                "url": "https://auth.{d}",
                "desc": "Identity & single sign-on for every app.",
            },
            {
                "name": "Portal (FastAPI)",
                "ver": "app",
                "lic": "—",
                "access": "open",
                "url": "https://{d}",
                "desc": "This site: devices, flows, lab, alerts, teach.",
            },
            {
                "name": "Docs (MkDocs)",
                "ver": "app",
                "lic": "—",
                "access": "open",
                "url": "https://{d}/docs/",
                "desc": "Getting-started guides (English & Arabic).",
            },
            {
                "name": "Caddy + layer4",
                "ver": "2.11.4",
                "lic": "Apache-2.0",
                "access": "internal",
                "url": "",
                "desc": "Edge reverse proxy: TLS, routing, MQTTS on :8883.",
            },
        ],
    },
    {
        "group": "Observability & monitoring",
        "items": [
            {
                "name": "Prometheus",
                "ver": "3.14.0",
                "lic": "Apache-2.0",
                "access": "internal",
                "url": "",
                "desc": "Collects metrics and evaluates alert rules.",
            },
            {
                "name": "Grafana",
                "ver": "13.1.4",
                "lic": "AGPL-3.0",
                "access": "admin",
                "url": "https://grafana.{d}",
                "desc": "Dashboards over Prometheus. Sign in with "
                "“Sign in with CHERT IoT” (SSO), not a password.",
            },
            {
                "name": "Alertmanager",
                "ver": "0.34.0",
                "lic": "Apache-2.0",
                "access": "internal",
                "url": "",
                "desc": "Routes platform alerts to email.",
            },
            {
                "name": "Uptime Kuma",
                "ver": "1.23.17",
                "lic": "MIT",
                "access": "open",
                "url": "https://status.{d}/status/chert-iot",
                "desc": "Public status & uptime page.",
            },
            {
                "name": "node-exporter",
                "ver": "1.12.1",
                "lic": "Apache-2.0",
                "access": "internal",
                "url": "",
                "desc": "Host CPU/RAM/disk metrics.",
            },
            {
                "name": "cAdvisor",
                "ver": "0.55.1",
                "lic": "Apache-2.0",
                "access": "internal",
                "url": "",
                "desc": "Per-container metrics.",
            },
            {
                "name": "postgres-exporter",
                "ver": "0.20.1",
                "lic": "Apache-2.0",
                "access": "internal",
                "url": "",
                "desc": "Database metrics.",
            },
        ],
    },
    {
        "group": "IoT & LoRaWAN stack",
        "items": [
            {
                "name": "ChirpStack",
                "ver": "4.19.1",
                "lic": "MIT",
                "access": "lora",
                "url": "https://{d}/lora",
                "desc": "LoRaWAN network server. Register at /lora.",
            },
            {
                "name": "ChirpStack Gateway Bridge",
                "ver": "4.1.2",
                "lic": "MIT",
                "access": "internal",
                "url": "",
                "desc": "Gateways send here: {d}:1700/udp (Semtech UDP, EU868).",
            },
            {
                "name": "Eclipse Mosquitto",
                "ver": "2.0.22",
                "lic": "EPL-2.0",
                "access": "internal",
                "url": "",
                "desc": "MQTT broker between ChirpStack and the bridge.",
            },
            {
                "name": "Redis",
                "ver": "7.4.11",
                "lic": "BSD-3",
                "access": "internal",
                "url": "",
                "desc": "ChirpStack device-session & metrics store.",
            },
            {
                "name": "lora-bridge",
                "ver": "app",
                "lic": "—",
                "access": "internal",
                "url": "",
                "desc": "Forwards LoRa uplinks to your ThingsBoard device by DevEUI.",
            },
        ],
    },
    {
        "group": "Student tools — flows & lab",
        "items": [
            {
                "name": "Node-RED",
                "ver": "5.0.6",
                "lic": "Apache-2.0",
                "access": "open",
                "url": "https://{d}/flows",
                "desc": "Your private low-code flow editor.",
            },
            {
                "name": "JupyterHub",
                "ver": "5.5.1",
                "lic": "BSD-3",
                "access": "open",
                "url": "https://lab.{d}",
                "desc": "Your Python notebooks — plot your own telemetry.",
            },
            {
                "name": "docker-socket-proxy",
                "ver": "0.5.0",
                "lic": "GPL-3.0",
                "access": "internal",
                "url": "",
                "desc": "Least-privilege Docker API used to spawn your flows/notebooks.",
            },
        ],
    },
    {
        "group": "Backup & dev",
        "items": [
            {
                "name": "restic",
                "ver": "0.16",
                "lic": "BSD-2",
                "access": "internal",
                "url": "",
                "desc": "Nightly encrypted off-box backups.",
            },
            {
                "name": "Mailpit",
                "ver": "1.31.0",
                "lic": "MIT",
                "access": "dev",
                "url": "",
                "desc": "Local email capture for development only.",
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
    groups = []
    for g in _SYSTEMS:
        items = [
            {
                **it,
                "href": it["url"].format(d=d) if it["url"] else "",
                "hint": it["desc"].format(d=d),
            }
            for it in g["items"]
        ]
        groups.append({"group": g["group"], "items": items})
    total = sum(len(g["items"]) for g in _SYSTEMS)
    return templates.TemplateResponse(
        request, "explore.html", {"user": user, "groups": groups, "total": total}
    )
