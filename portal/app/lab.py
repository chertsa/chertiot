"""JupyterHub notebooks — portal side (M5.3).

The portal is the only launch path: it authorises project membership, then hands off to the hub's
per-project **named server** (server name = the immutable project id). A hand-edited hub URL is
still rejected by the hub's own pre_spawn_hook (it calls /internal/lab-token, 403 for non-members),
so this module is the *friendly* gate and the hub is the *authoritative* one. It also deletes a
project's named servers on project delete, so no orphaned notebook container/volume is left behind.
"""

from __future__ import annotations

import logging
from urllib.parse import quote

import httpx

from app.config import get_settings

log = logging.getLogger(__name__)


def enabled() -> bool:
    return get_settings().lab_enabled


def spawn_url(email: str, project_id: str) -> str:
    """The hub URL that spawns (or reopens) this project's named server for this user."""
    return f"{get_settings().lab_url}/hub/spawn/{quote(email)}/{quote(project_id)}"


def healthy(timeout: float = 3.0) -> bool:
    """Best-effort hub liveness probe against the in-network API (never raises)."""
    s = get_settings()
    try:
        r = httpx.get(f"{s.lab_internal_url.rstrip('/')}/hub/health", timeout=timeout)
        return r.status_code == 200
    except httpx.HTTPError:
        return False


def _api(method: str, path: str, timeout: float = 15.0) -> httpx.Response:
    s = get_settings()
    return httpx.request(
        method,
        f"{s.lab_internal_url.rstrip('/')}/hub/api{path}",
        headers={"Authorization": f"token {s.lab_internal_secret}"},
        timeout=timeout,
    )


def delete_project_notebooks(project_id: str, emails: list[str]) -> None:
    """Stop + delete each member's named server for this project (and its container/volume), so a
    deleted/archived project leaves no orphaned notebook. Best-effort: never blocks a delete."""
    if not get_settings().lab_internal_secret:
        return
    for email in emails:
        try:
            # remove=true stops the server and removes its record; DockerSpawner.remove tears the
            # container down. 404 = never launched → nothing to do.
            r = _api(
                "DELETE",
                f"/users/{quote(email)}/servers/{quote(project_id)}",
            )
            if r.status_code not in (202, 204, 404):
                log.info("hub server delete %s/%s → %s", email, project_id, r.status_code)
        except httpx.HTTPError:
            log.info("hub unreachable deleting notebook for %s/%s", email, project_id)
