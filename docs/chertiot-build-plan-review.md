# ChertIoT build plan — architect review & revised draft
**Reviewer:** Claude (architect/dev) · **Date:** 2026-08-30 · **Against:** `docs/chertiot-build-plan.md` v1.0

Legend: ✅ keep · ⚠️ change · ➕ add · ❓ needs your ruling

---

## 0. Verdict

The plan is sound: ThingsBoard CE as the core, a thin FastAPI portal talking REST-only, profiles for optional stacks, gates with acceptance tests. I would ship it with **six structural corrections** before M0.1, because each one changes files created in Phase 0/1:

| # | Issue | Why it matters now |
|---|---|---|
| 1 | Portal must **not** own passwords — ThingsBoard is the identity provider | Changes `models.py`, `routers/auth.py`, the whole M1.2 flow |
| 2 | `thingsboard/tb-postgres` + separate `postgres:16` is a contradiction | Changes `docker-compose.yml` in M0.2 |
| 3 | "Personal dashboard" ≠ student-editable dashboard in CE | Changes M1.3 scope and what we promise in docs |
| 4 | Rebrand via source-patch series is the expensive option; a runtime overlay covers 90% | Changes `thingsboard-brand/` layout and M2.1 effort (weeks → a day) |
| 5 | MQTTS 8883 is unplanned: Caddy doesn't proxy MQTT without layer4 | Adds a decision in M0.2/M2.2 |
| 6 | Phase 3 per-user containers don't fit an 8 GB VPS at the stated caps | Changes success criterion 5 or Phase 3 design (idle-culling) |

Plus one naming ruling (❓ §1.4) before any UI text is written.

---

## 1. Section-by-section comments

### Part A — Proposal

**§1 Core decisions** ✅ with three notes:

- ⚠️ *"Extensions always authenticate with the student's own TB credentials"* — correct principle, but it only works if the portal never holds a second password. See §1.2 below (decision 1).
- ✅ REST-only integration contract. Add: **also never exec into the TB container or edit its files at runtime** — the rebrand overlay (decision 4) is applied at image/volume level, not by mutating a running container.
- ➕ Record non-obvious decisions as ADRs in `docs/adr/` (same format as chertshub `docs/adr/0001…`). The plan already has several "do not relitigate" decisions; they belong in ADR-0001..0006 so a future session can see *why*.

**§1.4 Naming** ❓ The CHERT Design System §1.4 says: wordmark is **CHERT** (caps), products are "CHERT <Product>", never "Chert" in sentence case, and code/URL form is one lowercase word. "ChertIoT" violates that rule. Options:
- (a) Product = **CHERT IoT**, URL/code `chertiot` — consistent with the design system. *(my recommendation)*
- (b) Keep "ChertIoT" and amend the design system.
This affects page titles, login text, email templates, and the TB rebrand — decide before M1.3.

**§2 Success criteria** ✅ Suggested tightenings:
- #4: define "cannot degrade" measurably: *p95 telemetry latency for a control device stays < 500 ms while a flood device is throttled.*
- #5: add a memory budget line (see §3.6). As written, criterion 5 and Phase 3 contradict each other.
- ➕ #6: **Upgrade drill** — a newer TB tag can be adopted in < 1 session with the brand overlay intact. (The plan mentions it in M2.1; it deserves criterion status because it's the main long-term cost of the rebrand.)

### Part B — Setup

**§3 CLAUDE.md** ✅ Additions:
- Hard rule: *"Decisions that aren't obvious from code go in docs/adr/NNNN-*.md, not chat."*
- Hard rule: *"Portal stores no user passwords. Login = TB `/api/auth/login`."*
- Hard rule: *"UI uses chert-tokens.css from docs/branding; never a raw hex."*
- Replace `make lint` = ruff + mypy with ruff + mypy **+ compose config validation** (`docker compose config -q` for every profile) — cheap and catches most compose drift.

**§4 Monorepo layout** ⚠️
- `PLAN.md` at root: fine, but keep it as a symlink/copy of `docs/chertiot-build-plan.md` — don't have two diverging copies. I'd keep `docs/` canonical and put a 3-line `PLAN.md` pointer at root.
- `thingsboard-brand/patches/` → rename to `thingsboard-brand/overlay/` (static asset overrides + Caddy rewrite rules) with `patches/` reserved for the day we actually need a source build (decision 4).
- `thingsboard-brand/assets/logo.svg, palette.md` → **don't duplicate**; reference `docs/branding/logo-master.svg` and `docs/branding/tokens/*.json`. One source of truth.
- ➕ `docs/adr/`.
- ➕ `portal/app/frontend` note: server-rendered **Jinja2 + HTMX**, no SPA build step. "Minimal JS frontend" should mean *no Node toolchain in the portal at all*.
- ➕ `deploy/scripts/tb_bootstrap.py` is called from M0.3 but lives outside `portal/`. It will need `tb_client.py`. Move it to `portal/scripts/tb_bootstrap.py` so it imports the real client instead of duplicating auth code.

**§5 Prerequisites** ➕ missing:
- SMTP domain **SPF/DKIM/DMARC** set up — verification mail landing in spam kills the 10-minute criterion.
- Privacy policy / ToS text (students are real users; possibly minors — ❓ are under-18s in scope?).
- Secondary backup target (Hetzner Storage Box / S3 bucket) credentials.
- Who owns the TB sysadmin account after bootstrap (rotate the default `sysadmin@thingsboard.org` password immediately; store in `.env`).

### Part C — Phases

#### Phase 0

**M0.1** ✅. Add: `git init` (repo isn't one yet), `docs/adr/0001-record-architecture-decisions.md`, and `make check-profiles`.

**M0.2** ⚠️ Three changes:
1. **Image choice.** `thingsboard/tb-postgres` embeds its own PostgreSQL; it cannot use the external `postgres:16` in the same list. Use **`thingsboard/tb-node`** (monolith: core + all transports + UI) with `SPRING_DATASOURCE_URL` pointing at `postgres:16`, `TB_QUEUE_TYPE=in-memory` (fine for one node), and `DATABASE_TS_TYPE=sql` (timeseries in Postgres — no Cassandra at this scale; TimescaleDB is an optional later switch). Disable transports we don't use (`COAP_ENABLED=false`, `LWM2M_ENABLED=false`, `SNMP_ENABLED=false`) — saves a few hundred MB.
2. **Scope.** Bring up only `postgres + tb-node + caddy` in M0.2. Move Prometheus/Grafana/exporters/Uptime Kuma to a new **M0.4 Monitoring** so M0.3 (the first real TB learning) isn't blocked on nine services' healthchecks.
3. **MQTTS.** Decide now how 8883 works (decision 5). Recommendation: build Caddy with the `layer4` module (`xcaddy`, pinned) and terminate TLS in Caddy → forward to `tb:1883`. Alternative: hand Let's Encrypt certs to TB via a sidecar that copies from Caddy's storage and sets `MQTT_SSL_*`. I prefer layer4: one cert manager, TB config stays stock. Record as ADR.

**M0.3** ✅. Add to the bootstrap: create a **Tenant Profile** "chert-class" with rate limits (`transportTenantMsgRateLimit`, `transportDeviceMsgRateLimit`, `maxDevices`, telemetry TTL) — rate limits in TB CE live in tenant profiles set via REST, **not** in compose env as M1.4 assumes. Also create a **Device Profile** "chert-default" (default MQTT topics, no provisioning strategy). Rotate sysadmin password.

#### Phase 1

**M1.1 tb_client.py** ✅. Add methods: `get_activation_link(user_id)` + `activate_user(token, password)` (this is how you set a password without email), `assign_dashboard_to_customer`, `create_dashboard(from_template_json)`, tenant-profile CRUD. Use `httpx` + `tenacity`; record fixtures with `respx`. Note the TB JWT is ~2.5 h and the refresh token ~1 week; a sysadmin/tenant-admin *service* session must refresh proactively.

**M1.2 Signup** ⚠️ **Decision 1 — TB is the IdP.** Flow:
1. POST signup (email, password, optional class code) → portal stores `signups(email, class_code, verify_token, expires)` — **no password hash**; hold the password only in memory/Redis-less signed token for ≤ 1 h, or better: collect the password on the *verify* page, not the signup form.
2. Verify link → portal creates TB Customer (`name = email`), TB User under it, fetches activation link, calls activate with the password → TB now owns the credential.
3. Creates first device (name `"{customer-id-prefix}-device-1"`; device names are unique **per tenant**, so prefix them), assigns dashboard template to the customer.
4. Portal login = `POST /api/auth/login` to TB; the portal keeps the TB JWT in a server-side session. Password reset = TB's own reset flow with SMTP configured in TB (or portal-triggered `resetPassword` via REST).
Result: no password sync problem, extensions (Node-RED/Jupyter) log in against TB with the same credentials as promised in §1, and the portal DB shrinks to `signups`, `class_codes`, `user_map(tb_user_id, tb_customer_id, tenant_id, role)`, `quotas`, `audit`.

Idempotency: every step keyed on `email`; provisioning re-runs look up by name before creating. Add a `provisioning_state` column so partial-failure recovery is explicit, not inferred.

**M1.3 Dashboard pages** ⚠️ **Decision 3.** In TB CE, **Customer users cannot create or edit dashboards** — they only view dashboards the tenant admin assigned to their customer. So the "personal dashboard" is: the portal (as tenant admin) instantiates a dashboard from a JSON template with an alias "all devices of current customer" and assigns it to the student's Customer. Students see live data for all *their* devices but cannot add widgets. For a lab this is acceptable and arguably desirable (they focus on the device side). Document it honestly in the student docs. If pilots demand self-built dashboards, the fallback is **one Tenant per student** (full editing rights; instructor roster then comes from the portal DB rather than TB) — that's a Phase 2+ ADR, not a Phase 1 decision.

Also: link-through to TB is a *second login* with the same credentials. Later improvement: TB CE supports OAuth2 login; the portal could become an OIDC provider — over-engineering for now; put in BACKLOG.

**M1.4 Quotas** ⚠️ Rate limits come from the tenant profile (set in M0.3/M1.1), not compose env. The flood test should run **nightly / on-demand**, not on every PR — a 1000 msg/s test in GitHub Actions is slow and flaky. Isolation test on every PR is fine (it's cheap: two customers, one token, expect 403/empty).

➕ Also cap **portal-side**: signups per IP/hour, devices per user (10), telemetry keys per device (TB tenant profile `maxDataPoints`/`maxTelemetryKeys` or similar per version — verify at build time).

#### Phase 2

**M2.1 Rebrand** ⚠️ **Decision 4.** Building TB from source (Java + Angular `ui-ngx`) takes 30–60 min and > 8 GB RAM, and every upstream tag means a rebase. CE has no white-label feature, but the branded surface is small: logo SVG, favicon, page `<title>`, login page text, primary colour. Recommendation, in order:
1. **Overlay image**: `FROM thingsboard/tb-node:<tag>`, `COPY overlay/ /usr/share/thingsboard/…/static/` replacing logo/favicon files — a 5-line Dockerfile, rebuilt in seconds per upstream tag.
2. **Caddy response rewrite** (`replace-response` module, pinned) for `<title>ThingsBoard</title>` → product name and the login-page strings. Keep the "powered by ThingsBoard" footer/about text (Apache-2.0 attribution; also matches the identity-map constraint: upstream name off the *marketing* surfaces, license notices intact).
3. Primary colour: TB CE supports a custom CSS on the tenant's white-label? No — CE doesn't. Accept the stock blue in TB in Phase 2; a source patch for the palette becomes M2.1b only if the pilot flags it. Note the brand rule: chert-orange is **fill only**, so a full TB palette swap needs care anyway.
Keep `patches/` as the escape hatch; do the upgrade drill against the overlay.

**M2.2 VPS** ✅. Add: unattended-upgrades, Docker log rotation (`json-file` max-size), `sysctl` for connection counts, and a `docker-socket-proxy` container now (Phase 3 spawners will need it; better to design the network with it from the start). Caddy must be the `xcaddy` build (layer4 + replace-response) — one custom image, pinned, built in CI.

**M2.3 Backups** ⚠️ pgBackRest + WAL **and** restic is two backup systems for one ~few-GB database. Simplify: nightly `pg_dump -Fc` of both DBs (TB + portal) + `restic` push of dumps + `.env` + Caddy storage + named volumes to the secondary target; retention 7d/4w/6m; alert if last snapshot > 26 h. RPO 24 h is fine for a lab. Upgrade to pgBackRest only if someone asks for point-in-time restore. Restore drill stays.

**M2.4 Docs** ✅. Start the docs skeleton in **Phase 1** (M1.3 needs the same snippets) so Phase 2 is polishing, not writing. Add a "What you can't do (yet)" page — dashboard editing limits, rate limits, retention.

#### Phase 3

**M3.1 Node-RED / M3.2 JupyterHub** ⚠️ **Decision 6 — memory budget.** TB node ≈ 2–3 GB, Postgres 0.5–1 GB, Caddy/monitoring 0.5 GB ⇒ ~4 GB free on an 8 GB box. 50 students × (256 MB Node-RED + 512 MB Jupyter) = 38 GB at cap. Either:
- (a) **Idle culling**: spawn on demand, stop after 30 min idle (JupyterHub has `idle-culler`; write the equivalent for the Node-RED spawner), assume ≤ 8 concurrent → fits. *(recommended; add "≤ 8 concurrent extension sessions" to success criterion 5)*
- (b) Bigger VPS for the semester (16 GB), or
- (c) Extensions on a second host.
Both spawners talk to Docker via `docker-socket-proxy` (allow `containers`, `images`, `networks` POST only; no `exec`, no volumes on host paths). Node-RED per-user auth: Node-RED's `adminAuth` can be a function — point it at TB `/api/auth/login` so it's the same credential (consistent with decision 1).

**M3.3 Instructor console** ✅. Note: with TB-as-IdP, "reset student password" = call TB's password reset for that user; "suspend" = TB user `additionalInfo`/disable via REST + portal flag.

**M3.4 Rules & export** ✅. Export should hit TB's timeseries API with the *student's* JWT — scope-by-construction, no portal-side filtering needed.

#### Phase 4 ✅ as written. ChirpStack → TB integration goes through TB's MQTT integration or an HTTP integration; both are CE features. Fine to leave demand-driven.

### Part D — Working agreements ✅ Add:
7. **ADRs**: any decision with a rejected alternative gets `docs/adr/NNNN-*.md` before the milestone closes.
8. **One milestone = one PR** (or one tagged commit range) so the acceptance test is reviewable.
9. **Upstream-version bumps are their own PR** with the drill in M2.1 re-run.

---

## 2. Revised phased plan (my draft)

Changes from v1.0 are marked ▲. Session estimates assume ~2–3 h focused sessions.

### Phase 0 — Foundation (3–4 sessions)
- **M0.1 Scaffold** ▲ + `git init`, `docs/adr/0001`, `PLAN.md` pointer, `make check-profiles`.
- **M0.2 Core stack** ▲ `postgres:16` + `tb-node` (SQL timeseries, in-memory queue, unused transports off) + Caddy (xcaddy: layer4 + replace-response). ADR-0002 "tb-node + external Postgres", ADR-0003 "MQTTS via Caddy layer4".
- **M0.3 Bootstrap** ▲ `portal/scripts/tb_bootstrap.py` using a first-cut `tb_client`; creates tenant profile (rate limits), device profile, dev tenant, admin, customer, device; rotates sysadmin password. Manual `mosquitto_pub` verification on 1883 and 8883.
- **M0.4 Monitoring** ▲ (moved from M0.2) Prometheus, Grafana, exporters, Uptime Kuma; admin-only vhosts.
- *Accept as in v1.0 per milestone.*

### Phase 1 — Portal & provisioning (6–8 sessions)
- **M1.1 tb_client** ▲ + activation-link/activate, dashboard-from-template, tenant-profile CRUD, proactive refresh.
- **M1.2 Signup** ▲ TB-as-IdP flow; `provisioning_state` machine; password collected at verify step; ADR-0004 "TB is the identity provider".
- **M1.3 Student pages + docs skeleton** ▲ dashboard = template assigned per Customer; firmware snippets; mkdocs skeleton starts here. ADR-0005 "Customer-per-student, template dashboards".
- **M1.4 Quotas & platform tests** ▲ limits via tenant profile; isolation test on PR, flood test nightly with a latency assertion.
- 🏁 **Gate 1** unchanged.

### Phase 2 — Brand, VPS, launch (4–6 sessions)
- **M2.1 Rebrand overlay** ▲ overlay Dockerfile + Caddy rewrites; upgrade drill; ADR-0006 "overlay over source patches". Palette patch deferred to backlog.
- **M2.2 VPS** ▲ + socket-proxy, log rotation, unattended-upgrades.
- **M2.3 Backups** ▲ pg_dump + restic; drill.
- **M2.4 Docs** polishing + external tester.
- 🏁 **Gate 2** unchanged (v1.0.0, ≥ 2-week pilot).

### Phase 3 — Power features (6–10 sessions)
- **M3.0 Capacity ADR** ▲ (new, 0.5 session) — idle-culling design + concurrency assumption recorded before any spawner code.
- **M3.1 Node-RED** ▲ + idle culler, socket-proxy, adminAuth against TB.
- **M3.2 JupyterHub** ▲ authenticator against TB login (not portal DB), idle-culler.
- **M3.3 Instructor/admin**, **M3.4 Rules/export** as v1.0.
- 🏁 **Gate 3** unchanged.

### Phase 4 — unchanged.

---

## 3. Decisions I need from you before M0.1

1. ❓ **Name**: "CHERT IoT" (design-system-compliant) or "ChertIoT"?
2. ❓ **TB as identity provider** (portal holds no passwords) — agree?
3. ❓ **Customer-per-student with template dashboards** (students can't edit widgets in CE) — acceptable for the pilot?
4. ❓ **Rebrand = overlay + Caddy rewrite**, source patches only if pilot demands a palette change — agree?
5. ❓ **MQTTS via Caddy layer4** (custom Caddy build) vs. certs copied into TB — preference? (I recommend layer4.)
6. ❓ **Phase 3 capacity**: idle-culling with ≤ 8 concurrent sessions on 8 GB, or plan for 16 GB?
7. ❓ Are **minors** among the intended students (affects signup consent text and what we log)?

Everything else in §1 I'd apply as routine judgment calls unless you object.

---

## 4. Things the plan doesn't say that I'll assume

- Repo is new (`git init` in M0.1), separate from chertshub; ADR numbering starts at 0001 here.
- Single VPS, single TB node, no Kafka/Cassandra, ever, unless a load test proves otherwise (matches M4.2's "don't add unprompted").
- Python 3.12, `uv` for env/lockfile, `httpx` for the TB client, `respx` for recorded fixtures.
- TB version pinned to the latest CE release at M0.2 time and recorded in `.env.example` + ADR-0002.
- Portal UI = Jinja2 + HTMX + `chert-tokens.css`; no Node build.
