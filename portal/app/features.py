"""v2 feature flags.

Each new v2 capability guards on a flag so it can ship dark and be turned on **staging-first**,
with production staying on the frozen v1 until the final cutover. Read server-side via ``flags()``
and in templates via the injected ``features`` mapping (e.g. ``{% if features.monitoring %}``).
Add a flag here as each capability lands; back it with a `Settings` field in `app/config.py`.
"""

from __future__ import annotations

from typing import Any

from fastapi import Request

from app.config import get_settings


def flags() -> dict[str, bool]:
    s = get_settings()
    return {
        "monitoring": s.monitoring_enabled,  # v2 Project Monitoring (Phase 2)
        "telemetry": s.telemetry_enabled,  # v2 Telemetry tab (Phase 3)
    }


def feature_globals(request: Request) -> dict[str, Any]:
    """Jinja context processor: expose `features` to every template."""
    return {"features": flags()}
