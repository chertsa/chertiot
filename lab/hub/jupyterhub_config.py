"""CHERT IoT JupyterHub (M3.2): Keycloak login, capped per-student notebook containers via the
socket proxy, 30-min idle culling. The student's own ThingsBoard JWT is minted by the portal
(internal endpoint, same impersonation mechanism the portal uses everywhere) and injected into
the notebook as TB_JWT — isolation stays ThingsBoard's own (D10)."""

import os

import requests

c = get_config()  # noqa: F821 - provided by JupyterHub

DOMAIN = os.environ["DOMAIN"]
NOTEBOOK_IMAGE = os.environ["LAB_NOTEBOOK_IMAGE"]
# Per-user cap on named servers (one per project). Bounds resource use and volume sprawl.
NAMED_SERVER_LIMIT = int(os.environ.get("LAB_NAMED_SERVER_LIMIT", "10"))

# Persist hub state in /data (a mounted volume); the config itself stays in the image at
# /srv/jupyterhub so config changes actually take effect (the volume must NOT mask the config file).
c.JupyterHub.db_url = "sqlite:////data/jupyterhub.sqlite"
c.JupyterHub.cookie_secret_file = "/data/jupyterhub_cookie_secret"

# --- auth: Keycloak (existing realm client `jupyterhub`)
from oauthenticator.generic import GenericOAuthenticator

issuer_pub = os.environ["KC_HOSTNAME"].rstrip("/") + "/realms/" + os.environ["KC_REALM"]
issuer_int = os.environ["KC_INTERNAL_URL"].rstrip("/") + "/realms/" + os.environ["KC_REALM"]
c.JupyterHub.authenticator_class = GenericOAuthenticator
c.GenericOAuthenticator.client_id = "jupyterhub"
c.GenericOAuthenticator.client_secret = os.environ["KC_SECRET_JUPYTERHUB"]
c.GenericOAuthenticator.authorize_url = issuer_pub + "/protocol/openid-connect/auth"
c.GenericOAuthenticator.token_url = issuer_int + "/protocol/openid-connect/token"
c.GenericOAuthenticator.userdata_url = issuer_int + "/protocol/openid-connect/userinfo"
c.GenericOAuthenticator.oauth_callback_url = f"https://lab.{DOMAIN}/hub/oauth_callback"
c.GenericOAuthenticator.username_claim = "email"
c.GenericOAuthenticator.scope = ["openid", "email", "profile"]
c.GenericOAuthenticator.allow_all = True
# Seamless SSO: skip JupyterHub's own "Sign in with OAuth 2.0" page (go straight to Keycloak) and
# auto-approve the internal per-server OAuth so the notebook opens without extra confirm clicks.
c.Authenticator.auto_login = True
c.Spawner.oauth_no_confirm = True

# --- spawner: docker via the least-privilege socket proxy
c.JupyterHub.spawner_class = "dockerspawner.DockerSpawner"
c.DockerSpawner.image = NOTEBOOK_IMAGE
c.DockerSpawner.network_name = os.environ.get("LAB_NETWORK", "chertiot_default")
c.DockerSpawner.remove = True
c.DockerSpawner.prefix = "jupyter"
c.DockerSpawner.mem_limit = "512M"
c.DockerSpawner.cpu_limit = 1.0
c.DockerSpawner.notebook_dir = "/home/jovyan/work"
# One notebook workspace PER PROJECT (M5.3): named servers, volume keyed by user + server (project).
# The server name is always the immutable CHERT project id (see pre_spawn_hook). The storage
# boundary is therefore per (user, project): volume `jupyter-<username>-<project_id>` mounted at the
# notebook's only writable path. A different project (different servername) mounts a different
# volume, and a different user (different username) a different volume again — no shared writable
# path exists across projects or users. The default (unnamed) server is never used: its name is ""
# → the portal membership check below rejects it, so no `jupyter-<username>-` volume is ever created.
c.JupyterHub.allow_named_servers = True
c.JupyterHub.named_server_limit_per_user = NAMED_SERVER_LIMIT
c.DockerSpawner.volumes = {"jupyter-{username}-{servername}": "/home/jovyan/work"}
c.JupyterHub.default_url = "/hub/home"
c.JupyterHub.hub_ip = "0.0.0.0"
c.JupyterHub.hub_connect_ip = "jupyterhub"
# CHERT branding: replace the JupyterHub navbar logo on Hub pages (shipped in the image).
c.JupyterHub.logo_file = "/srv/jupyterhub/chert-logo.png"

PORTAL_INTERNAL = os.environ.get("PORTAL_INTERNAL_URL", "http://portal:8000")
LAB_SECRET = os.environ["LAB_INTERNAL_SECRET"]


async def pre_spawn_hook(spawner):
    # The named server IS the CHERT project id; mint that project's TB session for the notebook.
    # This hook is the authoritative membership gate for EVERY spawn — including one triggered by a
    # hand-edited /hub/spawn/<email>/<project_id> URL — because the portal returns 403 unless this
    # authenticated user is an active member of exactly that project. A missing/empty server name
    # (the default server) has no project and is rejected the same way. A denied spawn raises a clean
    # 403 instead of a 500, and no notebook container/volume is created.
    from tornado import web  # local import: tornado is provided by the hub runtime

    email = spawner.user.name
    project_id = spawner.name  # named-server name = project id ("" for the default server)
    if not project_id:
        raise web.HTTPError(403, "Notebooks are opened per project from the CHERT IoT portal.")
    try:
        r = requests.post(
            f"{PORTAL_INTERNAL}/internal/lab-token",
            json={"email": email, "project_id": project_id},
            headers={"X-Lab-Secret": LAB_SECRET},
            timeout=30,
        )
    except requests.RequestException as e:
        raise web.HTTPError(503, "The CHERT IoT portal is unavailable; try again shortly.") from e
    if r.status_code == 403:
        raise web.HTTPError(403, "You are not a member of this project.")
    if r.status_code == 404:
        raise web.HTTPError(403, "Unknown account for this project.")
    r.raise_for_status()
    body = r.json()
    spawner.environment.update(
        {
            "TB_JWT": body["token"],
            "TB_URL": os.environ.get("TB_INTERNAL_URL", "http://tb:8080"),
            "TB_PUBLIC_URL": f"https://app.{DOMAIN}",
            "CHERT_PROJECT": project_id,
        }
    )


c.Spawner.pre_spawn_hook = pre_spawn_hook

# --- services: idle culling (30 min) + a least-privilege token for the portal so it can delete a
# project's named server when the project is archived/deleted (see portal app/lab.py).
c.JupyterHub.services = [
    {
        "name": "idle-culler",
        "command": ["python", "-m", "jupyterhub_idle_culler", "--timeout=1800"],
    },
    {"name": "portal", "api_token": LAB_SECRET},
]
c.JupyterHub.load_roles = [
    {
        "name": "idle-culler",
        "scopes": ["list:users", "read:users:activity", "read:servers", "delete:servers"],
        "services": ["idle-culler"],
    },
    {
        # The portal may stop/delete named servers (project delete) and read server state, nothing
        # more — it never gains notebook access or user administration.
        "name": "portal-servers",
        "scopes": ["admin:servers", "read:users:name", "list:users"],
        "services": ["portal"],
    },
]
