from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from prometheus_fastapi_instrumentator import Instrumentator
from starlette.middleware.sessions import SessionMiddleware

from app.auth import configure_oauth
from app.config import get_settings
from app.routers import auth, devices, home, signup

app = FastAPI(title="CHERT IoT portal", docs_url=None, redoc_url=None)
Instrumentator(excluded_handlers=["/healthz", "/metrics"]).instrument(app).expose(app)


@app.on_event("startup")
def _startup() -> None:
    configure_oauth()


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


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "env": get_settings().env}
