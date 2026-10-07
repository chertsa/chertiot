# CHERT Metro Map — ChertIoT (T)

**System code:** T · **Repository:** chertiot · **Generated:** 2026-09-26
**Method:** read from code, `docker-compose.yml`, `.env.example`, `CLAUDE.md`, `PLAN.md`, `portal/app/**`, deploy files. No code changed. No secrets copied.

---

## 1. Subject: what is this system?

**1.1 Name, code, website.** ChertIoT, code **T**, at `chertiot.com` (staging `stage.chertiot.com`; sub-domains `app.` ThingsBoard, `auth.` Keycloak, `lab.` JupyterHub, `flows.` Node-RED, `grafana.`, `status.`). **(confirmed** — `PLAN.md` routing line, `deploy/caddy`, `.env.example` domains.**)**

**1.2 One sentence.** A self-hosted, multi-tenant Internet-of-Things teaching platform where each learner or team gets their own isolated IoT workspace to connect devices, see live sensor data on dashboards, set alerts, wire no-code automations, analyse data in notebooks, and register LoRaWAN devices. **(confirmed** — portal templates + project tabs.**)**

**1.3 Problem it solves.** Standing up a real IoT stack (device management, telemetry storage, dashboards, rules, automation, LoRaWAN) is hard and expensive; ChertIoT gives each student/team a ready, isolated environment out of the box so they can learn and build without operating servers. **(assumed** — inferred from the teaching-lab design and per-project isolation.**)**

**1.4 Who uses it.** Education/training context. People: **students** (default), **instructors** (cohort roster + class codes), **admins** (platform). Inside a project: **owner** and **members**. **(confirmed** — `portal/app/permissions.py`, `routers/instructor.py`, `models.py` `ClassCode`.**)**

**1.5 Delivery.** **Chert-run private platform**, not installed on the customer's own box: two DigitalOcean droplets (`main`/`stage`), one Docker Compose stack per environment, public web sign-up with SSO. **(confirmed** — `deploy/scripts/deploy.sh`, `docker-compose.yml`, `CLAUDE.md`.**)**

**1.6 Status.** **In development (build phase)** on both `main` and `stage`; the v2 unified platform is feature-complete and green on staging (branch `release/chertiot-v2-unified`), no production cutover yet. **(confirmed** — session state; owner statement "build phase on both main and stage".**)**

---

## 2. Engines inside the system

| # | Engine | Type | Based on (upstream + version) | Licence | Role in the system | How much Chert changed it | Where in the repo |
|---|---|---|---|---|---|---|---|
| 1 | **Portal** | in-house | FastAPI (Python 3.12) | proprietary | Orchestration & product layer; the only user-facing app; brokers every other engine | core code (written by Chert) | `portal/` |
| 2 | **ThingsBoard** (chertiot-tb) | open-source, rebranded | ThingsBoard CE 4.3.1.4 | Apache-2.0 | IoT core: devices, telemetry, dashboards, alarms, tenants | branding + palette + Arabic (ar_AR) locale patches; config | `thingsboard-brand/`, image `ghcr.io/chertsa/chertiot-tb` |
| 3 | **Keycloak** | open-source, rebranded | Keycloak 26.7.2 | Apache-2.0 | Identity, SSO, sign-up, realm roles | CHERT login theme (EN/AR LTR) + realm/client config | `keycloak/theme/chertiot/`, `portal/scripts/setup_keycloak.py` |
| 4 | **Node-RED** (chertiot-nodered) | open-source, rebranded | Node-RED 5.0.6 | Apache-2.0 | Per-project no-code flow automation | Arabic ar-AR default (LTR) build + portal spawner | `nodered-brand/`, `portal/app/flows.py` |
| 5 | **JupyterHub + JupyterLab** (chertIoTlab) | open-source, rebranded | jupyterhub 5.5.1 / notebook 7.6.2 | BSD-3 | Per-project Python notebooks (named servers) | logo/title/label rebrand, config, per-project spawn hook | `lab/hub/`, `lab/notebook/` |
| 6 | **Grafana** (chertiot-grafana) | open-source, rebranded | Grafana 13.1.4 | AGPL-3.0 | Platform infrastructure dashboards (staff-only) | ar-SA locale build + OAuth/role gating | `grafana-brand/`, image `ghcr.io/chertsa/chertiot-grafana` |
| 7 | **ChirpStack** (+ gateway-bridge) | open-source | ChirpStack 4.19.1 / gw-bridge 4.1.2 | MIT | LoRaWAN network server + gateway bridge | configuration only | `deploy/chirpstack/`, `docker-compose.yml` (lora profile) |
| 8 | **Prometheus stack** | open-source | Prometheus v3.14.0, Alertmanager v0.34.0, node-exporter v1.12.1, cAdvisor v0.55.1, postgres-exporter v0.20.1 | Apache-2.0 | Metrics collection, alerting, host/container/db metrics | configuration only | `deploy/prometheus/`, `docker-compose.yml` |
| 9 | **Uptime Kuma** | open-source | Uptime Kuma 1.23.17 | MIT | Public up/down status page | configuration via `setup_status_page` | `portal/scripts/setup_status_page.py` |
| 10 | **Caddy** (chertiot-caddy) | open-source, rebranded | Caddy 2.11.4 + `caddy-l4` + replace-response (xcaddy) | Apache-2.0 | Reverse proxy, TLS, layer-4 MQTTS, `forward_auth` gate | custom xcaddy build + Caddyfile | `deploy/caddy/` |
| 11 | **PostgreSQL** | open-source | PostgreSQL 16.15 | PostgreSQL licence | Shared relational store (DBs: thingsboard, keycloak, portal, chirpstack) | configuration only | `docker-compose.yml`, `deploy/` init |
| 12 | **Eclipse Mosquitto** | open-source | Mosquitto 2.0.22 | EPL/EDL | MQTT broker on the LoRa→TB bridge path | configuration only | `docker-compose.yml`, `deploy/` |
| 13 | **Redis** | open-source | Redis 7.4.11 | RSAL/SSPL | Cache / ChirpStack backing store | configuration only | `docker-compose.yml` (lora profile) |
| 14 | **Docs site** | open-source, content in-house | MkDocs Material 9.7.7 (nginx serve) | MIT | Student/teacher documentation | Chert content + i18n | `docs-site/`, `docs/` |

All rows **(confirmed** — `docker-compose.yml`, `.env.example`, brand dirs, and the standalone-registry work this session.**)**

**2.1 Core vs support.** **Portal** (in-house) is the orchestration core and **ThingsBoard** is the IoT data/transaction core; **Keycloak** is the identity core. Supporting engines: Node-RED, JupyterHub, Grafana, ChirpStack+Mosquitto, Prometheus stack, Uptime Kuma, Caddy, PostgreSQL, Redis, Docs. **(confirmed.)**

**2.2 What rebranding changed.** Names/logos/colours to CHERT identity; **Arabic added as translation-only, LTR (no RTL)** across TB (ar_AR), Node-RED (ar-AR), Grafana (ar-SA), Keycloak login (EN/AR) and JupyterLab (chertIoTlab labels); warm-ivory/orange palette; local self-hosted fonts/assets; JupyterLab fully re-labelled "chertIoTlab" incl. logo, tab title and Help links. **(confirmed** — `thingsboard-brand/`, `nodered-brand/`, `grafana-brand/`, `keycloak/theme/`, `lab/notebook/branding/`.**)**

**2.3 Standalone vs coupled.** Could run alone: PostgreSQL, Redis, Mosquitto, Prometheus/exporters, Uptime Kuma, Docs. Only meaningful **together**: Portal (drives everything), ThingsBoard (fed & brokered by Portal), Keycloak (SSO for Portal/TB/Grafana/JupyterHub), Node-RED & JupyterHub (spawned per-project by Portal), Grafana (OAuth via Keycloak, data from Prometheus), ChirpStack (needs Mosquitto + lora-bridge + TB). **(confirmed.)**

---

## 3. Functions inside each engine

### Engine: Portal (in-house)

| # | Function | What it does | Who uses it | Status | Where in the repo |
|---|---|---|---|---|---|
| 1 | Sign up | Create Keycloak user (unverified), send verify mail | prospective users | live | `routers/signup.py` |
| 2 | Sign in / SSO / language switch | Keycloak OAuth login; EN/AR toggle | all users | live | `routers/auth.py`, `/lang/{code}` |
| 3 | Projects portfolio (Home) | List owned/shared projects, summary, create | all users | live | `routers/home.py`, `home.html` |
| 4 | Create project & provision | New project = new TB tenant + starter dashboard (idempotent) | owner | live | `routers/projects.py`, `project.py` |
| 5 | Project Overview | KPIs, device roster, active alarms, capability cards | members | live | `projects.py`, `project.html`, `/panel` |
| 6 | Devices | Add/rename/delete device, token/rotate, firmware snippets | members | live | `routers/devices.py` |
| 7 | Telemetry | Per-device latest values, trends, activity | members | live | `routers/*`, `telemetry.html` |
| 8 | Monitoring (portal-native) | Devices/alarms/history over TB, no per-project Grafana | members | live | `routers/monitoring.py` |
| 9 | Alerts | Threshold rules → TB alarms; ack (owner-only for CRITICAL) | members/owner | live | `routers/alerts.py`, `models.AlertRule` |
| 10 | Flows | Start/stop/open per-user Node-RED editor | members | live | `routers/flows.py`, `app/flows.py` |
| 11 | Notebooks | Launch per-project JupyterLab named server | members | live | `routers/projects.py`, `app/lab.py` |
| 12 | Reports | Print-friendly lifecycle report (KPIs, chart, alarms) | members | live | `routers/projects.py`, `project_report.html` |
| 13 | LoRaWAN | Register LoRa device (DevEUI/AppKey), gateway steps | members | live | `routers/lora.py`, `models.LoraDevice` |
| 14 | Open ThingsBoard console | SSO hand-off to per-project TB tenant | members | live | `/projects/{id}/thingsboard` |
| 15 | Members & Settings | Members, join-requests, invitations, dashboard reset, danger zone | members/owner | live | `projects.py`, `project_settings.html` |
| 16 | Instructor console | Class codes + read-only cohort roster | instructor/admin | live | `routers/instructor.py`, `models.ClassCode` |
| 17 | Platform Grafana launch | Staff-only redirect to Grafana | instructor/admin | live | `/grafana`, `home.py` |
| 18 | Internal lab-token | Mints a member's project-tenant TB JWT for JupyterHub | JupyterHub (service) | live | `routers/internal.py` |
| 19 | Flows forward-auth | Caddy `forward_auth` gate for `/flows` ownership | Caddy (service) | live | `/flows/auth` |
| 20 | Explore the stack / Docs / Status | Learn cards + docs + public status | all users | live | `/explore`, docs-site, Uptime Kuma |

### Engine: ThingsBoard

| # | Function | What it does | Who uses it | Status | Where in the repo |
|---|---|---|---|---|---|
| 1 | Tenant (= Project) | Each project is a TB Tenant; members are Tenant-Admins | Portal (brokered) | live | `app/tb_client.py`, `app/project.py` |
| 2 | Device management | Register devices, credentials/tokens | members via Portal | live | `tb_client.py` |
| 3 | Telemetry ingest & store | Receive/store timeseries (MQTT/HTTP) | devices | live | TB rule engine, `templates-tb/` |
| 4 | Dashboards | Starter dashboard per tenant; TB console | members | live | `app/home.py` `/dashboard/open` |
| 5 | Alarms | Raise/clear/ack alarms from rules | members | live | `app/dashboard.py`, `alerts.py` |
| 6 | Rule engine | Save-Timeseries + alarm rule chains | platform | live | `templates-tb/`, `provisioning.py` |

### Engine: Keycloak

| # | Function | What it does | Who uses it | Status | Where in the repo |
|---|---|---|---|---|---|
| 1 | User registry & verify-email | Holds users; email verification | all | live | `setup_keycloak.py`, `keycloak_admin.py` |
| 2 | SSO / OAuth2 | Login for Portal, TB, Grafana, JupyterHub | all | live | `setup_tb_oauth2.py`, realm clients |
| 3 | Realm roles | `platform-admin` / `platform-instructor` claims for Grafana gating | staff | live | `scripts/kc_roles.py`, `grant_role.py` |
| 4 | Branded login (EN/AR LTR) | CHERT login theme | all | live | `keycloak/theme/chertiot/login/` |

### Engine: Node-RED

| # | Function | What it does | Who uses it | Status | Where in the repo |
|---|---|---|---|---|---|
| 1 | Per-user flow editor | Isolated Node-RED instance (0.5 CPU/256 MB) | members | live | `app/flows.py`, `nodered-brand/` |
| 2 | TB pre-injected connection | ThingsBoard creds injected into flows | members | live | `app/flows.py` (settings.js) |
| 3 | Arabic (ar-AR, LTR) UI | Default Arabic editor, LTR-only | members | live | `nodered-brand/` |

### Engine: JupyterHub + JupyterLab (chertIoTlab)

| # | Function | What it does | Who uses it | Status | Where in the repo |
|---|---|---|---|---|---|
| 1 | Per-project named server | Notebook server keyed by project UUID | members | live | `lab/hub/jupyterhub_config.py` |
| 2 | Project-scoped TB token | `pre_spawn_hook` → Portal `/internal/lab-token` | members | live | `lab/hub/`, `routers/internal.py` |
| 3 | Analysis notebooks | pandas/matplotlib starter notebooks | members | live | `lab/notebook/notebooks/` |
| 4 | chertIoTlab branding | CHERT logo/title/labels, no "Jupyter" text | members | live | `lab/notebook/branding/` |

### Engine: Grafana

| # | Function | What it does | Who uses it | Status | Where in the repo |
|---|---|---|---|---|---|
| 1 | Platform infra dashboards | Prometheus-backed dashboards | instructor/admin | live | `grafana-brand/`, `deploy/` |
| 2 | OAuth role gating | Keycloak realm-role → Admin/Viewer, strict deny | staff | live | `scripts/reconcile_grafana.py` |

### Engine: ChirpStack (+ gateway-bridge)

| # | Function | What it does | Who uses it | Status | Where in the repo |
|---|---|---|---|---|---|
| 1 | LoRaWAN network server | Manage LoRa devices/gateways, decode uplinks | members via Portal | live | `deploy/chirpstack/`, `routers/lora.py` |
| 2 | Gateway bridge (Semtech UDP :1700) | Accept packets from real gateways | LoRa gateways | live | `docker-compose.yml` (lora) |

### Engine: Prometheus stack

| # | Function | What it does | Who uses it | Status | Where in the repo |
|---|---|---|---|---|---|
| 1 | Metrics scrape | Host/container/db/app metrics | platform | live | `deploy/prometheus/` |
| 2 | Alerting | Disk/RAM/cert/backup/service-down → email | platform ops | live | Alertmanager config |

### Engine: Uptime Kuma

| # | Function | What it does | Who uses it | Status | Where in the repo |
|---|---|---|---|---|---|
| 1 | Public status page | Up/down of public services | anyone | live | `scripts/setup_status_page.py` |

### Engine: Caddy

| # | Function | What it does | Who uses it | Status | Where in the repo |
|---|---|---|---|---|---|
| 1 | TLS + reverse proxy + host routing | Route each sub-domain to its engine | all | live | `deploy/caddy/Caddyfile*` |
| 2 | Layer-4 MQTTS (:8883) | Secure device MQTT | devices | live | `deploy/caddy/` (caddy-l4) |
| 3 | forward_auth gate | Delegate `/flows` auth to Portal | Node-RED path | live | `Caddyfile`, `/flows/auth` |

(PostgreSQL, Redis, Mosquitto, Docs provide infrastructure functions — storage, cache, MQTT transport, documentation — used by the engines above.) **All section-3 rows (confirmed.)**

---

## 4. In-house modules

| # | Module | Added to which engine | What it adds/changes | Functions it supports (§3) | Where in the repo |
|---|---|---|---|---|---|
| 1 | Portal app | (is its own engine) | Whole product/orchestration layer | Portal 1–20 | `portal/app/` |
| 2 | `tb_client.py` / `provisioning.py` | ThingsBoard | REST broker, idempotent tenant/device/dashboard provisioning, sysadmin impersonation | TB 1–6, Portal 4–14 | `portal/app/` |
| 3 | `permissions.py` | Portal | Central capability matrix (platform + project roles) | all gated functions | `portal/app/permissions.py` |
| 4 | CSRF middleware + `csrf.py` | Portal | Exact-origin CSRF on cookie mutations | all POST functions | `portal/app/main.py`, `csrf.py` |
| 5 | `flows.py` (spawner) | Node-RED | Per-user container spawn via docker-socket-proxy | Node-RED 1–3, Portal 10 | `portal/app/flows.py` |
| 6 | `lab.py` + hub config | JupyterHub | Per-project named-server launch + token | JupyterHub 1–4, Portal 11 | `portal/app/lab.py`, `lab/hub/` |
| 7 | **lora-bridge** | ChirpStack↔ThingsBoard | Forwards ChirpStack uplinks to each project's TB device | ChirpStack 1, TB 3 | `portal/scripts/lora_bridge.py` |
| 8 | `setup_keycloak.py` / `setup_tb_oauth2.py` | Keycloak / TB | Realm, clients, TB OAuth2 bootstrap | Keycloak 1–4 | `portal/scripts/` |
| 9 | `reconcile_grafana.py` / `kc_roles.py` / `grant_role.py` | Grafana / Keycloak | Staff role sync + Grafana gating reconcile | Grafana 2, Keycloak 3 | `portal/scripts/` |
| 10 | `setup_status_page.py` | Uptime Kuma | Creates monitors + published page | Uptime Kuma 1 | `portal/scripts/` |
| 11 | Brand patch sets | TB / Node-RED / Grafana | CHERT identity + Arabic (LTR) | rebranding (§2.2) | `thingsboard-brand/`, `nodered-brand/`, `grafana-brand/` |
| 12 | Firmware examples | Devices | Starter firmware (ESP32/RPi/HTTP/MQTT) | Portal 6 (snippets) | `firmware-examples/` |
| 13 | Image mirror + standalone repoint | CI / all engines | Mirror all images to `ghcr.io/chertsa`; ghcr-only compose/Dockerfiles | build/deploy | `.github/workflows/mirror.yml`, `docker-compose.yml` |

**All (confirmed.)**

---

## 5. Roles

**5.1 User roles.**

| # | Role | What this person does | Functions they use |
|---|---|---|---|
| 1 | Student (platform default) | Owns/joins projects; builds IoT workspaces | Portal 1–15 within their projects |
| 2 | Instructor | Sees cohort roster (read-only), issues class codes; staff Grafana | Portal 16–17, plus student functions |
| 3 | Admin | Platform administration; staff Grafana | Portal 16–17, all staff functions |
| 4 | Project Owner | Full control of one project incl. destructive actions | all project functions incl. owner-only |
| 5 | Project Member (active) | Uses a project they were added to | project functions except owner-only |
| 6 | Project Member (disabled) | Access revoked at the portal gate | none (blocked) |

**(confirmed** — `permissions.py`, `models.ProjectMember`, `routers/instructor.py`.**)**

**5.2 Engine roles (one line each).**
- **Portal** — the product brain: authentication broker, per-project provisioner, and the only human-facing UI; every other engine is reached through it.
- **ThingsBoard** — the IoT transaction/telemetry core; one Tenant per project holds that project's devices, data, dashboards and alarms.
- **Keycloak** — the single identity provider; issues SSO logins and the staff realm-roles that gate Grafana.
- **Node-RED** — per-project no-code automation, spawned and auth-gated by Portal.
- **JupyterHub/JupyterLab** — per-project Python analysis, launched with a project-scoped ThingsBoard token.
- **Grafana** — staff-only platform-infrastructure dashboards over Prometheus (not per-project data).
- **ChirpStack (+Mosquitto+lora-bridge)** — LoRaWAN ingestion path that lands uplinks into each project's ThingsBoard.
- **Prometheus stack** — collects host/container/db/app metrics and fires ops alerts.
- **Uptime Kuma** — public service-status page.
- **Caddy** — front door: TLS, routing, MQTTS, and the `forward_auth` gate.
- **PostgreSQL / Redis / Mosquitto** — shared storage, cache, and MQTT transport.

**(confirmed.)**

---

## 6. Processes (routes)

| # | Process | Steps (function → function) | Engines | Other Chert systems | Status |
|---|---|---|---|---|---|
| 1 | Sign up → working project | Sign up → verify email → SSO login → create project → provision TB tenant + starter dashboard | Portal, Keycloak, ThingsBoard, Postgres | — | live |
| 2 | Onboard device → live data | Add device → get token + firmware snippet → device connects (MQTTS :8883) → telemetry stored → Overview/Telemetry/Dashboard | Portal, ThingsBoard, Caddy, Mosquitto | — | live |
| 3 | Threshold alerting | Create alert rule → push to TB rule chain → alarm raised → ack (CRITICAL owner-only) | Portal, ThingsBoard | — | live |
| 4 | No-code automation | Start Node-RED → editor opens (forward_auth) → wire flows with pre-injected TB creds → deploy | Portal, Node-RED, Caddy | — | live |
| 5 | Notebook analysis | Open Notebooks → JupyterHub spawns named server → project TB token minted → analyse in JupyterLab | Portal, JupyterHub, ThingsBoard | — | live |
| 6 | LoRaWAN onboarding | Register LoRa device (DevEUI/AppKey) → point gateway at :1700 → uplink → lora-bridge → TB device | Portal, ChirpStack, Mosquitto, lora-bridge, ThingsBoard | — | live |
| 7 | Monitoring | Open Monitoring → portal reads TB devices/alarms/history (no per-project Grafana) | Portal, ThingsBoard | — | live |
| 8 | Reporting | Open Reports → lifecycle KPIs + 24h chart + alarm history → print | Portal, ThingsBoard | — | live |
| 9 | Team collaboration | Invite / request-to-join / approve / enable-disable-remove member | Portal, Keycloak | — | live |
| 10 | Platform monitoring (staff) | Staff open Grafana (SSO) → infra dashboards over Prometheus | Grafana, Keycloak, Prometheus | — | live |

**(confirmed** — routes in §3 map 1:1 to these steps.**)**

---

## 7. Entities (data)

| # | Entity | Created & owned by (engine → function) | Also used by | Shared with other Chert systems |
|---|---|---|---|---|
| 1 | User (`PortalUser` + Keycloak user) | Keycloak → registry; Portal → sign up | all functions | no (candidate shared identity — §9) |
| 2 | Role | Portal `permissions` / Keycloak realm roles | all gated functions | no |
| 3 | Organization → **Project** (`Project` = TB Tenant) | Portal → create project | every project function | no |
| 4 | Member (`ProjectMember`) | Portal → Members & Settings | authorization gate | no |
| 5 | Invitation (`ProjectInvite`) | Portal → invitations | join flow | no |
| 6 | Request (`ProjectJoinRequest`) | Portal → join requests | join flow | no |
| 7 | ClassCode | Portal (instructor) → class codes | cohort roster | no |
| 8 | Device (`LoraDevice` + TB Device) | Portal → Devices / LoRaWAN; TB → device mgmt | telemetry, alerts, flows, notebooks | no |
| 9 | SensorReading (TB telemetry) | Device → TB ingest | telemetry, monitoring, reports, notebooks | no |
| 10 | AlertRule (`AlertRule`) → Alarm (TB) | Portal → Alerts; TB → alarms | monitoring, reports | no |
| 11 | Dashboard (TB) | Portal provisioning → starter dashboard | Overview, TB console | no |
| 12 | FlowInstance (`FlowInstance`) | Portal → Flows | automation | no |
| 13 | Document (docs) | Docs site | learn | no |
| 14 | Metric (Prometheus) | exporters → Prometheus | Grafana, alerting | no |
| 15 | AuditLog (`AuditLog`) | Portal → all sensitive actions | audit/ops | no |

Added standard-name note: **SensorReading** = the "Telemetry" timeseries; **Design/Dataset** not used. **(confirmed** — `portal/app/models.py`, `tb_client.py`.**)**

---

## 8. Connections

**8.1 Inside the system.**

| From (engine → function) | To (engine → function) | Data (entity) | How | Status |
|---|---|---|---|---|
| Portal → provision/broker | ThingsBoard → tenant/device/dashboard | Project, Device, Dashboard | REST (`tb_client`, sysadmin impersonation) | live |
| Portal → sign up / SSO | Keycloak → registry/OAuth2 | User, Role | Admin REST + OAuth2 (SSO) | live |
| ThingsBoard → login button | Keycloak → OAuth2 | User | OAuth2 (domain-scoped) | live |
| Grafana → login | Keycloak → OAuth2 (realm roles) | User, Role | OAuth2, role-attribute-path | live |
| Grafana → datasource | Prometheus → query | Metric | HTTP datasource | live |
| Caddy `/flows` → forward_auth | Portal → `/flows/auth` | User (ownership) | forward_auth | live |
| JupyterHub → pre_spawn_hook | Portal → `/internal/lab-token` | Project TB token | internal HTTP | live |
| ChirpStack → uplink | Mosquitto → lora-bridge → ThingsBoard | SensorReading | MQTT + in-house bridge | live |
| Prometheus → scrape | exporters/cAdvisor/TB/Keycloak | Metric | HTTP scrape | live |
| Portal/TB/Keycloak/ChirpStack | PostgreSQL | all persistent entities | SQL (separate DBs) | live |

**8.2 With other Chert systems.** **None found.** A code search for other system names/domains/APIs returned only (a) a dev note that the local Colima VM is shared with unrelated projects `katula`/`chertclub`, and (b) shared **branding/design-system** references (`chertlearninghub`, `chertBI`) in `docs/branding/` — documentation, not runtime links. **(confirmed** — grep across `*.py/*.md/*.yml`.**)** → No live/planned integration in code.

**8.3 With outside services.**

| Function | Outside service | Data | Direction | Status |
|---|---|---|---|---|
| Sign up / email | SMTP provider | verification/notification email | sends | live (config `SMTP_*`) |
| Device connectivity | MQTT/MQTTS (:8883) & HTTP from customer devices | SensorReading | receives | live |
| LoRaWAN | Real LoRa gateways (Semtech UDP :1700) | uplinks | receives | live |
| TLS | ACME/Let's Encrypt (via Caddy) | certificates | both | live (assumed — standard Caddy ACME) |

No payment gateway, ZATCA, SFDA, carrier, ad-platform or SMS integration exists in this repo. **(confirmed** — `.env.example` has only SMTP.**)**

---

## 9. Overlaps with other Chert systems

| Function here | Same function in (codes) | Shared entity | Which system should own it | Connected today? |
|---|---|---|---|---|
| User login / SSO (Keycloak) | likely all systems (E, M, R, …) | User, Role | not decided (candidate: a shared CHERT identity) | no |
| Email sending | M (ChertMail) and others | Message | not decided | no |
| Reporting / dashboards | I (ChertBI) | Metric, Dataset | not decided | no |
| Customer/organization records | E (ChertERP), others | Organization, Customer | not decided | no |
| Design system / branding | all (shared design docs) | — | Chert (central) | partly (docs only) |
| Documentation portal | H (ChertLearningHub) | Document, Course | not decided | no |

**(assumed** — cross-system overlaps are conceptual; no code links exist (see 8.2).**)**

---

## 10. Open questions (for the developer)

1. Is ChertIoT's Keycloak meant to remain standalone, or federate into a **central CHERT identity** shared with other systems (E/M/R/…)? (Today it is standalone.)
2. Should platform reporting/analytics be surfaced through **ChertBI (I)** rather than local Grafana/Reports, and if so via what interface?
3. Is the product intended to stay **Chert-run only**, or also ship as an installable **ChertBox (Box entity)** for a customer's own server? (No ChertBox packaging found.)
4. Exact **licence** per engine is inferred from the upstream project, not declared in-repo — confirm licence obligations (esp. Grafana AGPL, Redis licence).
5. Which environment is the **eventual production** (`main` droplet) and what is the cutover trigger? (Both are "build phase" today.)
6. Should the **docs site / ChertLearningHub (H)** be one shared documentation function across systems?
7. Are `katula`/`chertclub` (dev-VM neighbours) actual CHERT systems that will ever integrate, or unrelated? (Only a shared-VM note exists.)
8. Is a payment/billing or SFDA/ZATCA path ever expected for ChertIoT, or is it purely educational? (None present.)

---

### Self-check
- Every §2 engine has functions in §3. ✓
- Every §3 function belongs to exactly one engine. ✓
- Every §6 process uses §3 functions. ✓
- Every §7 entity has an owner. ✓
- Every other-system mention uses its code. ✓
- No secrets appear anywhere. ✓
