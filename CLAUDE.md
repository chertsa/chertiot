# CHERT IoT — project memory
Read PLAN.md. Current: Phase 0 / M0.3. Last done: M0.2 (core stack, stock images, all healthy + Prometheus scraping).
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
- Rate limits live in TB **tenant profiles** (set via REST in M0.4), not in compose env.
