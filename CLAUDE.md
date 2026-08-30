# CHERT IoT — project memory
Read PLAN.md. Current: Phase 0 / M0.4. Last done: M0.3 (Keycloak realm + TB OAuth2; e2e proves Keycloak login → own TB tenant as TENANT_ADMIN).
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
## Environment
- Python via `uv` (portal/pyproject.toml + uv.lock). Python 3.12 pinned in portal/.python-version.
- Local dev: `make dev` (compose `core` profile). Needs `.env` (copy .env.example).
- Design tokens & logos: docs/branding/ (tokens/*.json, chert-tokens per CHERT-Design-System.md). Never hardcode a hex.
## Pins (M0.2, 2026-08-30) — see .env.example
ThingsBoard CE 4.3.1.4 (thingsboard/tb-node, monolith) · Keycloak 26.7.2 · Postgres 16.15 · Caddy 2.11.4 + caddy-l4@42db5690dea1.
## Gotchas
- `thingsboard/tb-postgres` embeds its own Postgres; we use `tb-node` + external Postgres (TB_SERVICE_TYPE=monolith, TB_QUEUE_TYPE=in-memory, DATABASE_TS_TYPE=sql). Config: deploy/tb/tb-node.env.
- TB schema install is a separate run with INSTALL_TB=true (same image). `tb-install` service does this once, marker in volume `tb-install-state`. Upgrades use UPGRADE_TB=true + FROM_VERSION (deliberate milestone).
- tb-node image has no curl/wget: healthchecks use bash /dev/tcp. Keycloak image likewise. Tomcat answers `HTTP/1.1 200 ` with no reason phrase — don't grep for `200 OK`.
- tb-install runs as root (user 0:0) only so it can write its marker into the root-owned volume; TB itself runs as uid 799.
- Keycloak 26: `start --optimized` fails on first ever start (no build). We use plain `start`; optimized image is in BACKLOG.
- TB's own conf sets a GC; adding -XX:+UseSerialGC in JAVA_OPTS → "Multiple garbage collectors selected".
- Compose `--env-file .env.example` is used by `make check-profiles`; services must not reference `.env` via `env_file` (would break the check). Pass vars explicitly.
- Caddy+layer4 (xcaddy Go build) needs ~4 GB RAM; it was OOM-killed in a shared Colima VM. Dev runs stock `caddy` (CADDY_IMAGE in .env); staging/prod use `make caddy-image` → chertiot/caddy:<ver>-l4. Dockerfile sets GOFLAGS=-p=1.
- Local Colima VM is shared with other projects (katula, chertclub). Keep JVM heaps capped (TB_JAVA_OPTS, JAVA_OPTS_KC_HEAP) and give the VM ≥12 GiB.
- macOS doesn't resolve *.localhost outside browsers. Scripts use loopback ports from docker-compose.override.yml (dev only: TB 18080, Keycloak 18081, portal 18000 — 8080/8081/8000 are taken by other projects); e2e tests connect to 127.0.0.1:80 with the real Host header (tests/e2e/conftest.py).
- TB OAuth2 (4.3.x): POST /api/oauth2/client + POST /api/domain + PUT /api/domain/{id}/oauth2Clients. Basic mapper with tenantNameStrategy=EMAIL and no customer pattern → tenant per user, user is TENANT_ADMIN, tenant gets the *default* tenant profile (so D4 quotas go on the default profile). Login button appears only when the request Host matches a Domain record.
- Keycloak 26 sets Secure;SameSite=None on auth cookies even over http with sslRequired=none. Browsers accept that on *.localhost; Python's cookiejar doesn't — tests/e2e/conftest.py patches DefaultCookiePolicy.return_ok_secure for *.localhost.
- `make bootstrap` is the source of truth for the realm (portal/scripts/setup_keycloak.py) + TB OAuth2 (setup_tb_oauth2.py); keycloak/realm/chertiot-realm.json is an export artifact (secrets masked) for `--import-realm` disaster recovery.
- Rate limits live in TB **tenant profiles** (set via REST in M0.4), not in compose env.
