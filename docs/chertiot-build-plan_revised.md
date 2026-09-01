# CHERT IoT — Production Build Plan (PLAN.md)
**Goal:** Multi-tenant IoT lab for students at chertiot.com. Production from day one. No pilot.
**How to use:** Place at repo root. Work milestone by milestone. Don't advance until acceptance criteria pass. Keep CLAUDE.md status updated every session.

---

## 1. DECISIONS — FINAL, DO NOT RELITIGATE

| # | Decision |
|---|----------|
| D1 | **Brand:** "CHERT IoT" in all UI/display text. Code, repos, DB, containers, domain: lowercase `chertiot`. |
| D2 | **Core:** ThingsBoard CE (Apache-2.0), pinned version, built from source with rebrand patch series. |
| D3 | **Identity:** Keycloak from day one at auth.chertiot.com. Single login for portal, TB, JupyterHub, Grafana, Node-RED. TB is an OAuth2 *client* of Keycloak, never the IdP. |
| D4 | **Tenancy:** ONE TENANT PER STUDENT. Student = Tenant Admin of own tenant → full rights (create devices, dashboards, rule chains, alarms). Quotas via TB tenant profiles (10 devices, 10 msg/s, capped API — env-tunable). Optional shared "class tenant" per course for group exercises. Never customer-per-student (CE customers are read-only). |
| D5 | **Starter content:** At signup, portal copies template dashboards INTO the student tenant (editable, theirs). "Reset dashboard" = re-import. Pristine references live in docs site. |
| D6 | **Instructor view:** Lives in OUR portal (roster: last-seen, device counts, msg volume via sysadmin REST API + "login as user" for support). Not in TB. |
| D7 | **Rebrand:** Source-built patch series in `thingsboard-brand/` (logo, favicon, theme, titles, login text, email templates). Never scattered edits. Overlay/proxy-rewrite is fallback only. |
| D8 | **MQTTS:** TLS terminated at Caddy layer4 (pinned xcaddy build), port 8883. Devices auth with TB access tokens. (If X.509 device auth ever needed → switch to passthrough; config change, noted, not built now.) |
| D9 | **Infra:** Production VPS 8 vCPU / 16 GB from day one + small staging VPS (~€10–15/mo). Nothing reaches production untested on staging. |
| D10 | **Integration contract:** Portal ↔ TB via REST API only (`portal/app/tb_client.py`). Never TB's database. Extensions always use the student's own credentials — isolation is inherited, never re-implemented. |
| D11 | **Minors-safe by default at launch:** age attestation on open signup; minor cohorts only via instructor class codes (consent responsibility on institution); minimal data collection; no third-party analytics; telemetry retention 90d; IP/audit logs 30d; plain-language privacy page live before first signup. |
| D12 | **Scope discipline:** Anything not in this plan → BACKLOG.md. |

## 2. STACK (all self-hosted, Docker Compose profiles)

| Profile | Services |
|---|---|
| `core` | Caddy (TLS/routing/layer4-MQTTS) · Keycloak · ThingsBoard CE (branded build) · PostgreSQL 16 · Portal (FastAPI) · Prometheus + exporters · Grafana (admin-only) · Uptime Kuma |
| `flows` | Node-RED per-student containers (spawner; 0.5 CPU / 256 MB caps; Caddy forward-auth → Keycloak) |
| `lab` | JupyterHub + DockerSpawner (OIDC → Keycloak; 1 CPU / 512 MB caps; idle-cull 30 min) |
| `lora` | ChirpStack + internal Mosquitto + Redis (demand-driven, Phase 4) |
| Backups | pgBackRest (nightly + WAL) + restic (encrypted off-site) |

Routing: chertiot.com→Portal · app.→TB · auth.→Keycloak · lab.→JupyterHub · flows.→Node-RED · status.→Uptime Kuma · 8883→TB MQTT.

## 3. REPO LAYOUT

```
chertiot/
├── PLAN.md  CLAUDE.md  BACKLOG.md  Makefile  .env.example  docker-compose.yml
├── deploy/            # bootstrap.sh (hardening/UFW/fail2ban), Caddyfile, backup/restore scripts, staging config, runbooks
├── portal/            # FastAPI: app/{main,config,models,tb_client,provisioning,routers/,templates/}, tests/{unit,integration,e2e}
├── keycloak/          # realm export (chertiot realm, clients: portal/tb/jupyterhub/grafana), theme (CHERT IoT login page)
├── thingsboard-brand/ # patches/ assets/ build.sh (clone pinned tag → apply → build image) README (upgrade drill)
├── templates-tb/      # starter dashboard JSON + tenant profile JSON (imported per student at signup)
├── firmware-examples/ # esp32-arduino/ esp32-micropython/ rpi-python/ browser-js/ (portal injects tokens)
├── docs-site/         # mkdocs-material: getting started, MQTT guide, dashboard how-to, privacy, fair use
├── monitoring/        # prometheus rules (disk, RAM, cert<14d, backup-age>26h, TB/Keycloak down), grafana dashboards
└── tests-platform/    # tenancy isolation, flood/rate-limit, e2e signup→telemetry
```

## 4. CLAUDE.md SEED (create verbatim in M0.1, then keep updated)

```markdown
# CHERT IoT — project memory
Read PLAN.md. Current: Phase 0 / M0.1. Last done: —
## Hard rules
- Decisions D1–D12 in PLAN.md are final.
- Brand: "CHERT IoT" display / `chertiot` code+domain.
- Portal→TB: REST only via tb_client.py. Idempotent provisioning, always.
- No secrets in git; .env only; .env.example current. Never invent creds — ask.
- Tests green before a milestone is done. make lint test must pass at session end.
- Staging before production, every time.
- Pin every image/dependency. Upgrades are deliberate milestones.
- TB API surprises → workaround in tb_client.py + note here + regression test.
## Commands
make dev | test | e2e | lint | staging-deploy | prod-deploy
```

## 5. PREREQUISITES (ask user — never guess)
- [ ] Production VPS (8 vCPU/16 GB) + staging VPS, SSH access
- [ ] DNS control: A records @, app, auth, lab, flows, lora, status (+staging.*)
- [ ] SMTP credentials (Keycloak + portal email)
- [ ] GitHub repo/org; Actions for CI
- [ ] Pin versions at M0.2: latest stable ThingsBoard CE + Keycloak tags (check at build time)

---

## 6. MILESTONES

### PHASE 0 — Foundation
**M0.1 Scaffold.** Repo layout, Makefile, .env.example, CI (lint+test on PR), CLAUDE.md seed, BACKLOG.md.
✔ `make dev` fails gracefully asking for .env; CI green.

**M0.2 Core stack (stock images).** Compose `core` profile incl. Keycloak; healthchecks, named volumes, restart policies; local Caddy routing; pinned tags.
✔ All services up; TB + Keycloak UIs reachable; Prometheus scraping all targets.

**M0.3 Keycloak realm + TB OAuth2.** Realm `chertiot` (clients: portal, thingsboard, jupyterhub, grafana; email flows; CHERT IoT login theme), realm export in repo. Configure TB OAuth2 client + mapper. **Verify the critical unknown:** Keycloak login auto-creates/maps a TB tenant-per-user OR portal handles tenant creation — test both, record working approach in CLAUDE.md.
✔ Browser: Keycloak login → lands in TB as tenant admin of own tenant. Realm reimportable from export.

**M0.4 tb_client.py + tenant provisioning core.** Sysadmin auth (JWT+refresh, retry/backoff, pydantic); create tenant (from tenant-profile JSON with quotas), tenant admin user, device + credentials; import dashboard JSON from templates-tb/; delete/suspend tenant. Integration tests vs local TB.
✔ Script: fresh student tenant with quotas + starter dashboard + device token, end-to-end, idempotent (safe rerun on partial failure). mosquitto_pub with token → telemetry on the starter dashboard.

### PHASE 1 — Portal
**M1.1 Signup.** Portal registers user in Keycloak (or Keycloak self-registration + portal webhook — pick simpler at build time); email verification; age attestation (D11); class-code field (instructor codes → tag cohort; else community). On verify → M0.4 provisioning runs. Portal DB: users↔tenant map, class codes, audit.
✔ e2e: signup→verify→own TB tenant with dashboard+device. Partial-failure test passes. One login (Keycloak) reaches portal AND TB with no second prompt.

**M1.2 Student pages.** My Devices (list/create/rename/revoke, last-seen via TB API); device page with copy-paste firmware snippets (tokens injected from firmware-examples/); "Open my dashboard" (SSO into TB); "Reset starter dashboard" (re-import); usage/quota view.
✔ Student adds 2nd device and flashes working snippet without touching TB admin screens.

**M1.3 Abuse controls + platform tests.** Tenant-profile quotas enforced (verify with flood test: 1000 msg/s device throttled, others unaffected — measure); portal rate limits on auth endpoints; audit log.
✔ tests-platform/: isolation test (student A token cannot read B's tenant/devices) + flood test green in CI.

**🏁 GATE 1 (local):** signup→device→telemetry→dashboard, one login, isolation proven. Tag v0.9.0.

### PHASE 2 — Brand, deploy, LAUNCH
**M2.1 TB branded build.** thingsboard-brand/build.sh: clone pinned tag → patches (logo/favicon/theme/titles/login "CHERT IoT — powered by ThingsBoard"/email templates) → image `chertiot/tb:<tag>-bN`. Upgrade drill on staging documented + executed once. CI smoke test: branded strings present post-build.
✔ Branded image replaces stock in compose; drill done.

**M2.2 Staging deploy.** bootstrap.sh (user, SSH hardening, UFW 22/80/443/8883, fail2ban, Docker); staging.* domains, Let's Encrypt, layer4 MQTTS; full e2e suite against staging incl. real ESP32 over internet.
✔ Staging green; external MQTTS device streams to dashboard.

**M2.3 Production deploy + ops.** Same to prod VPS; pgBackRest + restic + **executed restore drill onto staging (<1 h, documented)**; alerting live (disk/RAM/certs<14d/backup-age/TB+Keycloak down → email); Uptime Kuma public status page; maintenance-window policy published.
✔ All alerts test-fired; restore drill report in deploy/runbooks/.

**M2.4 Docs + legal-lite.** Getting-started (ESP32 Arduino/MicroPython, RPi, browser-JS), MQTT/auth explainer, dashboard tutorial, fair-use, plain-language privacy page (D11), service-expectation note ("best-effort, maintenance Sundays, see status page").
✔ Outside human: signup→live data <10 min using docs alone.

**🏁 GATE 2 — PRODUCTION LAUNCH.** Blockers (no exceptions): restore drill done · isolation+flood tests in CI · alerting live · status page up · privacy page live · docs verified. Tag v1.0.0.

### PHASE 3 — Power features (post-launch, staging-first)
**M3.1 Node-RED per-student.** Spawner (create/start/stop container, caps, own volume, no host mounts, stop-on-idle); Caddy forward-auth→Keycloak; TB MQTT creds injected. ✔ Isolation + resource-cap tests.
**M3.2 JupyterHub.** OIDC→Keycloak; notebook image (pandas/matplotlib/requests + chertiot.py TB-fetch helper); idle-cull 30 min; example notebooks. ✔ Student plots own telemetry; cannot query another tenant (test).
**M3.3 Instructor console.** Class-code management; roster (last-seen/devices/msgs via sysadmin API); login-as for support; suspend/reset. ✔ Scripted instructor e2e green.
**M3.4 Alerts + export.** Portal-defined threshold→email/webhook (TB rule-chain templates via REST); CSV/JSON export of own telemetry (range+rate limited). ✔ Rule fires; 100k-row export scoped to owner.
**🏁 GATE 3:** semester-ready. Tag v1.5.0.

### PHASE 4 — Demand-driven
**M4.1 ChirpStack** (`lora` profile) + TB integration: LoRa uplinks land on the same student dashboards; gateway onboarding doc.
**M4.2** eKuiper edge track / EMQX evaluation — only if load tests demand. Everything else → BACKLOG.md.

---

## 7. SESSION PROTOCOL
1. Start: read CLAUDE.md → open current milestone → state 3-bullet session plan → build.
2. End: update CLAUDE.md status/gotchas; `make lint test` green; commit `M<x.y>: summary`.
3. Blocked on a prerequisite/secret → stop and ask the user. Never stub production paths.
4. Milestone done = acceptance criteria demonstrably pass. No exceptions, this is production.
