import logging
from pathlib import Path

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from prometheus_fastapi_instrumentator import Instrumentator
from starlette.middleware.sessions import SessionMiddleware

from app.auth import configure_oauth
from app.config import get_settings
from app.i18n import translator
from app.keycloak_admin import KeycloakError
from app.routers import alerts, auth, devices, home, instructor, internal, signup
from app.routers import flows as flows_router
from app.tb_client import TbError
from app.templating import templates

log = logging.getLogger(__name__)

app = FastAPI(title="CHERT IoT portal", docs_url=None, redoc_url=None)
Instrumentator(excluded_handlers=["/healthz", "/metrics"]).instrument(app).expose(app)


@app.on_event("startup")
def _startup() -> None:
    configure_oauth()
    _start_flows_culler()


def _start_flows_culler() -> None:
    """Every 5 minutes, stop Node-RED instances idle > 30 min (M3.1 capacity control)."""
    import threading

    from app import flows as flows_mod
    from app.db import session_factory

    if not flows_mod.enabled():
        return

    def loop() -> None:
        import time

        while True:
            time.sleep(300)
            try:
                flows_mod.cull_idle(session_factory())
            except Exception:  # noqa: BLE001 — the culler must never die
                log.exception("flows culler iteration failed")

    threading.Thread(target=loop, daemon=True, name="flows-culler").start()


app.add_middleware(
    SessionMiddleware,
    secret_key=get_settings().portal_secret_key,
    session_cookie="chertiot_session",
    https_only=get_settings().env != "dev",
    same_site="lax",
    max_age=8 * 3600,
)
app.mount(
    "/static", StaticFiles(directory=str(Path(__file__).resolve().parent / "static")), name="static"
)
app.include_router(home.router)
app.include_router(signup.router)
app.include_router(auth.router)
app.include_router(devices.router)
app.include_router(flows_router.router)
app.include_router(internal.router)
app.include_router(instructor.router)
app.include_router(alerts.router)


@app.exception_handler(httpx.TransportError)
@app.exception_handler(KeycloakError)
@app.exception_handler(TbError)
async def upstream_unavailable(request: Request, exc: Exception) -> Response:
    """Keycloak/ThingsBoard slow or down: say so plainly (D-voice: no vague 'oops'), never a 500."""
    log.warning("upstream failure on %s %s: %r", request.method, request.url.path, exc)
    _ = translator(request)
    ctx = {
        "title": _("The lab is busy right now"),
        "message": _(
            "A backend service did not answer in time. "
            "Nothing was lost — wait a minute and try again."
        ),
    }
    return templates.TemplateResponse(request, "error.html", ctx, status_code=503)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "env": get_settings().env}
