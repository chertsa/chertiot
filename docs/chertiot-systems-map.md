# CHERT IoT — Systems → Components & URLs Map

Maps every open-source system in [`opensource-systems-inventory.md`](opensource-systems-inventory.md)
to its **container/service**, **internal endpoint**, **public URL**, exposure, and the
**student-facing entry point** on chertiot.com. Companion to `architecture.md` and
`chertiot_journies_and_services.md`.

**Domains:** production `chertiot.com` · staging `stage.chertiot.com` (same layout, `stage.` prefix).
All public traffic enters through **Caddy** (TLS + routing); internal endpoints are reachable only
on the Docker network.

---

## 1. Master map

| System | Version | Container / service | Profile | Internal endpoint | Public URL | Exposure | Where a user meets it |
|---|---|---|---|---|---|---|---|
| **ThingsBoard CE** | 4.3.1.4 | `tb` | core | `tb:8080` (REST/UI), `tb:1883` (MQTT) | `https://app.chertiot.com` · MQTTS `chertiot.com:8883` | Public | "Open my dashboard", devices, alarms; devices publish to `:8883` |
| **Keycloak** | 26.7.2 | `keycloak` | core | `keycloak:8080` | `https://auth.chertiot.com` | Public | "Sign in with CHERT IoT"; `/admin/` for operators |
| **Portal (FastAPI)** | app | `portal` | core | `portal:8000` | `https://chertiot.com` | Public | The website itself (see §3 for paths) |
| **Docs (mkdocs→nginx)** | app | `docs` | core | `docs:80` | `https://chertiot.com/docs/` | Public (via portal host) | Getting-started & guides (EN/AR) |
| **Caddy + layer4** | 2.11.4 | `caddy` | core | `:80` `:443` `:443/udp` `:8883` | *is the edge* for all hosts | Public | TLS padlock; MQTTS broker on `:8883` |
| **PostgreSQL** | 16.15 | `postgres` | core, lora | `postgres:5432` (DBs: thingsboard, keycloak, portal, chirpstack) | — | Internal only | (invisible) |
| **Prometheus** | v3.14.0 | `prometheus` | core | `prometheus:9090` | — | Internal only | Feeds Grafana/alerts |
| **Alertmanager** | v0.34.0 | `alertmanager` | core | `alertmanager:9093` | — | Internal only | Sends alert emails (SMTP2GO) |
| **Grafana** | 13.1.4 | `grafana` | core | `grafana:3000` | `https://grafana.chertiot.com` | Public (admin-only) | Operator dashboards |
| **Uptime Kuma** | 1.23.17 | `uptime-kuma` | core | `uptime-kuma:3001` | `https://status.chertiot.com` (page: `/status/chert-iot`) | Public | Public status page |
| **node-exporter** | v1.12.1 | `node-exporter` | core | `node-exporter:9100` | — | Internal only | Host metrics → Prometheus |
| **cAdvisor** | v0.55.1 | `cadvisor` | core | `cadvisor:8080` | — | Internal only | Container metrics → Prometheus |
| **postgres-exporter** | v0.20.1 | `postgres-exporter` | core | `postgres-exporter:9187` | — | Internal only | DB metrics → Prometheus |
| **Node-RED** | 5.0.6 | `nodered-<userId>` (spawned per student) | flows | `nodered-<userId>:1880` | `https://flows.chertiot.com/u/<userId>/` | Public (owner-only via `forward_auth`) | `/flows` → "CHERT Node" editor |
| **docker-socket-proxy** | v0.5.0 | `socket-proxy` | flows, lab | `socket-proxy:2375` (containers/images/volumes/networks only) | — | Internal only | Lets the portal spawn Node-RED / notebooks |
| **JupyterHub** | 5.5.1 | `jupyterhub` (+ per-user notebook containers) | lab | `jupyterhub:8000` | `https://lab.chertiot.com` | Public (OIDC) | Python notebooks |
| **ChirpStack** | 4.19.1 | `chirpstack` | lora | `chirpstack:8080` (gRPC API) | — (UI internal; students use portal `/lora`) | Internal only | Behind `/lora` registration |
| **ChirpStack Gateway Bridge** | 4.1.2 | `chirpstack-gateway-bridge` | lora | `:1700/udp` (Semtech UDP) | `chertiot.com:1700/udp` (EU868) | Public (UDP, for gateways) | Point your LoRa gateway here |
| **Eclipse Mosquitto** | 2.0.22 | `mosquitto` | lora | `mosquitto:1883` | — | Internal only | ChirpStack ↔ bridge ↔ lora-bridge |
| **Redis** | 7.4.11 | `redis` | lora | `redis:6379` | — | Internal only | ChirpStack session/metrics store |
| **lora-bridge** (custom) | app | `lora-bridge` | lora | (MQTT consumer, no port) | — | Internal only | Forwards LoRa uplinks → your TB device |
| **restic** | 0.16 | ops script (`deploy/scripts/backup.sh`) | — (cron) | — → SFTP on the other droplet | — | Off-box | (invisible) nightly backups |
| **Mailpit** | v1.31.0 | `mailpit` (dev only) | dev override | `127.0.0.1:18025` | — | Local dev only | Not in production |

`<userId>` = the student's portal user id; `flows.` routes each `/u/<id>/` only to that student's
container after Caddy `forward_auth` → portal `/flows/auth`.

---

## 2. Public URL map (what the edge exposes)

| URL / port | Caddy routes to | Purpose |
|---|---|---|
| `https://chertiot.com` | `portal:8000` | The portal (signup, devices, flows, lora, alerts, teach) |
| `https://chertiot.com/docs/` | `docs:80` | Documentation (EN + `/docs/ar/`) |
| `https://app.chertiot.com` | `tb:8080` | ThingsBoard UI + REST + HTTP telemetry |
| `https://auth.chertiot.com` | `keycloak:8080` | Login pages, OIDC endpoints, admin console |
| `https://lab.chertiot.com` | `jupyterhub:8000` | JupyterHub notebooks |
| `https://flows.chertiot.com/u/<id>/` | `nodered-<id>:1880` | Per-student Node-RED (owner-only) |
| `https://grafana.chertiot.com` | `grafana:3000` | Admin metrics dashboards |
| `https://status.chertiot.com` | `uptime-kuma:3001` | Public status page |
| `https://lora.chertiot.com` | *302 redirect* | → `chertiot.com/lora` (ChirpStack UI stays internal) |
| `chertiot.com:8883` (TLS) | `tb:1883` | **Device MQTTS** — token auth, TLS terminates at Caddy |
| `chertiot.com:1700/udp` | `chirpstack-gateway-bridge` | **LoRaWAN gateway** uplinks (EU868) |

---

## 3. Portal path map (systems reached through `chertiot.com/...`)

| Path | Backed by | What it does |
|---|---|---|
| `/signup`, `/login`, `/auth/callback` | Portal + Keycloak | Register / OIDC sign-in |
| `/home` | Portal + ThingsBoard | Landing; "Open my dashboard" (SSO into TB) |
| `/devices`, `/devices/<id>` | Portal + ThingsBoard | Device list, tokens, firmware snippets |
| `/dashboard/reset` | Portal + ThingsBoard | Re-import starter dashboard |
| `/flows`, `/flows/start`, `/flows/stop`, `/flows/auth` | Portal + Node-RED + socket-proxy | Spawn/gate the Node-RED editor |
| `/lora` | Portal + ChirpStack (gRPC) | Register LoRa device, get OTAA keys |
| `/alerts` | Portal + ThingsBoard | Threshold alerts (rule chains) + CSV/JSON export |
| `/teach`, `/join` | Portal + Keycloak + ThingsBoard | Instructor console; join a class by code |
| `/docs/`, `/docs/ar/` | Docs (mkdocs) | Student documentation |
| `/internal/lab-token` | Portal (in-network) | Hands JupyterHub the student's TB JWT |

---

## 4. Exposure summary

- **Public, student-facing:** portal (`chertiot.com`), ThingsBoard (`app.`), Keycloak (`auth.`),
  JupyterHub (`lab.`), Node-RED (`flows.`, owner-gated), docs (`/docs/`), status (`status.`),
  MQTTS `:8883`, LoRa gateway UDP `:1700`.
- **Public, admin-only:** Grafana (`grafana.`), Keycloak admin (`auth.../admin`).
- **Internal only (never exposed):** PostgreSQL, Prometheus, Alertmanager, all exporters,
  docker-socket-proxy, Mosquitto, Redis, ChirpStack API/UI, lora-bridge.
- **Off-box / non-service:** restic backups (cron → SFTP), Mailpit (dev only).

---

## 5. Identity relationships (who trusts whom)

- **Keycloak** is the identity provider. **Portal**, **ThingsBoard**, **JupyterHub** and **Grafana**
  are all OIDC/OAuth2 clients of the `chertiot` realm → one login everywhere.
- **Portal → ThingsBoard**: REST only (`tb_client.py`), always as the student (impersonation).
- **Portal → ChirpStack**: gRPC (`chirpstack-api`).
- **Portal → Node-RED / notebooks**: via `docker-socket-proxy` (least-privilege Docker API).
- **Devices → ThingsBoard**: MQTTS `:8883` (token = MQTT username).
- **LoRa gateway → ChirpStack**: UDP `:1700` → gateway-bridge → Mosquitto → ChirpStack → `lora-bridge` → the student's TB device.
