# CHERT IoT — project memory
## Hard rules
- Decisions D1–D12 in PLAN.md are final.
- Brand: "CHERT IoT" display / `chertiot` code+domain.
- Portal→TB: REST only via tb_client.py. Idempotent provisioning, always.
- No secrets in git; .env only; .env.example current. Never invent creds — ask.
- Tests green before a milestone is done. make lint test must pass at session end.
- Staging before production, every time.
- Pin every image/dependency. Versions are FROZEN — no upgrade plan (owner ruling 2026-09-04).
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
- Caddy = chertiot/caddy:<ver>-l4 everywhere (make caddy-image locally, images.yml in CI). Dockerfile sets GOFLAGS=-p=1 to bound build memory.
- Caddyfile is a single-file bind mount: `git pull` swaps its inode, so `caddy reload` alone re-reads the STALE pre-pull file. deploy.sh force-recreates the caddy container (re-binds the inode) before reloading. Adding a new vhost (e.g. `lora.{$DOMAIN}`) needs that recreate to take effect; Caddy fetches the cert on first hit.
- Local Colima VM is shared with other projects (katula, chertclub). Keep JVM heaps capped (TB_JAVA_OPTS, JAVA_OPTS_KC_HEAP) and give the VM ≥12 GiB.
- macOS doesn't resolve *.localhost outside browsers. Scripts use loopback ports from docker-compose.override.yml (dev only: TB 18080, Keycloak 18081, portal 18000 — 8080/8081/8000 are taken by other projects); e2e tests connect to 127.0.0.1:80 with the real Host header (tests/e2e/conftest.py).
- TB OAuth2 (4.3.x): POST /api/oauth2/client + POST /api/domain + PUT /api/domain/{id}/oauth2Clients. Basic mapper with tenantNameStrategy=EMAIL and no customer pattern → tenant per user, user is TENANT_ADMIN, tenant gets the *default* tenant profile (so D4 quotas go on the default profile). Login button appears only when the request Host matches a Domain record.
- Keycloak 26 sets Secure;SameSite=None on auth cookies even over http with sslRequired=none. Browsers accept that on *.localhost; Python's cookiejar doesn't — tests/e2e/conftest.py patches DefaultCookiePolicy.return_ok_secure for *.localhost.
- `make bootstrap` is the source of truth for the realm (portal/scripts/setup_keycloak.py) + TB OAuth2 (setup_tb_oauth2.py); keycloak/realm/chertiot-realm.json is an export artifact (secrets masked) for `--import-realm` disaster recovery.
- Rate limits live in TB **tenant profiles** (templates-tb/tenant-profile-student.json via provisioning.ensure_student_profile), not in compose env.
- TB API quirks captured in tb_client.py/provisioning.py: (a) POST /tenantProfile with default=true fails while another default exists → save, then POST /tenantProfile/{id}/default; (b) tenant profile validation requires the calculated-field limits (>0) even if unused; (c) DeviceCredentials.id is a bare {"id"} without entityType; (d) userCredentialsEnabled=false blocks password/refresh login only — not live JWTs, sysadmin impersonation (GET /user/{id}/token), or OAuth2 logins; re-enabling a never-activated user 400s ("should have password") → real suspend is Keycloak-side (M3.3); (e) GET /tenant/devices?deviceName= returns 404 when absent; textSearch on /tenants is substring → filter exact title.
- Provisioning runs tenant-scoped steps via sysadmin impersonation (needs TB default security.user_token_access_enabled=true). Never as sysadmin directly — sysadmin can't own dashboards/devices.
- Signup design (M1.1): portal creates the Keycloak user (unverified, VERIFY_EMAIL) via the `portal` client's service account (manage-users/view-users/query-users); Keycloak sends the verification mail; provisioning runs idempotently in /auth/callback on every verified login (repairs drift). Portal holds no passwords.
- Keycloak 26 verify-email UX: link opened outside the originating session → "Click here to proceed" interstitial → "Your account has been updated « Back to Application" (redirect_uri). The default user profile REQUIRES first/last name (forces an "Update Account Information" step) — setup_keycloak.ensure_user_profile makes them optional (D11).
- Portal image builds from the repo root (compose build.context=.) so /templates-tb ships inside it. Alembic runs on container start (docker-entrypoint.sh); alembic.ini has no logging section on purpose.
- Dev mail: Mailpit (docker-compose.override.yml) at http://127.0.0.1:18025; .env SMTP_HOST=mailpit, SMTP_STARTTLS=false. Prod SMTP creds are a prerequisite (ask).
- Tests force PORTAL_DATABASE_URL to a temp SQLite file (tests/conftest.py) — `make test` sources .env for TB/Keycloak creds only.
- Device 'last seen' = TB server attributes `active` / `lastActivityTime` (GET .../values/attributes/SERVER_SCOPE). Token rotation = POST /device/credentials with the existing credentials id and a new credentialsId.
- Firmware templates live in firmware-examples/ (shipped in the portal image at /firmware-examples, FIRMWARE_DIR); placeholders {{MQTT_HOST}} {{MQTT_PORT}} {{HTTP_URL}} {{ACCESS_TOKEN}} {{DEVICE_NAME}}; dev .env uses MQTT localhost:1883, prod 8883.
- paho-mqtt: always `disconnect()` before `loop_stop()`; a QoS1 publish TB never ACKs (e.g. a plain device publishing to v1/gateway/*) makes `loop_stop()` block forever. TB logs 'gatewaySessionHandler is null' and drops such messages silently.
- Flood test (tests-platform/test_flood.py, `make flood-test`): flooder in a separate process; TB throttles via tenant profile and closes the flooder's session repeatedly (MQTT_MSG_QUEUE_SIZE_PER_DEVICE_LIMIT=100, 'Closing current session because msq queue size'); control-device numbers are only meaningful on a quiet host — rerun on staging (M2.2) for the real criterion-4 numbers. The CI nightly sets FLOOD_STRICT_CONTROL=0 so the control-device health assertions (lost==0, p95<1.0) are a reported soft-check there — the flooder-throttling assertions stay hard everywhere; strict control runs on staging (default).
- thingsboard-brand/: patches apply to v4.3.1.4 (validated with git apply --check). The branded image and the layer4 Caddy image are built by CI (.github/workflows/images.yml → GHCR); one image per component in every environment, no dev-only variants. Logo assets are PNG-in-SVG derived from docs/branding (logo-master.svg is itself a raster). Palette patch keeps orange as accent/fill only (design-system rule).
- i18n: Jinja2 gettext via context processor (app/i18n.py); catalogs in portal/app/locales (make i18n-extract / i18n-compile; compiled in the image build). babel.cfg paths are relative to the extract input dir (`app`). Docs Arabic via mkdocs-static-i18n suffix structure (*.ar.md).
- Status page live: Uptime Kuma pinned to 1.23.17 (2.x socket.io API not supported by uptime-kuma-api); setup_status_page (uptime-kuma-api) creates admin from KUMA_PASSWORD, 6 monitors, published page. Kuma admin password reset needs its 1.x db; fresh-volume setup is the reliable path.
- LoRaWAN M4.1 DONE (staging+prod): ChirpStack needs pg_trgm+hstore extensions in its db or migrations apply 0 tables silently — created in deploy + init.sql. ChirpStack API is gRPC-only (chirpstack-api). Full path verified: register via ChirpStack → simulated uplink → student dashboard. paho-mqtt is a RUNTIME dep (lora-bridge).
- Flows (M3.1): portal is the spawner via docker-socket-proxy (containers/images/volumes/networks only, no exec). Per-user: 0.5 CPU / 256 MB / pids 256, own volume, `chertiot_flows` network (caddy+portal only), settings.js generated with httpAdminRoot=/u/<id>/. Editor gated by Caddy forward_auth → /flows/auth (session must own the path). Idle-stop 30 min; capacity assumption ≤8 concurrent instances per host.
- Scripts run as modules: `uv run python -m scripts.<name>` (portal/scripts is a package) so they can import `app`.
