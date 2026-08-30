from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from app.config import get_settings

app = FastAPI(title="CHERT IoT portal")
Instrumentator(excluded_handlers=["/healthz", "/metrics"]).instrument(app).expose(app)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "env": get_settings().env}
