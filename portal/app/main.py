from fastapi import FastAPI

from app.config import get_settings

app = FastAPI(title="CHERT IoT portal")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "env": get_settings().env}
