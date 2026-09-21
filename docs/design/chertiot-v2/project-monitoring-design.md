# Design — Project Monitoring (`/projects/{project_id}/monitoring`)

**Status:** DESIGN ONLY — for owner review. No code, branches, tags, snapshots, config, or deploys result from this document.
**Author:** Claude (engineering). **Related:** `engineering-review.md`.

> Sanitization note: no staging tenant UUIDs, demo emails, private project slugs, credentials, tokens, internal account details, machine-specific paths, or `vscode-webview://` links appear here. Placeholders are used where an example is needed. Source references are repo-relative.

**Position in the plan:** Project Monitoring is the **first work package** under the complete unified-v2 master plan — **not a replacement** for that plan.

**Anchored final decisions:** Project = TB Tenant (no customer model); portal-native monitoring over ThingsBoard REST; Grafana = platform-infrastructure monitoring for platform admins only; default range 24h; user-facing reference = **slug/reference only, never any part of `tb_tenant_id`**; **Chart.js vendored locally, no CDN**; alarm policy per §7; no "authorized member" permission until a persisted permission model exists; **initial scope = actual active `ProjectMember`s only** (instructor/admin tenant-session access is an unresolved follow-up).

---

## 1. Summary

A first-class **Monitoring** tab per project rendering **only data ThingsBoard CE genuinely provides per tenant**, through the **existing** `require_membership` + `as_project()` impersonation boundary and the **existing** `dashboard_data()` / `alarm_history()` data layer, extended with an explicit device+telemetry-key selector, a time-range selector, a ThingsBoard-connectivity + Node-RED services strip, typed response models, and a locally-vendored Chart.js under a strict CSP. Platform infrastructure metrics stay in **admin-only Grafana**, unchanged. No new datasource, no Grafana multi-tenancy, no schema change.

---

## 2. Metrics genuinely available from ThingsBoard CE (evidence-based)

Proven working today in `portal/app/dashboard.py`, all tenant-scoped through the impersonated session. **ThingsBoard REST call paths below omit `/api`** because `TbClient` already targets it: `httpx.Client(base_url=f"{self.base_url}/api", …)` (`tb_client.py:142`); e.g. `session._post("/entitiesQuery/find", …)` → effective `…/api/entitiesQuery/find`.

| Metric | `TbClient` call (effective HTTP path) | Card/Chart |
|---|---|---|
| Device count (total) | `_post("/entitiesQuery/find")` → `/api/entitiesQuery/find`, `totalElements` | KPI |
| Online / offline | Entity Data Query `latestValues` ATTRIBUTE `active` + `lastActivityTime` | KPI + roster |
| Per-device last reading & last-seen | Entity Data Query latest ATTRIBUTE/TIME_SERIES | Roster |
| Active alarms + list | `_get("/alarms", searchStatus="ACTIVE", …)` → `/api/alarms` | KPI + list |
| Alarm history | `_get("/alarms", sortProperty="createdTime", sortOrder="DESC")` | History table |
| Available telemetry keys (per device) | `_get(f"/plugins/telemetry/DEVICE/{id}/keys/timeseries")` → `/api/plugins/telemetry/DEVICE/{id}/keys/timeseries` | Key selector (new) |
| Time-series (agg over range) | `_get(f"/plugins/telemetry/DEVICE/{id}/values/timeseries", agg="AVG", interval=…)` | Trend chart |
| Device quota | tenant profile via existing `_max_devices(sysadmin, tenant_id)` | KPI (used/quota) |
| Alarm ack | `_post(f"/alarm/{alarm_id}/ack")` → `/api/alarm/{id}/ack` (CE-supported) | Ack action |

### 2.1 Explicitly excluded (no fabrication)

- **Per-project message throughput / msgs-per-sec / success-fail rates:** `transport_total` is **platform-wide** (Prometheus), not per-tenant. A per-tenant figure *might* be derivable from `GET /api/usage`, but this is **unverified** — excluded from v1 and listed as a later spike (§18). No throughput card ships with platform-wide or invented numbers.
- **Host CPU/RAM, container network I/O, PostgreSQL connections, global rate:** remain in **platform Grafana, admin-only**, untouched.

---

## 3. Routes & files

### 3.1 Routes (new)

| Method | Path | Purpose | Response |
|---|---|---|---|
| `GET` | `/projects/{project_id}/monitoring` | Page shell + first snapshot | HTML |
| `GET` | `/projects/{project_id}/monitoring/data?range=&device=&key=` | Snapshot for polling/refresh | JSON `MonitoringSnapshot` |
| `POST` | `/projects/{project_id}/monitoring/alarms/{alarm_id}/ack` | Acknowledge one active alarm (CSRF-protected) | 303 / JSON |

Query params are validated (§6): `range ∈ {1h,6h,24h,7d}` (default **24h**); `device` must be a device id present in the tenant's device list; `key` must be a **numeric** timeseries key discovered for that device. Invalid values → 400 (or ignored to default), never trusted.

### 3.2 Files expected to change (implementation preview — not done now)

**New**
- `portal/app/routers/monitoring.py` — 3 routes; membership gate; feature-flag guard; rate-limit; CSRF on ack; audit.
- `portal/app/monitoring.py` — data layer (`snapshot(...)`, device/key discovery, services health), Pydantic models, bounded TTL cache.
- `portal/app/templates/monitoring.html` — page (no inline executable script; see §11).
- `portal/app/static/js/monitoring.js` — chart init + polling (served from `/static/`).
- `portal/app/static/vendor/chartjs/4.4.1/chart.umd.min.js` — **vendored Chart.js** (see §10).
- `portal/app/static/vendor/chartjs/4.4.1/SOURCE.txt` — upstream release source/URL of the pinned artifact.
- `portal/app/static/vendor/chartjs/4.4.1/LICENSE.md`, `.../CHECKSUM.txt` — license + SHA-256.
- `portal/tests/unit/test_monitoring.py` — positive tests + the negative cross-project isolation matrix (§20).
- `portal/tests/unit/test_no_external_assets.py` — static external-asset guard over `templates/` + `static/` (§10.4).

**Edited**
- `portal/app/main.py` — include monitoring router; add **security-headers/CSP middleware** (§10).
- `portal/app/config.py` — `monitoring_enabled: bool = False`; `monitoring_cache_ttl: int = 15`.
- `.env.example` — `MONITORING_ENABLED=`, `MONITORING_CACHE_TTL=`.
- `portal/app/templates/project.html` — Monitoring capability card + project sub-nav; **remove the Chart.js CDN `<script>` and use the vendored asset** (report page likewise).
- `portal/app/templates/project_report.html` — swap Chart.js CDN → vendored asset.
- `portal/app/templates/_project_nav.html` (new partial) — shared project sub-nav.
- `portal/app/locales/ar/LC_MESSAGES/messages.po` + `.mo` — Arabic labels (hand-added + `pybabel compile`; **no full extract** — the catalog is stale and fuzzy-injects wrong strings).

**No schema change.**

### 3.3 Reused unchanged

`require_membership`, `as_project`, `dashboard_data`, `alarm_history`, `TbClient.timeseries/latest_timeseries/server_attributes/list_devices`, `rate_limited`, `audit`, `templates`, `app.i18n`, `base.html`, `flows.ready`.

---

## 4. Device & telemetry-key selection (no arbitrary "first device")

1. **Device list** from the Entity Data Query (id + name), tenant-scoped. Empty → "no devices" state.
2. **Selected device** = validated `device` query param **if present in the tenant device list**, else the first alphabetical device as a *default landing* (not silently charted from an arbitrary device — the selector shows which device is active and the URL reflects it).
3. **Key discovery:** `_get(f"/plugins/telemetry/DEVICE/{id}/keys/timeseries")` returns the device's timeseries keys. Determine **numeric** keys by fetching latest values (`latest_timeseries`) and keeping those whose value parses as a float. Only numeric keys populate the key selector and charts.
4. **Preferred suggestions:** `temperature`, `humidity` are highlighted **only when actually present** in the numeric key set; never assumed.
5. **Selection persistence:** `device`, `key`, `range` are preserved via **validated URL query parameters** (device ∈ tenant list; key ∈ discovered numeric keys; range ∈ allow-list). Invalid values are rejected/ignored, never trusted.
6. **Empty states:** (a) no devices; (b) device has no telemetry keys; (c) device has telemetry but **no numeric** keys (chart hidden, roster still shown).

---

## 5. Polling & time-range

- **Range → params** (server-side; client sends only the allow-listed token):

  | range | startTs | interval | agg |
  |---|---|---|---|
  | 1h | now−1h | 60 s | AVG |
  | 6h | now−6h | 5 min | AVG |
  | 24h (default) | now−24h | 30 min | AVG |
  | 7d | now−7d | 3 h | AVG |

- Initial snapshot server-rendered; client polls `…/monitoring/data` every **30 s**, paused when the tab is hidden.
- Per-refresh call budget: 1 Entity Data Query + 2 alarm calls + 1 chart call (+ key discovery only on device change). Node-RED readiness is a **separate** call (§12).

---

## 6. Membership + impersonation sequence (server-side)

```
GET /projects/{project_id}/monitoring[/data]
 └─ require_membership(request, db, project_id)   # 403 unless an ACTIVE ProjectMember
 └─ feature flag check                            # 404 if monitoring_enabled is false
 └─ validate query params (range/device/key allow-lists)
 └─ [cache lookup ONLY AFTER authorization]       # see §14
 └─ with as_project(member) as (sysadmin, session):
        snapshot = monitoring.snapshot(sysadmin, session, range, device, key)  # tenant-bounded
 └─ audit(db, user.email, "monitoring.view", project.slug)   # once per page load, not per poll
 └─ render / return
```

- **Initial scope = active `ProjectMember`s only.** Instructor/admin access is **not** implemented in this package (unresolved follow-up, §17). No claim is made that instructors/admins pass through `require_membership`/`as_project`.
- No client-supplied tenant/device/alarm id is trusted; all are resolved through the impersonated session (TB returns 404/403 for out-of-tenant ids → surfaced as 404).

---

## 7. Role & alarm-acknowledgement policy (final)

Initial implementation (active ProjectMembers only):

| Action | active member | owner (a member, role=owner) | instructor | platform admin |
|---|---|---|---|---|
| View project Monitoring | ✅ | ✅ | follow-up (read-only, not in v1) | break-glass, audited (not in v1) |
| Acknowledge **ordinary** alarm | ✅ | ✅ | ❌ (read-only) | via break-glass only |
| Acknowledge **critical** alarm | ❌ | ✅ | ❌ | via break-glass only |
| Send device command | ❌ | (separate capability) | ❌ | via break-glass only |
| Platform Grafana (infra) | ❌ | ❌ | ❌ | ✅ (only) |

- **No "authorized member"** intermediate permission is introduced until a **persisted permission model** exists.
- **Instructor = read-only** (target policy); **not part of the first implementation** since instructor tenant-session resolution is unproven (§17).
- **Platform administrator** access to a project tenant requires an **explicit, audited break-glass design** (separate follow-up); it is not a silent passthrough.

---

## 8. User-facing reference

The project header and every response model use **only the project slug / portal reference**. **No part of `tb_tenant_id` is ever displayed or serialized** to the browser.

---

## 9. Response model (`MonitoringSnapshot`, Pydantic)

```python
class DeviceRow(BaseModel):
    name: str; label: str; active: bool; last_seen: str | None; reading: str

class AlarmRow(BaseModel):
    id: str | None; type: str | None; severity: str; status: str; device: str; time: str

class SeriesPoint(BaseModel):
    t: str; v: float

class ServiceHealth(BaseModel):
    thingsboard_connectivity: Literal["ok","degraded","unknown"]   # API reachability, NOT ingestion
    node_red: Literal["ok","stopped","unknown"]

class MonitoringSnapshot(BaseModel):
    generated_at: str; range: str
    selected_device: str | None; selected_key: str | None
    available_devices: list[dict]        # [{id, name}]
    numeric_keys: list[str]
    device_count: int; online_count: int; offline_count: int
    max_devices: int | None
    alarm_active_count: int
    devices: list[DeviceRow]
    active_alarms: list[AlarmRow]; alarm_history: list[AlarmRow]
    series: dict[str, list[SeriesPoint]]
    services: ServiceHealth
    stale: bool; degraded: list[str]
```

No `tb_tenant_id`, TB JWTs/tokens, user ids, or raw stack traces are ever serialized.

---

## 10. Zero external runtime assets — Chart.js vendoring + CSP (mandatory)

**Principle (target end-state):** *CHERT production UI has zero external runtime asset dependencies. All browser-delivered assets are version-pinned, stored in the repository or approved CHERT artifact storage, included in the deployed image, and served from CHERT-controlled origins.*

**Status of this section — approved requirements, NOT completed work.** As of this design:
- Chart.js has **not** yet been vendored.
- The existing CDN references have **not** been removed.
- The CSP has **not** been deployed.
- The external-asset test has **not** been implemented.

**⚠ Current-state warning:** *Current v1 still loads Chart.js from cdnjs in two templates. Therefore zero-external-runtime compliance is not yet achieved. This must be remediated and verified on staging before the final compliant v1 freeze, or explicitly recorded as a freeze blocker.*

### 10.1 Chart.js vendoring (to be implemented)

- **Version:** Chart.js **4.4.1** (UMD build `chart.umd.min.js`) — the approved initial local version, because it matches the version currently referenced in the templates. Its upstream source, license and SHA-256 must still be verified during implementation.
- **Upstream source:** the official Chart.js 4.4.1 release artifact (recorded in `vendor/chartjs/4.4.1/SOURCE.txt`).
- **License:** MIT (`vendor/chartjs/4.4.1/LICENSE.md`, committed).
- **Integrity:** SHA-256 of the committed file recorded in `vendor/chartjs/4.4.1/CHECKSUM.txt`; an update procedure re-verifies the checksum before replacing the file.
- **Serving:** exclusively from the portal's own `/static/vendor/chartjs/4.4.1/chart.umd.min.js`. No CDN, no alternative public CDN.
- **Build/update process:** the file lives in the repo and ships in the normal portal image build (already copied via the static dir); updating = download the pinned release, verify checksum, replace, bump the path, update `CHECKSUM.txt`, re-run tests.
- **Offline requirement:** once implemented, Monitoring (and the report page, once migrated) **must render fully with outbound internet disabled**.
- **CSP implication:** because Chart.js is same-origin, `script-src 'self'` suffices; no CDN host is allowed.

### 10.2 Remove existing CDN usage (reported; to be remediated, not silent)

The two existing external references — `templates/project.html` and `templates/project_report.html` (Chart.js via cdnjs) — are **reported** in `engineering-review.md §6`. They are **currently still present** and are **to be replaced** with the vendored asset as part of this work package. No other behavior will be changed silently.

### 10.3 Content Security Policy (to be added via middleware in `main.py`)

No CSP middleware exists today. The following CSP **will be added** portal-wide (introduced together with vendoring so no page breaks):

```
default-src 'self';
script-src 'self';
style-src 'self' 'unsafe-inline';   # interim minimum: templates currently use inline style attributes
font-src 'self';
img-src 'self' data:;
connect-src 'self';
object-src 'none';
base-uri 'self';
frame-ancestors 'self';
```

- `script-src 'self'` (no `'unsafe-inline'`): the monitoring page carries **no inline executable script** — chart init/polling live in `/static/js/monitoring.js`; the initial snapshot is passed via a non-executing `<script type="application/json">` block read by that file.
- `style-src` keeps `'unsafe-inline'` as the **documented minimum** because existing templates use inline `style="…"` attributes; a follow-up removes inline styles to drop the exception (tracked, not required for this package).
- No external hosts appear in any directive.

### 10.4 Automated external-asset test (approved requirement — not yet implemented)

`test_no_external_assets.py` (to be added) **statically inspects every relevant file** under `portal/app/templates/` and `portal/app/static/` and **fails** if it finds an external runtime destination in any of:

- script `src`;
- stylesheet `href` (`<link rel="stylesheet">`);
- image/media `src` and `srcset`;
- iframe / embed / object sources;
- CSS `@import`;
- CSS `url(...)`;
- JavaScript static and dynamic `import(...)`;
- `Worker` and `SharedWorker` constructors;
- service-worker registration (`navigator.serviceWorker.register`);
- `WebSocket`;
- `EventSource`;
- `fetch` / `XMLHttpRequest`;
- web app manifests (`<link rel="manifest">` and the manifest's own asset URLs).

A destination is **external** when it resolves to any origin other than the portal's own (i.e. anything not `/static/…`, relative, or same-origin). Only **explicitly approved CHERT-controlled top-level navigation** — the `grafana.`, `status.`, and `lab.` anchor links — may be **allow-listed by exact host**. The test does **not** exempt all anchors, and does **not** exempt all HTTPS URLs; anything outside the exact allow-list fails the test. It inspects file contents statically (not only rendered HTML), so a new external reference in any template or static asset is caught.

### 10.5 Portal-wide external-dependency audit (reported before change)

| Category | Finding |
|---|---|
| Public CDNs | Chart.js via cdnjs (2 templates) — **to vendor** |
| Google Fonts | none (fonts local under `/static/fonts`) |
| Externally hosted icons/images | none |
| Third-party JavaScript | none (besides the Chart.js CDN above) |
| Remote CSS imports | none |
| Browser calls to TB/Grafana/engines bypassing the portal | none (browser fetches are same-origin; TB/Grafana handoffs are top-level navigations/redirects, not background asset loads) |
| Nav links to grafana./status./lab. subdomains | CHERT-controlled first-party origins (navigation) — allowed |

Any browser request to a non-CHERT-controlled origin is treated as a **release blocker** unless the owner explicitly approves that integration.

---

## 11. Cards, charts & states

**KPI cards:** Devices (count / quota) · Online (online/total) · Active alarms (0 green / ≥1 amber / any critical red) · Services (ThingsBoard connectivity + Node-RED chips).
**Chart:** telemetry trend (Chart.js line) for the selected **numeric** key over the range; hidden if none.
**Tables:** device roster; active alarms (with role-gated Ack); alarm history.

**States:** loading (skeleton) · empty (no devices / no telemetry / no numeric keys, each distinct) · stale (cache past TTL and last TB call failed — show last values + banner) · permission-denied (403, no data) · engine-unavailable (`as_project` 409 / TB error — retry; rest of shell usable) · partial degradation (`degraded[]` per-section). Status is conveyed by **icon + label**, never color alone. No secrets/tokens/endpoints/stack traces in any state.

---

## 12. Node-RED readiness (separate from the ThingsBoard snapshot)

- **Call path:** reuse `flows.ready(project_id)` — checks container `status()` via the Docker socket-proxy, then probes `http://<container>:1880/u/{project_id}/` with a **2.0 s timeout**, returns bool, swallows all errors.
- **Isolation:** invoked in its **own** try/except within the services strip, **after** the TB snapshot and **independent** of it. Gated by `flows.enabled()`.
- **Failure behavior:** any failure/timeout sets `services.node_red` to `stopped`/`unknown` **only**; it never affects the ThingsBoard snapshot or the rest of the page.
- Naming: the TB indicator is `thingsboard_connectivity` (API reachability), explicitly **not** described as ingestion health.

---

## 13. CHERT tokens & chart palette

Use `portal/app/static/chert-tokens.css` CSS variables (single source, from `docs/branding/tokens/colors.json`): page `--chert-cream`, cards `--chert-surface`, borders `--chert-border`, text `--chert-ink`, emphasis `--chert-orange`. Add `--chert-ok/--chert-warn/--chert-crit` status tokens if absent (no hardcoded hex). Chart colors read from these vars via `getComputedStyle` so a token change reskins charts.

---

## 14. Caching (expanded)

- **Scope:** **process-local, per worker** (in-memory dict). Not shared across workers/processes.
- **Bounded:** maximum **N** entries (e.g. 256) with simple LRU/oldest-eviction; keyed by `(project_id, range, device, key)`.
- **TTL:** short (default **15 s**, `MONITORING_CACHE_TTL`).
- **Disableable:** `MONITORING_CACHE_TTL=0` disables caching entirely.
- **Data only:** cache stores only snapshot **data** — **no role, membership, or authorization fields**.
- **Never an access boundary:** **every request passes membership authorization first**; the cache lookup happens **only after** `require_membership` succeeds. A cache hit never bypasses authorization.
- **Invalidation:** an alarm ack invalidates that project's entries.
- **ThingsBoard load with multiple workers:** each of *W* workers holds its own cache, so worst case is *W* × (4 calls) per TTL window per active (project,range,device,key) combo, regardless of viewer count — bounded and predictable; typical steady state is ≤4 calls/15 s per active project per worker.

---

## 15. Alarm acknowledgement sequence

```
POST /projects/{project_id}/monitoring/alarms/{alarm_id}/ack
 1. require_membership(...)                          # 403 if not an active member
 2. CSRF check (session-bound token)                # 403 on failure
 3. with as_project(member) as (_, session):
 4.     alarm = <tenant-scoped alarm-read endpoint>       # UNVERIFIED — see spike §15.1; must 404/403 out-of-tenant
 5.     if not found / out-of-tenant → 404
 6.     severity = alarm.severity                    # determined SERVER-SIDE
 7.     if severity == CRITICAL and member.role != owner → 403 (per §7)
 8.     session._post(f"/alarm/{alarm_id}/ack")      # ack via the SAME tenant session
 9. invalidate project cache
10. audit(db, user.email, "alarm.ack", project.slug, alarm_id=…, severity=…)  # AFTER success only
```

Severity is never taken from the client. Ordinary-vs-critical policy is enforced server-side. Audit is written only on success.

### 15.1 Required implementation-start spike (blocking)

The exact tenant-scoped alarm-read endpoint (step 4) is **not yet verified**. `/alarm/info/{alarm_id}` is a candidate only and is **not presented as proven**.

**Required implementation-start spike: verify the tenant-scoped alarm-read endpoint before implementing acknowledgement. No acknowledgement feature may be built until the endpoint and its cross-tenant 404/403 behavior are proven against the installed ThingsBoard CE version (or the authoritative API for that exact version).** The `POST /alarm/{id}/ack` acknowledgement path is likewise verified in the same spike.

---

## 16. Feature flag, staging acceptance, rollback

- **Flag:** `settings.monitoring_enabled` (`MONITORING_ENABLED`). Staging = true; production = false until accepted. Route + nav both guard on it.
- **Staging acceptance:** all §20 negative cross-project isolation tests pass; KPIs/roster/alarms match the TB console for a seeded project; charts render real seeded telemetry across ranges; device/key selectors work incl. all empty states; EN + Arabic-LTR render (LTR preserved, long AR labels don't clip); loading/stale/denied/unavailable/partial states reproduce; 429 under abusive polling, never under normal 30 s; tablet/mobile usable; keyboard focus + non-color status; **external-asset test passes and Monitoring works with outbound internet disabled**; no secrets/tokens/tenant ids in any response; audit rows for view/ack.
- **Rollback:** additive, **no schema migration** → rollback = redeploy the previous portal image by digest. First-line mitigation = `MONITORING_ENABLED=false` + recreate portal. Grafana/TB untouched.

---

## 17. Unresolved follow-up — instructor / admin tenant-session access

`require_membership` + `as_project(member)` yield a tenant session only for an **active `ProjectMember`** with a `tb_user_id` inside the project tenant. Instructors and platform admins are generally not ProjectMembers and have no such `tb_user_id`, so there is **no proven, safe tenant-session path** for them yet. Options to design later (each needs its own security review): a read-only instructor TB user provisioned into assigned-cohort tenants; sysadmin-impersonation of an existing member strictly for read; or a portal-side read-only projection. **Until proven, the initial implementation serves active ProjectMembers only**, and any platform-admin access is a separate **audited break-glass** design.

---

## 18. Deferred / later spikes

- Per-tenant message throughput via `GET /api/usage` — verify fields on staging before any throughput card; excluded until proven real.
- Per-project Grafana orgs / new time-series pipeline — deferred by owner decision.
- Device command UI (owner) — separate capability; monitoring only links to it.
- Removing inline `style=` attributes to drop the CSP `style-src 'unsafe-inline'` exception.

---

## 19. Project Overview redesign & unified navigation

- **Shared partial `_project_nav.html`:** project header (name · lifecycle chip · **slug/reference only** · breadcrumb) + sub-nav: Overview · Devices · Telemetry · **Monitoring** · Alerts · Flows · LoRaWAN · Notebooks · Settings. Engine names stay out of student nav; "Open in ThingsBoard" is a protected action for owners.
- **Overview (`GET /projects/{id}`)** redesigned to: identity + lifecycle + provisioning status; an **at-a-glance mini monitoring panel** (counts only, reusing `monitoring.snapshot`); totals; recent activity (from `audit`); capability cards as secondary nav.
- **Integration:** Monitoring is a sub-nav tab; Overview deep-links to it; the platform-Grafana link appears **only for platform admins**.

---

## 20. Negative cross-project test matrix (release-blocking)

Scope = active `ProjectMember`s only (instructor/admin deferred, §17). Fixtures: Alice is an active member of projects A1 and A2; Bob is a member of B1; Alice is *not* a member of B1. Every row must pass on staging before release; any cross-project disclosure is a release blocker.

| # | Attempt | Expected |
|---|---|---|
| 1 | Alice `GET /projects/{B1}/monitoring` | 403 (not a member) — before any TB call |
| 2 | Alice `GET /projects/{B1}/monitoring/data` | 403 |
| 3 | Alice `POST /projects/{A1}/monitoring/alarms/{B1_alarm_id}/ack` | 404 (alarm id outside A1's tenant, resolved via A1 session) |
| 4 | Alice `GET /projects/{A1}/monitoring/data?device={B1_device_id}` | 400/ignored — device not in A1's tenant device list; no B1 data returned |
| 5 | Alice edits the URL `project_id` A1→B1 | 403 before any TB call (membership re-checked on the new id) |
| 6 | Disabled member of A1 opens Monitoring | 403 |
| 7 | Non-member (no membership row) opens Monitoring | 403 |
| 8 | Feature flag off → `GET /projects/{A1}/monitoring` | 404 (route/nav guarded) |
| 9 | `range`/`device`/`key` set to an invalid or injection value | 400 (server-side allow-list; never trusted) |
| 10 | Non-owner member acks a **critical** alarm in A1 | 403 (per §7 policy) |
| 11 | Ack request without a valid CSRF token | 403 |
| 12 | Inspect any response body for `tb_tenant_id`, TB JWT, or token | none present |

These rows are the source for `test_monitoring.py`'s negative suite (referenced from §3.2 and §16).

---

**Bottom line:** a thin, typed, feature-flagged Monitoring capability over the existing impersonation boundary and `dashboard_data` layer; TB-CE-real per-project data only; explicit device/key selection; locally-vendored Chart.js under a strict CSP with an automated external-asset guard; active-member scope with instructor/admin access deferred as an explicit follow-up; additive and rollback-clean — ready to implement on the v2 branch once approved.
