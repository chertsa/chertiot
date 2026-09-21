# CHERT IoT v1 — As-Is Final freeze record

**Deployed code tag:** `chertiot-v1-as-is-final` → `9a025791d33b5c61878097b82a38fe8efb2460aa` (the exact code running in production).
**Evidence tag:** `chertiot-v1-as-is-final-record` → the commit that contains this (corrected) freeze record.
**Frozen production commit:** `9a025791d33b5c61878097b82a38fe8efb2460aa`
**Frozen:** 2026-09-21
**Owner approval:** granted this session (promote verified Chart.js compliance change to production; then freeze v1).
**Purpose:** immutable, independently restorable baseline of production CHERT IoT v1 after the pre-freeze zero-external-runtime (Chart.js vendoring) compliance change. v2 is not started.

> **Note on tag ordering.** The deployed **code** tag `chertiot-v1-as-is-final` points at
> `9a02579`, the exact commit deployed to production. **This evidence document was committed
> *after* that tag** (a docs-only commit that does not change the deployed runtime), so it is not
> reachable from the code tag. A separate annotated **evidence** tag,
> `chertiot-v1-as-is-final-record`, points at the freeze-record commit. Neither the code tag nor
> production history was moved, deleted, or force-updated.

---

## 1. What is frozen

Production CHERT IoT v1 as running on the production host, portal-only change applied
(local Chart.js; no external runtime assets), all other engines unchanged.

- Production commit: `9a025791d33b5c61878097b82a38fe8efb2460aa` (`main` HEAD at freeze).
- Compliance state: **zero external runtime assets** in the portal UI — Chart.js served locally
  from `/static/vendor/chartjs/4.4.1/chart.umd.min.js`; **no cdnjs**; portal-wide external-runtime
  guard test in place.

## 2. Running images (production)

Terminology: **local image ID** = the image identifier on the host (`docker inspect <container>
.Image`). **Registry manifest digest** = obtained independently from the registry (`docker buildx
imagetools inspect <ref>`). The **portal** image is **built on the host and never pushed to a
registry, so no registry manifest digest exists** for it — only a local image ID. (This host uses a
containerd image store, so for registry-pulled images the local `.Image` value coincides with the
manifest digest; they are still labelled by their true kind below.)

| Service | Image ref | Local image ID | Registry manifest digest (independent) |
|---|---|---|---|
| portal | `chertiot/portal:dev` (built on host) | `sha256:8453abe4cc3494612dad47f48d7618d44848cce436f91b68a56c670497601455` | — none (not pushed) |
| thingsboard | `ghcr.io/chertsa/chertiot-tb:4.3.1.4-b3` | `sha256:c9462d2e528f8e62c5e7584629f8a2baefe2df1251f00205465db1ea494fd216` | `sha256:c9462d2e528f8e62c5e7584629f8a2baefe2df1251f00205465db1ea494fd216` |
| keycloak | `quay.io/keycloak/keycloak:26.7.2` | `sha256:9d1f1b2b7261ff53c66cb1092dfcdc34a5fb77e81f9e6a6e75b8b6a795de8067` | `sha256:9d1f1b2b7261ff53c66cb1092dfcdc34a5fb77e81f9e6a6e75b8b6a795de8067` |
| postgres | `postgres:16.15` | `sha256:f1c3376c26f2609ab9f29f71f824103fe2fcd8ee0346485cb6122a4f93df6f94` | `sha256:a3b7f434b2dc57ce85a67e171163eb8ab1a1ebcb39d27484661f26b1dfbe30d6` |
| grafana | `ghcr.io/chertsa/chertiot-grafana:13.1.4-b1` | `sha256:32687c0c187092dfc0c1a1512f0dd3456bddd500fc0d8d539d3d906dd7cd22c9` | `sha256:32687c0c187092dfc0c1a1512f0dd3456bddd500fc0d8d539d3d906dd7cd22c9` |
| caddy | `ghcr.io/chertsa/chertiot-caddy:2.11.4-l4` | `sha256:6b34fe38ebb7827daf7d0575152a9a43624e885f3bca7aae4ba5a48ecbb9af3b` | `sha256:f8e3567bd2fae6de409e6f134cb9f8d2700e9e17214e1769a70514b7c955ee33` |

Node-RED runs as per-project on-demand containers (`ghcr.io/chertsa/chertiot-nodered:5.0.6-b1`), not a
core compose service; ChirpStack/Jupyter per the `lora`/lab profiles.

The **rollback portal image ID** `sha256:6968405f9c464e9eab8a9833c90061149bfb6ddf2929aae3df635bb28552f6ab`
(§6) is likewise a local image ID (previous host build, not pushed → no registry digest).

Vendored Chart.js provenance: Chart.js 4.4.1 UMD (npm `chart.js@4.4.1` `dist/chart.umd.js`),
SHA-256 `74401d738dd3e03ee5dfb3b6841210fe2c4ead8a960c4011ca4ba0b78a9fd8f3`, MIT.

## 3. Health at freeze

- Portal: `Up (healthy)`, `/healthz` 200.
- Database: PostgreSQL accepting connections; portal projects = 3 (unchanged from pre-deploy).
- Public smoke: `chertiot.com/healthz` 200, `app.chertiot.com/login` 200,
  `auth.chertiot.com/realms/chertiot` 200.

## 4. As-Is production verification (sanitized)

Authenticated (SSO) browser verification on `chertiot.com`, online and with all non-CHERT public
origins blocked by request interception. Screenshots: `v1-as-is/prod-project-chart.png`,
`v1-as-is/prod-report-chart.png`.

- Project chart and Project Report chart render — Chart.js `4.4.1`, initialized, 2 datasets, 96 real
  data points each (temporary verification project, since removed).
- `window.Chart.version == "4.4.1"`; Chart.js loaded from `/static/vendor/chartjs/4.4.1/chart.umd.min.js`.
- Served asset HTTP 200, SHA-256 `74401d738dd3e03ee5dfb3b6841210fe2c4ead8a960c4011ca4ba0b78a9fd8f3`.
- **No request to cdnjs; no unapproved external runtime request** (request hosts limited to
  `chertiot.com` + `auth.chertiot.com`; offline `blocked_hosts` empty — no external attempt made).
- No chart-page JavaScript errors. SSO, `/home`, project navigation and device pages functional.

## 5. Known limitations / accepted at freeze

- Keycloak login page logs a benign CSS MIME-type console warning on `auth.chertiot.com` (login
  theme resource); not on the chart pages, unrelated to the portal or Chart.js.
- CI annotations note Node.js 20 action deprecation (cosmetic).

## 6. Rollback (EMERGENCY OPERATIONAL ONLY — NOT compliant)

Restoring the previous portal restores the **CDN-dependent** (cdnjs) Chart.js version. This is an
emergency operational rollback only and is **not** zero-external-runtime compliant.

- Previous production commit: `c611cde836712091f7682c12d42c1c796b9258ef`
- Previous portal image ID: `sha256:6968405f9c464e9eab8a9833c90061149bfb6ddf2929aae3df635bb28552f6ab`

Commands (on the production host, `/srv/chertiot`):

```bash
# Fast image restore (no rebuild):
docker tag sha256:6968405f9c464e9eab8a9833c90061149bfb6ddf2929aae3df635bb28552f6ab chertiot/portal:dev
docker compose -f docker-compose.yml up -d --no-deps --force-recreate portal

# Or commit restore (rebuild):
git reset --hard c611cde836712091f7682c12d42c1c796b9258ef
docker compose -f docker-compose.yml --profile core up -d --build portal
```

No database migration or data mutation was performed by the deployment; rollback needs no data
restore. Do not modify data on rollback.

## 7. Restoration reference (to the frozen baseline)

To restore the frozen v1 baseline: check out `chertiot-v1-as-is-final`
(`9a025791d33b5c61878097b82a38fe8efb2460aa`), redeploy the portal (rebuild on host or the recorded
portal image ID above), and confirm the running image digests in §2. Other engines are pinned by
digest and unchanged.

## 8. Scope note

v2 is not started. No `release/chertiot-v2-unified` branch exists. This freeze is the rollback
baseline for any future v2 work.
