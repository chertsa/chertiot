# CHERT IoT v2.0.0 — freeze record

**Deployed code tag:** `v2.0.0` → `f595d498c6422b0357e53e2023607c34bd138b25` (the exact code running in production).
**Evidence tag:** `v2.0.0-record` → the commit that contains this freeze record.
**Frozen:** 2026-10-07
**Owner approval:** "go" to publish staging to production, then "sync local and GitHub, commit all and freeze the version" (this session).
**Purpose:** immutable, restorable baseline of CHERT IoT v2 as launched on https://chertiot.com.

> **Tag ordering.** `v2.0.0` points at `f595d49`, the merge of PR #1 that production runs. This record
> was committed *after* that tag (docs only — the deployed runtime does not change), so it is not
> reachable from the code tag; the annotated evidence tag `v2.0.0-record` points at it. Neither the
> code tag nor production history is moved, deleted or force-updated.

---

## 1. What is frozen

- **Production** (`chertiotserver2`, 134.122.31.32, NYC1): `main` @ `f595d49` = `v2.0.0`, `VERSION` 2.0.0.
- **Staging** (`chertiotstagingserver2`, 161.35.119.46, NYC1): same code (checkout aligned to `v2.0.0`;
  it differs from the last staging deploy `95cea5d` only by the `VERSION` file).
- **Engines (pinned, frozen — no upgrade plan):** ThingsBoard CE 4.3.1.4 (branded `-b3`), Keycloak 26.7.2,
  PostgreSQL 16.15, Caddy 2.11.4 + layer4, Grafana 13.1.4 (branded), Prometheus v3.14.0, Alertmanager v0.34.0,
  Uptime Kuma 1.23.17, ChirpStack 4.19.1 + Gateway Bridge 4.1.2, Mosquitto 2.0.22, Redis 7.4.11,
  Node-RED 5.0.6 (branded), JupyterHub 5.5.1 / Notebook 7.6.2 (chertIoTlab), MkDocs Material 9.7.7.
- **Self-standalone:** every runtime image comes from `ghcr.io/chertsa` or is a CHERT build on the host;
  zero external registries at runtime (guarded by `test_no_external_registries.py`).

## 2. Snapshots (restore points)

| Snapshot | Droplet | Size | Taken | Kind |
|---|---|---|---|---|
| `chertiotserver2-prelaunch` | production | 45.76 GB | 2026-10-07, after launch | owner, **offline** |
| `chertiotstagingserver2-prelaunch` | staging | 47.97 GB | 2026-10-07, after launch | owner, **offline** |
| `chertiotserver2-pre-v2.0.0-20261007T0222Z` | production | 42.87 GB | 2026-10-07 02:22 UTC, before the v2 deploy | live (v1.1 state) |

The two **offline** owner snapshots are the frozen v2.0.0 baseline. The live pre-deploy snapshot is the
rollback to the previous (v1.1) production. The server also keeps `/srv/chertiot/.env.bak-pre-v2.0.0` (mode 600).

## 3. Running images (production, at freeze)

Mirrored images keep the upstream manifest digest (the mirror is a byte-identical copy).

| Service | Image | Digest |
|---|---|---|
| alertmanager | `ghcr.io/chertsa/chertiot-alertmanager:v0.34.0` | `sha256:690c7b525f4367aa91f73e2f91c632206d32e97c6384bdbf2fb7a861b420340d` |
| caddy | `ghcr.io/chertsa/chertiot-caddy:2.11.4-l4` | `sha256:f8e3567bd2fae6de409e6f134cb9f8d2700e9e17214e1769a70514b7c955ee33` |
| cadvisor | `ghcr.io/chertsa/chertiot-cadvisor:v0.55.1` | `sha256:3de2bd5203120b866d74a9b283b2ffb8ec382fbf9dc321814700c6ea6f44ec57` |
| chirpstack | `ghcr.io/chertsa/chertiot-chirpstack:4.19.1` | `sha256:9e0105f1dd733d3d3caa77aa7cfdbf817417fab8a093dd89639a2cd899ab9efe` |
| chirpstack-gateway-bridge | `ghcr.io/chertsa/chertiot-chirpstack-gw-bridge:4.1.2` | `sha256:cc820a195e739fa653c6d7fd403abe73b9b0c79b5dd4ab0f4bf9c6443470121b` |
| docs | `chertiot/docs:dev` (built from `v2.0.0` on the host) | image `sha256:989647180121…` |
| grafana | `chertiot/grafana-branded:dev` (built from `v2.0.0` on the host) | image `sha256:abed105ac313…` |
| jupyterhub | `chertiot/jupyterhub:dev` (built from `v2.0.0` on the host) | image `sha256:782839aaeaf0…` |
| keycloak | `ghcr.io/chertsa/chertiot-keycloak:26.7.2` | `sha256:9d1f1b2b7261ff53c66cb1092dfcdc34a5fb77e81f9e6a6e75b8b6a795de8067` |
| lora-bridge | `chertiot/portal:dev` (built from `v2.0.0` on the host) | image `sha256:75461ac32c0e…` |
| mosquitto | `ghcr.io/chertsa/chertiot-mosquitto:2.0.22` | `sha256:199ea8ef2e35ec2b1b37e59cfd1dbae538ed4dfa4a2251a121a52215a6248a21` |
| node-exporter | `ghcr.io/chertsa/chertiot-node-exporter:v1.12.1` | `sha256:1b4e4438faca4dd7e001dd445d161a4a2091b0fededa84093b3a8dfeae1f1be0` |
| portal | `chertiot/portal:dev` (built from `v2.0.0` on the host) | image `sha256:75461ac32c0e…` |
| postgres | `ghcr.io/chertsa/chertiot-postgres:16.15` | `sha256:1a6ab3f5345eb6dbe04a1349529caabdb0ab09293a09590fad07b2246bfa4b54` |
| postgres-exporter | `ghcr.io/chertsa/chertiot-postgres-exporter:v0.20.1` | `sha256:ac5ec343104fae0e2d84a27bb8d69b38430a11910c5382cad85d478d2bab713e` |
| prometheus | `ghcr.io/chertsa/chertiot-prometheus:v3.14.0` | `sha256:5ce7540c3c00ef4ab0c9d2c995c6a5b9c421f44b4a115d97a2c7af3b1c21cbb0` |
| redis | `ghcr.io/chertsa/chertiot-redis:7.4.11` | `sha256:c6eabf748fc7a61dbb5a705c78bcf3d6377b1127a97d0ce965c11c44ba46896f` |
| socket-proxy | `ghcr.io/chertsa/chertiot-socket-proxy:v0.5.0` | `sha256:1f5038b54f06c3e18422902cf00ba21803d1c97805aae032e5e6673d532d3459` |
| tb | `ghcr.io/chertsa/chertiot-tb:4.3.1.4-b3` | `sha256:c9462d2e528f8e62c5e7584629f8a2baefe2df1251f00205465db1ea494fd216` |
| uptime-kuma | `ghcr.io/chertsa/chertiot-uptime-kuma:1.23.17` | `sha256:3d632903e6af34139a37f18055c4f1bfd9b7205ae1138f1e5e8940ddc1d176f9` |

## 4. Health and verification at freeze

- Production: 20 containers, 0 unhealthy; staging: 21 containers (incl. one per-user Node-RED), 0 unhealthy.
- CI on PR #1: lint + unit tests (144) and full-stack e2e — green.
- Verified on https://chertiot.com (headless Chrome): marketing site, sign-up, Keycloak sign-in /
  reset (themed, CHERT favicon), home, all 11 project pages, teaching, explore, docs — English and
  Arabic, desktop and phone — HTTP 200, no console errors, no external requests, no horizontal overflow.
- End-to-end IoT path: project provisioned (own ThingsBoard tenant), device created, 3 readings over
  **MQTTS to chertiot.com:8883 from an external host** (CONNACK 0 / PUBACK 0) → device Online, telemetry visible.

## 5. Non-secret configuration at freeze (production)

`ENV=prod`, `DOMAIN=chertiot.com`, `LORA_ENABLED=true`, `LAB_ENABLED=true`, `LAB_NAMED_SERVER_LIMIT=10`,
`MONITORING_ENABLED=true`, `MONITORING_CACHE_TTL=15`, `TELEMETRY_ENABLED=true`. The demo simulator
(`demo` profile) is retired on production. Note: `.env.example` defaults for the three feature flags are
`false`; `deploy.sh` only appends missing keys and never changes existing values.

## 6. Known limitations / accepted at freeze

- `monitor.chertiot.com` rename of the platform monitor awaits a DNS record (Grafana stays on `grafana.`).
- Docs text still describes the pre-project "My devices / My dashboard" flow (design is current).
- Test project **"Launch verification"** (UAT instructor) remains on production for the owner to review/delete.
- Owner UAT walkthroughs (`docs/owner_uat/`) stay local-only by design (public repo; on-screen emails/tokens).

## 7. Rollback

1. **Whole host:** restore `chertiotserver2-prelaunch` (frozen v2.0.0) or
   `chertiotserver2-pre-v2.0.0-20261007T0222Z` (previous v1.1 production) from the DigitalOcean console.
2. **Code only:** `git checkout v2.0.0` on the host, then `deploy/scripts/deploy.sh 134.122.31.32 chertiot.com`
   (rebuilds CHERT images from the tag; mirrored images pin by the digests above).

## 8. Freeze policy

- `main` and the `v2.0.0` tag are frozen. No change reaches production without explicit owner approval.
- Any future change: new branch → staging (`stage.chertiot.com`) → owner UAT → PR to `main` → new tag
  (`v2.0.x` for fixes, `v2.1.0` for features) → production.
- Engine versions remain frozen (owner ruling 2026-09-04): no upgrades.
