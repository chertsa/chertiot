# ChertIoT — Master Proposal & Build Plan
## Implementation guide for building chertiot.com with Claude Code (VS Code)
**Version:** 1.0 · **Repo:** `chertiot` (monorepo) · **Target:** Single VPS, Docker Compose, fully open-source, multi-tenant IoT lab for students & developers

> **How to use this file:** Place it at the repo root as `PLAN.md`. Work phase by phase, milestone by milestone. Each milestone has concrete tasks and acceptance criteria — do not advance until criteria pass. Keep `CLAUDE.md` (Section 3) updated as the living project memory.

---

# PART A — MASTER PROPOSAL (context for every session)

## 1. What we are building

ChertIoT (chertiot.com) is a self-hosted, multi-tenant IoT laboratory. A student signs up on the portal, receives isolated MQTT credentials and a device namespace, flashes provided ESP32 starter code, and sees live telemetry on a personal dashboard within 10 minutes — no servers of their own, no third-party clouds.

**Core decisions (already made — do not relitigate):**
- **ThingsBoard CE** (Apache-2.0) is the core platform: device connectivity (MQTT/HTTP/CoAP), multi-tenancy (Tenant → Customer → User → Device), telemetry storage, dashboards, rule chains, REST API. We rebrand its UI as ChertIoT via a small isolated patch series.
- **ChertIoT Portal** is the only fully custom component: FastAPI + PostgreSQL + minimal JS frontend. Signup, class codes, automated provisioning via ThingsBoard REST API, docs, admin console. Kept thin.
- **Extensions:** Node-RED (per-user containers, Phase 3), JupyterHub (Phase 3), ChirpStack + internal Mosquitto (Phase 4, LoRa track).
- **Ops:** Caddy (TLS/routing), Prometheus + Grafana admin-only, Uptime Kuma, pgBackRest + restic.
- **Tenancy model:** One TB Tenant per class/community group; students are Customers/Users under it; instructors are Tenant Admins; platform owner is SysAdmin. Extensions always authenticate with the student's own TB credentials — isolation is inherited, never re-implemented.
- **Integration contract:** Portal ↔ ThingsBoard via REST API **only**. Never touch TB's database schema directly.

## 2. Success criteria (whole project)

1. Stranger → signup → live dashboard with real device in **< 10 minutes**, zero admin involvement.
2. Zero cross-tenant data visibility (verified by automated tests).
3. Full platform reproducible on a fresh VPS from this repo + backups in **< 1 hour** (documented drill).
4. A misbehaving device (1000 msg/s flood) cannot degrade other users (rate limits verified by load test).
5. 30–50 student class runs a semester on a 4 vCPU / 8 GB VPS.

---

# PART B — PROJECT SETUP FOR CLAUDE CODE

## 3. `CLAUDE.md` (create this first, verbatim start)

```markdown
# ChertIoT — Claude Code project memory

## What this is
Multi-tenant IoT lab (chertiot.com). ThingsBoard CE core + custom FastAPI portal.
Read PLAN.md for the full build plan. Current phase/milestone tracked below.

## Hard rules
- Portal talks to ThingsBoard via REST API only (client in portal/app/tb_client.py). Never TB's DB.
- No secrets in git. All secrets via .env (gitignored); .env.example stays current.
- Every provisioning action must be idempotent (safe to retry).
- Every milestone: write/extend tests before marking done.
- Docker Compose profiles: core | flows | lab | lora. Don't collapse them.
- ThingsBoard rebrand = patch series in thingsboard-brand/ only. Never scatter edits.
- Python: FastAPI, SQLAlchemy, pydantic v2, pytest, ruff. Node tooling only where upstream requires.

## Current status
Phase: 0  · Milestone: M0.1 · Last completed: —

## Environment
Local dev: docker compose --profile core up. VPS deploy: see deploy/README.md.
TB admin creds, SMTP, domain config: .env (ask user, never invent).

## Key commands
make dev          # local core stack
make test         # portal unit+integration tests
make e2e          # end-to-end provisioning test against local TB
make lint         # ruff + mypy
```

## 4. Monorepo layout (create in M0.1)

```
chertiot/
├── PLAN.md                    # this file
├── CLAUDE.md                  # living project memory (Section 3)
├── Makefile
├── .env.example
├── docker-compose.yml         # profiles: core, flows, lab, lora
├── deploy/                    # VPS provisioning: hardening, compose deploy, runbooks
│   ├── README.md
│   ├── caddy/Caddyfile
│   └── scripts/ (bootstrap.sh, backup.sh, restore-drill.sh)
├── portal/                    # FastAPI app — the custom heart
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── models.py          # signups, class_codes, quotas, audit
│   │   ├── tb_client.py       # ThingsBoard REST wrapper (ONLY TB touchpoint)
│   │   ├── provisioning.py    # idempotent user/device provisioning flows
│   │   ├── routers/ (auth.py, devices.py, admin.py, docs.py)
│   │   └── templates/ + static/
│   ├── tests/ (unit/, integration/, e2e/)
│   └── pyproject.toml
├── thingsboard-brand/         # rebrand patch series + build
│   ├── patches/ (0001-logo.patch, 0002-theme.patch, 0003-titles.patch)
│   ├── assets/ (logo.svg, favicon, palette.md)
│   └── build.sh               # clone upstream tag → apply patches → build image
├── firmware-examples/         # student starter code
│   ├── esp32-arduino/ esp32-micropython/ rpi-python/ browser-js/
│   └── templating notes (portal injects tokens into these)
├── docs-site/                 # student docs (mkdocs-material)
├── monitoring/ (prometheus/, grafana-dashboards/, alert-rules/)
└── tests-platform/            # cross-cutting: tenancy isolation, flood tests
```

## 5. Prerequisites (ask the user; do not guess)

- [ ] VPS provider + SSH access (recommend Hetzner CX32+ / DO 8GB)
- [ ] DNS control for chertiot.com (A records: @, app, flows, lab, lora, status)
- [ ] SMTP credentials for verification email (any provider/relay)
- [ ] GitHub org/repo created; CI runner choice (GitHub Actions default)
- [ ] Decide initial ThingsBoard version tag to pin (check latest stable release at build time)

---

# PART C — PHASED BUILD PLAN

## PHASE 0 — Foundation (est. 2–4 sessions)

### M0.1 Repo scaffold
- Create monorepo layout above; Makefile targets (dev/test/lint/e2e); .env.example; .gitignore; pre-commit with ruff; GitHub Actions CI skeleton (lint + tests on PR).
- **Accept:** `make dev` fails gracefully with "configure .env"; CI green on empty test suite.

### M0.2 Core compose stack (stock, unbranded)
- docker-compose.yml `core` profile: postgres:16, thingsboard/tb-postgres (pinned tag, stock image for now), caddy, prometheus, grafana, uptime-kuma, node_exporter, cadvisor, postgres_exporter.
- Caddyfile: local dev routing (localhost ports); production vhosts commented and templated.
- Named volumes for all state; healthchecks on every service; restart policies.
- **Accept:** `make dev` brings up stack; TB login page reachable; Prometheus scrapes all exporters; docs in deploy/README.md explain every service in 2 lines each.

### M0.3 ThingsBoard exploration & fixture script
- Script `deploy/scripts/tb_bootstrap.py`: logs in as sysadmin, creates demo Tenant "ChertIoT-Dev", one tenant admin, one customer, one device; prints device access token. Idempotent.
- Manually verify: MQTT publish with mosquitto_pub using that token → telemetry visible in TB UI.
- Document findings in CLAUDE.md (TB REST quirks encountered).
- **Accept:** Script rerunnable; published test message visible on a TB dashboard.

## PHASE 1 — Portal core & provisioning (est. 6–10 sessions)

### M1.1 tb_client.py — ThingsBoard REST wrapper
- Auth (JWT + refresh), create/get tenant, customer, user, device; device credentials; server-side attributes; telemetry query; activation email suppression (portal handles email).
- Retry w/ backoff; typed responses (pydantic); comprehensive unit tests with recorded fixtures; integration tests against local TB from M0.2.
- **Accept:** 100% of wrapper methods integration-tested green against live local TB.

### M1.2 Signup & provisioning flow
- Portal: email+password signup → verification email (SMTP) → on verify, `provisioning.py` creates TB Customer+User under the configured class Tenant, first Device, stores mapping in portal DB. Idempotent at every step (safe re-run on partial failure).
- Class codes: instructor-generated codes route signups to specific Tenants; default "community" tenant otherwise.
- **Accept:** e2e test: POST signup → confirm link → TB objects exist → device token retrievable. Partial-failure test: kill TB mid-provision, re-run completes cleanly.

### M1.3 Student dashboard pages
- Portal pages: My Devices (list, last-seen via TB API, create/rename/revoke); Device detail with copy-paste firmware snippets (from firmware-examples/, tokens injected); link-through to TB dashboard (SSO note: Phase-1 = separate TB login with same credentials, document; true SSO deferred).
- **Accept:** New user creates 2nd device and gets working ESP32 snippet without touching TB admin UI.

### M1.4 Quotas & abuse controls
- TB rate limits config (per-tenant/per-device msg rates, payload caps) tuned in compose env; portal enforces max devices per user (default 10); portal audit log table.
- tests-platform/: tenancy isolation test (user A token cannot read user B device), flood test (device at 1000 msg/s throttled, others unaffected — measure).
- **Accept:** Both platform tests pass and run in CI against compose stack.

### 🏁 GATE 1: Local stack demonstrates full signup→device→telemetry with isolation proven. Tag v0.1.0.

## PHASE 2 — Branding, VPS, launch (est. 5–8 sessions)

### M2.1 ThingsBoard rebrand build
- thingsboard-brand/build.sh: clone pinned upstream tag → apply patches (logo, favicon, palette, page titles, login-page text "ChertIoT — powered by ThingsBoard") → build custom image `chertiot/tb:<upstream-tag>-b<u>`.
- Patches minimal & documented; upgrade playbook in thingsboard-brand/README.md (rebase drill on next upstream tag as a test).
- **Accept:** Branded image runs in compose in place of stock; upgrade drill to a newer tag executed once successfully.

### M2.2 VPS deploy & hardening
- deploy/scripts/bootstrap.sh: user, SSH hardening, UFW (22, 80, 443, 8883 only), fail2ban, Docker install, compose up with production .env; Caddy production vhosts + Let's Encrypt; MQTTS 8883 exposed to TB transport.
- **Accept:** All services green on VPS; SSL Labs A grade; external MQTT TLS connect works; ports scan clean.

### M2.3 Backups & restore drill
- pgBackRest nightly + WAL; restic encrypted push of backups+configs to secondary storage; deploy/scripts/restore-drill.sh; alerting if backup age > 26h.
- **Accept:** Executed restore drill onto scratch container/VM documented with timing (< 1 h target).

### M2.4 Docs site & starter content
- mkdocs-material at docs.chertiot.com (or /docs): Getting Started (ESP32 Arduino, MicroPython, RPi, browser-JS), MQTT topics & auth explainer, dashboard how-to, fair-use policy, status page link.
- **Accept:** External tester (real human) goes signup→blinking-data in <10 min using docs alone; friction notes filed as issues.

### 🏁 GATE 2: PUBLIC SOFT LAUNCH — invite 10–20 pilot users. Tag v1.0.0. Run pilots ≥2 weeks; fix before Phase 3.

## PHASE 3 — Power features (est. 6–10 sessions)

### M3.1 Node-RED per-user containers (`flows` profile)
- Spawner service (small FastAPI or portal module): create/start/stop per-user node-red container (CPU 0.5 / RAM 256 MB caps, no host mounts, own volume), routed via Caddy at flows.chertiot.com/<user>/ behind portal auth.
- Pre-provisioned settings.js injecting the user's TB MQTT credentials as env; quota: 1 instance/user, project tier 3.
- **Accept:** Isolation test: user container cannot reach another's editor or the docker socket; resource caps enforced under stress.

### M3.2 JupyterHub (`lab` profile)
- JupyterHub + DockerSpawner, auth vs portal DB (custom authenticator), notebook image w/ pandas+matplotlib+requests + `chertiot.py` helper (TB telemetry fetch with user JWT); caps 1 CPU / 512 MB.
- Example notebooks in image: "Plot your last 24 h", "Anomaly detection on your sensor".
- **Accept:** Student runs example notebook on own telemetry; cannot query another user's device (test).

### M3.3 Instructor & admin console
- Portal: instructor role — generate class codes, roster view (last-seen, device counts, msgs today; no private data), reset student password, suspend.
- Admin: platform stats, user search, quota overrides, broadcast banner.
- **Accept:** Instructor persona walkthrough scripted and passing in e2e suite.

### M3.4 Webhook rules & data export
- Portal-defined simple rules (TB rule-chain templates instantiated via REST): threshold→email/webhook. CSV/JSON export of own telemetry (range-limited, rate-limited).
- **Accept:** Rule fires on test device crossing threshold; export of 100k rows completes and is scoped to owner only.

### 🏁 GATE 3: Feature-complete for a semester course. Tag v1.5.0.

## PHASE 4 — LoRa & advanced tracks (demand-driven)

### M4.1 ChirpStack (`lora` profile): chirpstack + internal mosquitto + redis; TB integration rule mapping uplinks→student devices; gateway onboarding doc.
### M4.2 Optional: eKuiper edge-processing tutorial track; EMQX swap-in evaluation only if TB transport hits limits (load-test first — don't add unprompted).
- **Accept (M4.1):** Real LoRa node uplink lands on the same student dashboard as their WiFi devices.

---

# PART D — WORKING AGREEMENTS FOR CLAUDE CODE SESSIONS

1. **Session start:** read CLAUDE.md status → open PLAN.md at current milestone → state plan for the session in 3 bullets → proceed.
2. **Session end:** update CLAUDE.md (status line + any new gotchas), ensure `make lint test` green, commit with `phase-milestone: summary` messages (e.g., `M1.2: idempotent signup provisioning + partial-failure test`).
3. **Never** mark a milestone done with failing/absent acceptance tests. If blocked on a prerequisite (Section 5), stop and ask the user — do not stub secrets or fake external services in production paths.
4. **Version pinning:** every image and dependency pinned; upgrades are deliberate milestones, not side effects.
5. **When TB's API surprises you** (it will): capture the workaround in tb_client.py with a comment + CLAUDE.md note, and add a regression test.
6. **Scope discipline:** anything not in this plan goes to `BACKLOG.md`, not into the current milestone.

---

*End of plan. First action for a fresh Claude Code session: execute M0.1.*
