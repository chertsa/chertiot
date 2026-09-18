"""CHERT IoT JupyterHub (M3.2): Keycloak login, capped per-student notebook containers via the
socket proxy, 30-min idle culling. The student's own ThingsBoard JWT is minted by the portal
(internal endpoint, same impersonation mechanism the portal uses everywhere) and injected into
the notebook as TB_JWT — isolation stays ThingsBoard's own (D10)."""

import os

import requests

c = get_config()  # noqa: F821 - provided by JupyterHub

DOMAIN = os.environ["DOMAIN"]
NOTEBOOK_IMAGE = os.environ["LAB_NOTEBOOK_IMAGE"]

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
c.JupyterHub.allow_named_servers = True
c.DockerSpawner.volumes = {"jupyter-{username}-{servername}": "/home/jovyan/work"}
c.JupyterHub.default_url = "/hub/home"
c.JupyterHub.hub_ip = "0.0.0.0"
c.JupyterHub.hub_connect_ip = "jupyterhub"

PORTAL_INTERNAL = os.environ.get("PORTAL_INTERNAL_URL", "http://portal:8000")
LAB_SECRET = os.environ["LAB_INTERNAL_SECRET"]


async def pre_spawn_hook(spawner):
    # The named server is the CHERT project id; mint that project's TB session for the notebook.
    # The portal rejects the spawn (403) unless this user is an active member of that project.
    email = spawner.user.name
    project_id = spawner.name  # named-server name = project id ("" for the default server)
    r = requests.post(
        f"{PORTAL_INTERNAL}/internal/lab-token",
        json={"email": email, "project_id": project_id},
        headers={"X-Lab-Secret": LAB_SECRET},
        timeout=30,
    )
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

# --- idle culling (30 min, like flows)
c.JupyterHub.services = [
    {
        "name": "idle-culler",
        "command": ["python", "-m", "jupyterhub_idle_culler", "--timeout=1800"],
    }
]
c.JupyterHub.load_roles = [
    {
        "name": "idle-culler",
        "scopes": ["list:users", "read:users:activity", "read:servers", "delete:servers"],
        "services": ["idle-culler"],
    }
]
