# CHERT IoT v2 plan — engineering review

**Status:** Advisory / design input for CHERT IoT v2. No code, branches, tags, snapshots, or deployments result from this document.
**Author:** Claude (engineering).
**Inputs:** the v2 unified-platform master plan draft, the current-state (ThingsBoard Home, Grafana platform dashboard) screenshots, the to-be concept poster, and the live codebase (portal, compose, `grafana-brand/`, `thingsboard-brand/`, monitoring provisioning).

> Sanitization note: staging identifiers (tenant UUIDs, demo emails, private project slugs) are replaced with placeholders. This document contains no credentials, tokens, internal account details, or machine-specific paths.

---

## 1. Verdict

The plan's **direction and governance are right** — freeze v1, staging-first, negative isolation tests, rollback evidence, "engines are internal capabilities; the portal is the product." Keep all of it. The material corrections are: (1) the tenancy model is **Project = ThingsBoard Tenant** (confirmed below), not customer-per-project; (2) **project-scoped Grafana** is a hard multi-tenancy problem on Grafana OSS, so project monitoring is delivered **portal-native over ThingsBoard REST**; and (3) v2 **reuses the substantial project-centric shell that already exists** — it is a completion, not a greenfield rewrite — developed on a dedicated v2 branch off the frozen production commit.

---

## 2. Confirmed tenancy model — Project = ThingsBoard Tenant

Resolved from four authorities; all agree. The "Customer-per-project" wording was the **superseded draft** of D13, which the ADR records as superseded.

- **PLAN.md (D13):** "**Project = a TB Tenant.** Owner + members are Tenant-Admin users within it … the portal is the identity broker … opens project sessions via sysadmin impersonation. … **No TB Customers.** Supersedes D4."
- **PLAN.md (D4, superseded):** "ONE TENANT PER PROJECT … Never customer-per-project (CE customers are read-only)."
- **ADR-001:** "Tenancy: **Project = TB Tenant**"; "supersedes D4 tenant-per-student **and the draft Customer-per-project**"; "**RESOLVED: Project = TB Tenant**."
- **Implementation:** `models.py` `Project.tb_tenant_id` (no `tb_customer_id`); `project.py` creates **one TB Tenant per project** and each member as **TENANT_ADMIN**; sessions via `impersonate()`; **no customer creation anywhere**.
- **Live staging (sanitized):** a student who is an active member of **two projects** resolved to **two distinct tenant ids** (`<project-A-tenant-uuid>`, `<project-B-tenant-uuid>`); ThingsBoard reported only tenants and **zero customers**.

### 2.1 Identity / scope table

| Layer | Value / mechanism | Scope |
|---|---|---|
| Portal Project identity | `projects.id` (UUID) + `projects.slug` (unique) | Canonical source of truth |
| Student / user identity | one Keycloak identity → one `portal_users` row | One human across their projects |
| ThingsBoard Tenant | `projects.tb_tenant_id` — one per project | The isolation boundary |
| ThingsBoard Customer | none (no field; zero customers exist) | N/A — not part of the model |
| Device ownership | device created **inside the project tenant** via the member's impersonated session; no customer assignment | Tenant-scoped, native isolation |
| Auth / impersonation | `require_membership` (403 for non-members) → `impersonate(ProjectMember.tb_user_id)` → tenant-scoped session | Cross-tenant access impossible via this path |

**Consequence:** because the project **is** the tenant, a Tenant Admin naturally seeing all entities in their own tenant is correct (no customers to filter). **Cross-student isolation** = TB tenant boundary + portal membership gate. **Same-student multi-project scoping** = which project-tenant session the portal impersonates.

### 2.2 User-facing project reference

The **`tb_tenant_id` is never displayed** to users, in any UI or response model. The only user-facing reference is the **project slug / portal-generated reference**.

---

## 3. Monitoring direction (why portal-native)

- Grafana's only datasource is Prometheus, which holds **platform/infrastructure aggregates** (host CPU/RAM, container I/O, PostgreSQL, global message throughput). There is **no per-project data** in it.
- Grafana OSS has **no row-level/label-enforced security**; a shared datasource with a "project" dropdown is client-side selection — forbidden as a security boundary and it fails the isolation test.

Therefore **Project Monitoring is portal-native, backed by ThingsBoard REST**, scoped by the existing membership + impersonation boundary. **Grafana remains platform-infrastructure monitoring for platform administrators only.** Per-project Grafana orgs and any new time-series pipeline are **deferred**. Detailed design: `project-monitoring-design.md`.

---

## 4. v1 → v2 strategy (respecting the owner decision)

- **Freeze v1** — snapshot + tag `chertiot-v1-as-is-final` from the current production commit; capture the freeze record (image digests, backup ids, restore evidence, screenshots, smoke results). *(Not to be executed until the owner authorizes; no snapshot/tag is created by this review.)*
- **Branch v2** — `release/chertiot-v2-unified` **from that same production commit**, inheriting the working portal, provisioning, `tb_client`, membership guards, SSO, ar-SA locale, and branded-image pipelines.
- **Reuse, don't rebuild** — treat the existing project shell (§5) as the v2 baseline; add only missing capabilities + the visual system.
- **Staging-first milestones**, each passing functional + negative-isolation tests before the next.
- **Controlled reconciliation** — any severity-1 v1 fix is applied to frozen v1 and cherry-picked into v2 (no silent divergence).
- **Final cutover with rollback** by image digest.

Project Monitoring is the **first work package** under this plan — not a replacement for it.

---

## 5. Existing-capability matrix (evidence-based)

Routes in `portal/app/routers/*` + `portal/app/project.py`; authorization via `require_membership` (403 for non-members).

| Capability | Route(s) | Source file | Status | Tests | v2 verdict |
|---|---|---|---|---|---|
| Home / portfolio | `GET /`, `GET /home`, `GET /projects/new`, `POST /projects` | `routers/home.py`, `routers/projects.py` | Implemented | `integration/test_provisioning.py` | Reuse |
| Project Overview | `GET /projects/{id}`, `GET …/panel` | `routers/projects.py` | Partial (cards, not a rich overview) | — | **Redesign** |
| Devices | `GET/POST …/devices`, `…/{id}`, `…/snippet/{track}`, `…/rename`, `…/revoke`, `…/delete`, `…/dashboard/reset` | `routers/devices.py` | Implemented, tenant-scoped | `e2e/test_devices.py` | Reuse + visual tokens |
| Telemetry (portal-native) | — | — | **Missing** | — | Build |
| Monitoring | — | — | **Missing** (this work package) | — | Build |
| Alerts (rules) | `GET/POST …/alerts`, `…/{id}/delete` | `routers/alerts.py` | Implemented | `unit/test_alerts.py` | Reuse + visual tokens |
| Flows (Node-RED) | `GET …/flows`, `…/ready`, `POST …/start`, `…/stop` | `routers/flows.py` | Implemented | `unit/test_flows.py` (incl. 403 isolation) | Reuse + visual tokens |
| LoRaWAN | `GET/POST …/lora` | `routers/lora.py` | Implemented | `unit/test_lora.py` | Reuse + visual tokens |
| Notebooks | Lab handoff + `POST /internal/lab-token` | JupyterHub + router | Implemented | `unit/test_internal_lab_token.py` (incl. non-member 403) | Reuse + visual tokens |
| Report | `GET …/report` | `routers/projects.py` | Implemented | `unit/test_export.py` | Reuse + visual tokens |
| Settings / members | `…/members/{id}/{action}`, `…/invite`, `…/join`, `…/requests/{id}/{decision}` | `routers/projects.py` | Implemented | — | Reuse + add settings/audit |
| TB handoff (protected native) | `GET …/thingsboard` | `routers/projects.py` | Implemented (SSO handoff) | `e2e/test_keycloak_tb_sso.py` | Reuse as protected native interface |
| Provisioning | `POST …/provision` | `routers/projects.py`, `project.py` | Implemented, idempotent | `integration/test_provisioning.py` | Reuse |

**Already done (plan lists as requirements):** Keycloak Generic OAuth + PKCE; Grafana SSO auto-login (break-glass `/login?disableAutoLogin`); Grafana ar-SA LTR branded image (`ghcr.io/chertsa/chertiot-grafana:13.1.4-b1`); `thingsboard-brand/` + `grafana-brand/` build pipelines; portal EN/AR i18n.

**Test-coverage gaps for v2:** negative cross-project isolation tests exist for **flows** and **lab-token** only; add equivalent 403 / object-reference-substitution tests for **devices, alerts, lora, report, members**, and the new **monitoring** capability.

---

## 6. Runtime-asset & CSP finding (portal-wide)

The portal must have **zero external runtime asset dependencies**. Current audit:

| Item | Location | Verdict |
|---|---|---|
| Chart.js (cdnjs) | `templates/project.html`, `templates/project_report.html` | **External — must be vendored** |
| Fonts (Inter, IBM Plex Sans Arabic) | `static/chert-fonts.css` → `/static/fonts/*.woff2` | Local ✓ |
| Nav links (grafana./status./lab.) | anchors to CHERT-controlled subdomains | First-party navigation ✓ |
| Browser fetches (`/flows/ready`, `/panel`) | same-origin portal routes | ✓ |
| Google Fonts / unpkg / jsdelivr / external icons / 3rd-party JS / remote CSS / browser→engine bypass | — | none found |

No CSP middleware exists yet. Remediation (vendoring Chart.js, adding CSP, and an automated external-URL test) is specified in the monitoring design and applies portal-wide; the two existing Chart.js CDN usages are reported here and are remediated as part of that work (not silently).

**Mandatory principle (adopted):** *CHERT production UI has zero external runtime asset dependencies. All browser-delivered assets are version-pinned, stored in the repository or approved CHERT artifact storage, included in the deployed image, and served from CHERT-controlled origins.*

---

## 7. Remaining unresolved design question

**Instructor / platform-administrator tenant-session access is unresolved.** `require_membership` + `as_project(member)` resolve a session only for an **active `ProjectMember`** (a human with a `tb_user_id` inside the project tenant). Instructors and platform admins are generally **not** ProjectMembers and have **no `tb_user_id`** in that tenant, so there is no proven, safe way for them to obtain a tenant-scoped session yet. Until that resolution is designed and proven, **the initial implementation serves actual active ProjectMembers only**; instructor read-only access and an audited platform-admin break-glass path are follow-up design items.
