# CHERT IoT — Journeys & Services

How the platform's open-source engines fit together, and the detailed journeys — student,
instructor, operator, and the device itself — that turn them into one **unified IoT teaching lab**
at [chertiot.com](https://chertiot.com).

**Build:** v1.6.0 (Phases 0–4 complete) · **Live:** production + staging on DigitalOcean.

---

## 1. The idea — one lab, one login, real hardware

A student signs up once and immediately owns a **real, isolated IoT workspace**: their own
ThingsBoard tenant, a device token, ready-to-flash firmware, live dashboards, a visual flow editor,
a Python notebook, threshold alerts, and a LoRaWAN path — all behind a **single sign-on** and all
built from proven open-source engines rather than bespoke code. The portal is the only custom piece;
everything else is a self-hosted engine integrated through its public API.

**Design rules that make it "unified":**
- **One identity (Keycloak).** The portal, ThingsBoard, JupyterHub and Grafana are all OIDC clients
  of the same realm — log in once, reach everything.
- **One tenant per student (ThingsBoard).** Each student is Tenant Admin of their own tenant, so
  isolation is inherited from the engine, never re-implemented.
- **REST-only integration.** The portal talks to ThingsBoard exclusively through its REST API
  (`tb_client.py`), always with the student's own credentials.
- **Reproducible.** The whole platform is one Docker Compose file with profiles `core | flows | lab | lora`,
  deployed staging-first, pinned and frozen.

---

## 2. The engines & services (what each one does)

| Engine / service | Role in the lab | Student sees it as |
|---|---|---|
| **Caddy + layer4** | TLS for every subdomain; HTTP routing; terminates **MQTTS 8883 → ThingsBoard MQTT** so devices need only a token, no certificate. | The `https://` padlock and the `chertiot.com:8883` broker. |
| **Keycloak** | Identity provider. Holds every password; issues the one login for portal + ThingsBoard + JupyterHub + Grafana; sends verification email. | "Sign in with CHERT IoT". |
| **Portal (FastAPI)** | The custom glue: signup, provisioning, device pages, firmware snippets, `/flows`, `/lab` tokens, `/teach`, `/lora`, alerts, exports, i18n (EN/AR). | The chertiot.com website itself. |
| **ThingsBoard CE** | The IoT core: device connectivity, telemetry storage, dashboards, rule chains, alarms, per-tenant quotas. One tenant per student. | "My dashboard", devices, alarms. |
| **PostgreSQL 16** | One instance, four DBs: `thingsboard`, `keycloak`, `portal`, `chirpstack`. | (invisible) |
| **Node-RED** (per student) | A private low-code flow editor, spawned on demand, isolated by container + proxy auth; TB credentials pre-injected. | `/flows` → "CHERT Node" editor. |
| **JupyterHub + DockerSpawner** | Per-student Python notebooks with a `chertiot.py` helper that fetches their own telemetry. | `lab.chertiot.com`. |
| **ChirpStack + Gateway Bridge + Mosquitto + Redis** | LoRaWAN network server; a bridge forwards uplinks to the owning student's TB device by DevEUI. | `/lora` registration + uplinks on the dashboard. |
| **Prometheus + Alertmanager + Grafana + exporters** | Platform metrics, alert rules, admin dashboards; Alertmanager emails on failures. | (admin only) `grafana.chertiot.com`. |
| **Uptime Kuma** | Public status page + up/down monitoring. | `status.chertiot.com`. |
| **restic** | Nightly encrypted backups (pg_dump of all DBs + configs/volumes) to the other droplet; proven restore drill. | (invisible) |
| **mkdocs-material** | Student documentation, bilingual (EN/AR). | `/docs/`. |

**Routing map** (one Caddyfile, `{$DOMAIN}` per environment):
`chertiot.com`→portal · `app.`→ThingsBoard · `auth.`→Keycloak · `flows.`→Node-RED (per-user,
`forward_auth`) · `lab.`→JupyterHub · `lora.`→redirect to `/lora` · `status.`→Uptime Kuma ·
`grafana.`→Grafana · `:8883`→ThingsBoard MQTT.

---

## 3. Student journey — from nothing to live data (~10 minutes)

```
signup → verify email → sign in (SSO) → auto-provision → device + token
      → flash firmware → MQTTS telemetry → live dashboard → flows / lab / alerts / LoRa
```

### 3.1 Sign up & verify
- `/signup`: email + password + **age attestation** (minors-safe by default) + optional **class code**.
- The portal creates the user in Keycloak (unverified) via its service account — the portal never
  stores the password. Keycloak emails a verification link (SMTP2GO).
- Click the link → email verified → return to the portal.

### 3.2 First sign-in → automatic provisioning
On the first verified login the portal runs **idempotent provisioning** against ThingsBoard:
1. ensure the `chertiot-student` tenant profile (quotas: 10 devices, 10 msg/s + 300/min per device,
   90-day telemetry retention);
2. create the student's **tenant** (named by email) with the student as **Tenant Admin**;
3. import the **starter dashboard** (editable copy) and create a **starter device** with a token.
The same routine repairs drift on every later login (deleted a device? it's recreated).

### 3.3 Connect a device
- **My devices** lists devices with online state; add up to 10.
- Each device page shows the **access token**, broker (`chertiot.com:8883`), topic
  (`v1/devices/me/telemetry`), an HTTP alternative, and **ready-to-flash starter code** for four
  tracks (ESP32 Arduino, ESP32 MicroPython, Raspberry Pi Python, browser JS) with the token and
  broker already filled in.
- The device connects over **MQTTS 8883** (TLS terminates at Caddy; TB sees plain MQTT), authenticates
  with the token as the MQTT username, and publishes JSON telemetry.

### 3.4 See the data
- **Open my dashboard** → single-click SSO into ThingsBoard → the student's **"My devices"** dashboard
  (Temperature/Humidity charts, latest-telemetry table) updates within seconds.
- **Reset starter dashboard** re-imports the pristine template without touching devices or data.
- **Issue new token** instantly revokes a leaked token.

### 3.5 Go further (the "lab")
- **Flows (`/flows`)** — start a private **CHERT Node** (Node-RED) editor (0.5 CPU / 256 MB, idle-culled
  at 30 min). TB MQTT credentials are pre-injected as `TB_MQTT_HOST/PORT/ACCESS_TOKEN`. Wire device
  data to logic, dashboards or outgoing calls — no code. The editor is isolated: only the owner reaches it.
- **Lab (`lab.chertiot.com`)** — a JupyterHub notebook (1 CPU / 512 MB, idle-culled) with pandas/
  matplotlib and `chertiot.py` to pull **your** telemetry and plot it. You cannot query another tenant.
- **Alerts (`/alerts`)** — set a threshold (e.g. temperature > X); it becomes a per-tenant rule chain
  that raises an alarm and optionally emails/webhooks when a reading crosses. Export your telemetry as
  CSV/JSON (range-limited, scoped to you).
- **LoRaWAN (`/lora`)** — register a LoRa device to get OTAA credentials (DevEUI/AppKey), point a
  gateway at `chertiot.com:1700/udp` (EU868); uplinks arrive on your dashboard alongside Wi-Fi devices.

### 3.6 Everyday
Rename/delete devices, watch quota usage, read the docs (`/docs/`, English or Arabic RTL), and
**sign out** cleanly (clears the session and the SSO login).

---

## 4. Instructor journey — the `/teach` console
1. An instructor account (role granted by the operator) opens **`/teach`**.
2. **Create class codes** (with expiry and max uses); share the code so students join a **cohort** at
   signup (or at `/join`).
3. **Roster** — see each student's last-seen, device count and message volume (never their private
   telemetry).
4. **Suspend** a student — disables their Keycloak login and flags them in ThingsBoard.
Everything an instructor sees is their own cohort; the console never exposes another instructor's data.

---

## 5. Operator / admin journey
| Task | How |
|---|---|
| Deploy | `make staging-deploy` / `make prod-deploy` → `deploy/scripts/deploy.sh` (git pull on server → compose build → caddy re-create for Caddyfile changes → health gate → idempotent Keycloak/TB/ChirpStack/status bootstrap → smoke). **Staging first, always.** |
| New server | `deploy/scripts/bootstrap.sh` (hardening, UFW 22/80/443/8883, fail2ban, swap, Docker). |
| Watch | Grafana (metrics), Prometheus/Alertmanager (email alerts), Uptime Kuma (public status). |
| Back up / restore | Nightly restic to the other droplet; restore drill via `restore-drill.sh` (proven ~260 s). |
| Back-office | Keycloak admin (`auth.…/admin`), ThingsBoard sysadmin (all tenants), Grafana, Uptime Kuma — creds in git-ignored `deploy/secrets.production-admin.env`. |
| Seed test users | `scripts.seed_uat` (idempotent pre-verified, provisioned accounts). |

**Frozen posture:** all engine versions are pinned and **not upgraded** (owner ruling); the branded
ThingsBoard and layer4 Caddy images are still built once from their pinned tags in CI.

---

## 6. The device's journey (what the firmware sees)
Connect `chertiot.com:8883` with TLS (public CA — no cert to provision) → authenticate with the
access token as the MQTT username → publish JSON to `v1/devices/me/telemetry` → ThingsBoard timestamps,
rate-checks against the tenant profile, and stores it in the Postgres timeseries → dashboards and the
REST API serve it back, **scoped to the owning tenant only**. Over-limit messages are dropped; a
persistent flooder is disconnected (proven by the nightly flood test) while neighbours are unaffected.

---

## 7. How the pieces deliver value (the unified loop)
1. **Identity** (Keycloak) makes one login reach every tool → no friction, no per-app accounts.
2. **Ownership** (ThingsBoard tenant-per-student) gives each learner a real, safe sandbox → they can
   break things without touching anyone else.
3. **On-ramps** (firmware snippets + MQTTS + HTTP) get hardware or a browser sending data in minutes.
4. **Depth** (Node-RED, JupyterHub, alerts, LoRaWAN) lets the same data drive low-code logic, Python
   analysis, notifications and long-range radio — one dataset, many lenses.
5. **Trust** (isolation tests, quotas, backups, status page, alerting) keeps it production-grade.

The result is a lab a class can use on day one and a curriculum can grow into — assembled from
open-source engines, integrated cleanly, and reproducible from a single repository.

---

*See also: `docs/architecture.md` (system diagram, engines & licenses), `docs/uat/UAT-PLAN.md`,
and the student-facing `student_user_guide.md`.*
