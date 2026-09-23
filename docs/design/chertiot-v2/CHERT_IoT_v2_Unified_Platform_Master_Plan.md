<!-- CANONICAL, version-controlled copy. Source: the owner-UAT draft under docs/owner_uat/4/ (git-ignored audit evidence). This tracked file is authoritative. -->

# CHERT IoT v2 — Unified Project-Centric Platform Master Plan

**Document type:** Implementation plan and Claude Code execution specification  
**Status:** Proposed for owner approval  
**Target:** CHERT IoT v2  
**Principle:** CHERT IoT is the product; ThingsBoard, Grafana, ChirpStack, Node-RED and JupyterHub are internal capability engines.

---

## 0. AS-BUILT RECONCILIATION (v2 — authoritative; overrides any contradiction below)

This banner reconciles this plan with the running code and the canonical ADR
(`docs/adr/ADR-001-project-centric-platform.md`). Where the body of this document disagrees, **this
section and ADR-001 win.**

1. **Tenancy — Project = a ThingsBoard *Tenant* (NOT a Customer).** Proven from code
   (`app/project.py`: `sysadmin.save_tenant(...)`, member users created with `authority="TENANT_ADMIN"`
   and `tenantId`, `delete_tenant(...)`; there is **no** `save_customer`/customer-user path anywhere).
   Owner and members are Tenant-Admin users in the project's tenant; the portal brokers per-project
   sessions via sysadmin impersonation. **Ignore every "ThingsBoard Customer" / `tb_customer_id`
   reference in §4.1 and §7.3 below** — the field is `tb_tenant_id` and isolation is the tenant
   boundary (D13 / ADR-001, which supersedes the earlier Customer-per-project draft).

2. **Project monitoring is portal-native (ThingsBoard-backed), NOT Grafana.** The delivered "Monitoring"
   and "Telemetry" tabs read the project's ThingsBoard tenant directly (tenant-scoped, server-side
   isolated). **Project-scoped Grafana (§7.5b, §9) is DEFERRED** — see
   `docs/owner_uat/4/RESPONSE-to-be-gap-and-grafana.md` for why (Grafana's datasource is Prometheus =
   platform/infra metrics; per-project IoT data lives in ThingsBoard; OSS Grafana cannot make a
   dashboard variable an authorization boundary). **Grafana today = platform monitoring, staff-only.**

3. **Arabic is translation-only LTR.** `lang="ar"`, `dir="ltr"`; no page/shell RTL (enforced in
   `app/i18n.py`; verified EN/AR desktop+mobile). This matches §2.10 and §6.2; any RTL implication
   elsewhere is void.

4. **Current phase status (2026-09-23):** V2.0 Foundation ✓ · V2.1 Overview/lifecycle ✓ ·
   V2.2 Devices+Telemetry ✓ · V2.3 Monitoring — portal-native ✓, platform Grafana staff-gated ✓,
   **project-scoped Grafana deferred** · V2.5 LoRaWAN+Notebooks ✓ (named servers) · **V2.4 Phase 4
   authorization model — centralized in `app/permissions.py`, in owner review** · V2.6 Visual/RC —
   pending · Production cutover — pending (**production stays frozen v1**, tag `chertiot-v1-as-is-final`
   → `9a02579`).

5. **Authorization model** is centralized in `app/permissions.py` (capability matrix, §10). Platform
   Grafana access is enforced at the Grafana OAuth layer (Keycloak realm role), not only the portal
   link — a portal-link gate alone is insufficient.

6. **No external runtime assets.** Every page loads only from the CHERT hosts (self + auth/app/lab/
   grafana/status subdomains); JS/CSS/Chart.js are vendored/self-hosted (verified by an exact
   hostname allowlist in browser checks). **Production remains frozen v1** (`chertiot-v1-as-is-final`
   → `9a02579`); v2 lives only on staging until the owner-approved cutover.

**Canonical identity:** the portal `Project` UUID is the single cross-platform identity and maps
**Project UUID → ThingsBoard Tenant** (plus ChirpStack Application, Node-RED instance, Jupyter named
server). There is **no Customer-per-project implementation**.

---

## 1. Executive decision

CHERT IoT v1 will be snapshotted, tagged and frozen as the proven rollback baseline. CHERT IoT v2 will be developed as a new unified Project-centric release rather than as incremental modifications to the production interface.

The portal becomes:

- the single product shell;
- the source of truth for Project identity and lifecycle;
- the authorization gateway for every capability;
- the owner of global and Project navigation;
- the owner of the English/Arabic LTR preference;
- the only normal entry point for students and Project members.

The underlying engines remain operationally independent but are presented as CHERT capabilities:

| Engine | CHERT capability |
|---|---|
| ThingsBoard CE | Devices, assets, telemetry, commands and alarms |
| Grafana OSS | Project and platform monitoring |
| ChirpStack | LoRaWAN connectivity |
| Node-RED | Flows and automation |
| JupyterHub | Notebooks and analysis |

Engine product names must not dominate normal student navigation. Native engine interfaces may remain available only through controlled administrator or break-glass access.

---

## 2. Non-negotiable constraints

1. Do not modify CHERT IoT v1 after it is frozen except through a separately approved emergency-fix process.
2. Do not develop v2 directly on the production branch or production server.
3. Do not replace supported APIs with database writes.
4. Do not use Nginx, injected JavaScript or runtime CSS as the permanent customization method.
5. Do not use Project names as identifiers or authorization keys.
6. Do not use client-side filtering as a security boundary.
7. Do not change SSO, authorization, visual branding and datasource queries in one indivisible deployment.
8. Do not overwrite the existing Grafana infrastructure dashboard with a Project dashboard.
9. Do not fabricate data to reproduce values shown in the To-Be concept.
10. Arabic is a translation in an LTR interface; v2 does not introduce RTL layout.
11. Every release goes staging → verification → owner acceptance → production.
12. Every production mutation must have a tested rollback path.

---

## 3. Version boundary and repository freeze

### 3.1 Capture the v1 baseline

Before v2 development:

- take a complete infrastructure snapshot;
- create verified database backups;
- export ThingsBoard dashboards and configuration;
- export Grafana dashboards, folders, datasources and alert definitions;
- record Keycloak clients, scopes, redirect URIs and role mappings;
- record deployed container image names and immutable digests;
- record application configuration checksums;
- capture current English and Arabic-LTR screenshots;
- run and retain the current smoke-test results;
- perform one restoration rehearsal or prove the most recent restoration evidence.

### 3.2 Freeze markers

Recommended immutable Git tag:

```text
chertiot-v1-as-is-final
```

Recommended v2 development branch:

```text
release/chertiot-v2-unified
```

Create a short freeze record containing:

- timestamp;
- owner approval;
- production commit;
- image digests;
- database backup identifiers;
- snapshot identifier;
- known defects and accepted limitations;
- rollback procedure.

### 3.3 v1 maintenance policy

After freeze:

- no v2 code is backported to v1;
- no visual redesign is performed on v1;
- only severity-1 production fixes may be applied;
- any emergency v1 fix must be tagged and documented without moving the v2 baseline silently.

---

## 4. Product architecture

### 4.1 Canonical Project

The portal Project row is the canonical record. Its immutable UUID is the only cross-platform Project identity.

Each Project maps to:

| Portal field | Purpose |
|---|---|
| `project_uuid` | Canonical immutable Project identity |
| `owner_user_id` / membership relation | Authorization |
| `tb_tenant_id` | ThingsBoard tenant (Project = TB **Tenant**; see §0) |
| `chirpstack_application_id` | LoRaWAN scope |
| `nodered_instance_id` | Flow runtime |
| `jupyter_server_id` | Notebook runtime |
| Grafana scope reference | Monitoring context |
| lifecycle state | Provisioning, active, suspended, archived or failed |

Display names may change and must never be used for authorization or engine reconciliation.

### 4.2 Unified request path

```text
Authenticated user
→ CHERT IoT portal
→ selected Project UUID
→ server-side membership check
→ engine resource resolution
→ capability-specific session or signed transition
→ project-scoped content
```

### 4.3 Engine boundaries

- The portal must use supported REST/HTTP APIs.
- `tb_client.py` remains REST-only.
- Engine credentials remain server-side.
- The browser must not receive privileged service credentials.
- Engine health failures must appear as CHERT capability states rather than raw stack traces.

---

## 5. Unified information architecture

### 5.1 Global navigation

The normal user shell contains:

1. **Home** — portfolio summary and recent Projects.
2. **Projects** — create, search, filter and manage Projects.
3. **Reports** — lifecycle and consolidated reports permitted by role.
4. **Notifications** — Project and platform events visible to the user.
5. **Profile** — identity, language and session actions.

Do not place ThingsBoard, Grafana, Node-RED, ChirpStack or JupyterHub in global student navigation.

### 5.2 Project navigation

When a Project is selected, the shell must clearly display:

- Project name;
- lifecycle state;
- immutable short reference;
- environment indicator where relevant;
- breadcrumb back to Projects;
- Project capability navigation.

Required Project sections:

1. **Overview**
2. **Devices**
3. **Telemetry**
4. **Monitoring**
5. **Alerts**
6. **Flows**
7. **LoRaWAN**
8. **Notebooks**
9. **Project settings**

### 5.3 Administrator navigation

Administrators receive a separate, role-gated area:

- Platform health;
- Provisioning failures;
- Engine status;
- Audit events;
- User and role administration;
- protected native-engine access;
- break-glass operations.

This area must not be discoverable or reachable by normal students merely by guessing routes.

---

## 6. CHERT visual system

### 6.1 Design tokens

Create a version-controlled design-token package or equivalent shared specification.

Core palette:

| Token | Intended use |
|---|---|
| CHERT cream | Application background |
| Paper white | Cards, tables and working surfaces |
| Espresso brown | Navigation, primary text and strong surfaces |
| Copper orange | Primary actions, active navigation and chart emphasis |
| Muted warm gray | Secondary text and borders |
| Operational green | Healthy/connected state |
| Warning amber | Degraded or attention state |
| Critical red | Failure and destructive action |

The exact color values must be extracted from the approved CHERT brand assets and stored once. Do not duplicate arbitrary values across applications.

### 6.2 Typography

- Use one approved Latin family for English interface text.
- Use Noto Sans Arabic or the approved CHERT Arabic family for Arabic.
- Preserve technical product terms in Latin where translation would reduce clarity.
- Minimum normal UI text should remain readable at browser zoom up to 200%.
- Arabic text must be properly shaped while the page layout remains LTR.

### 6.3 Common components

Standardize:

- global header;
- Project header;
- side navigation;
- breadcrumbs;
- buttons;
- cards;
- data tables;
- tabs;
- status chips;
- empty states;
- skeleton/loading states;
- warning/error states;
- confirmation dialogs;
- chart palette;
- notification banners;
- language selector;
- user menu;
- mobile navigation.

### 6.4 Branding assets

Required assets:

- CHERT stone mark;
- CHERT wordmark;
- `CRADLE OF EXPERTS` lockup where space permits;
- favicon;
- loading mark;
- light and dark approved variants;
- monochrome variant.

Do not redraw or approximate the production logo in CSS.

---

## 7. Screen and function specification

## 7.1 Home — Projects portfolio

### Purpose

Give the user an immediate view of their Projects rather than engine shortcuts.

### UI

- greeting and account context;
- Projects summary cards;
- lifecycle distribution;
- recent Projects;
- Projects requiring attention;
- recent notifications;
- create Project action when authorized;
- global platform status shown only at an appropriate abstraction level.

### Functions

- open a Project;
- create a Project;
- filter by lifecycle state;
- search by Project name/reference;
- view provisioning progress;
- resume failed provisioning when authorized;
- archive or restore according to policy.

### Empty state

Explain how to create the first Project. Do not display native ThingsBoard onboarding, community templates or engine setup instructions as the CHERT Home experience.

## 7.2 Project Overview

### UI

- Project identity and state;
- owner and membership summary;
- provisioning status across capabilities;
- device, alert and activity totals;
- recent activity timeline;
- capability cards for Devices, Monitoring, Flows, LoRaWAN and Notebooks;
- contextual actions allowed by role.

### Functions

- navigate to each capability;
- inspect provisioning errors;
- retry safe idempotent provisioning steps;
- view Project audit trail;
- manage Project members if authorized.

## 7.3 Devices

### Engine

ThingsBoard CE through supported APIs.

### UI

- Project-scoped device table;
- connectivity status;
- device profile/type;
- last activity;
- alarm badge;
- gateway or transport type;
- search, sorting and filters;
- create/register device action;
- device details panel.

### Functions

- create device;
- create it in the Project’s ThingsBoard **Tenant** (owner/members are Tenant-Admins);
- view credentials only according to policy;
- update permitted metadata;
- deactivate/archive where supported;
- open telemetry;
- send permitted commands;
- view related alarms.

### Security

The server must resolve the Project to its `tb_tenant_id` and act via the member's impersonated tenant session. A caller-supplied tenant/device ID must not be trusted (see §0).

## 7.4 Telemetry

### UI

- Project and device selector;
- time-range selector;
- live/recent telemetry;
- metric cards;
- time-series charts;
- latest-value table;
- export action if authorized;
- no-data and stale-data states.

### Functions

- retrieve telemetry for devices within the Project;
- compare approved metrics;
- change time range;
- stream or refresh current values;
- link to alarms and device details.

### Preservation

Do not alter existing telemetry ingestion, MQTT topics or ThingsBoard rule processing merely to redesign the UI.

## 7.5 Monitoring

### Engine

Grafana OSS, entered through CHERT IoT with SSO.

### Project monitoring UI

- project message throughput;
- successful/failed messages;
- relevant gateway health;
- Project Node-RED instance health;
- Project alarm trend;
- device availability;
- Project service health;
- time-range controls.

### Platform monitoring UI

Role-gated administrators retain:

- ThingsBoard transport rate;
- container network I/O;
- host CPU;
- host memory;
- PostgreSQL connections;
- total platform message rate;
- service and container health.

### Rules

- Preserve the existing infrastructure dashboard and its UID.
- Create a new Project dashboard with a new UID.
- Never replace real queries with sample values from the concept image.
- Preserve datasource credentials server-side.
- Viewer remains the default Grafana role.
- Break-glass local Grafana login remains available through a protected documented route.

## 7.6 Alerts

### UI

- active, acknowledged and cleared tabs;
- severity filters;
- device/source filter;
- timestamp and age;
- acknowledgement state;
- Project context;
- alert details panel.

### Functions

- view Project alarms;
- acknowledge when role permits;
- navigate to the source device;
- correlate with telemetry;
- show monitoring context.

Define whether ThingsBoard, Grafana or the portal owns each alert type. Do not merge distinct alert semantics without an explicit normalized model.

## 7.7 Flows

### Engine

Per-Project Node-RED instance.

### UI

- instance status;
- open editor;
- deployed/not-deployed state;
- last deployment;
- health and error summary;
- safe restart when authorized.

### Functions

- provision one instance per Project;
- SSO transition;
- retain Project context;
- prevent navigation to another Project instance;
- preserve flows across image upgrades.

## 7.8 LoRaWAN

### Engine

ChirpStack Application mapped to the Project.

### UI and functions

- application status;
- gateways and devices;
- uplink/downlink activity;
- join status;
- frame counters;
- signal indicators where available;
- open advanced network view for authorized roles.

All queries must derive the ChirpStack Application ID from the portal Project record.

## 7.9 Notebooks

### Engine

JupyterHub named server mapped to the Project.

### UI and functions

- server state;
- launch/resume;
- stop when authorized;
- recent notebooks if available through supported integration;
- Project storage context;
- SSO transition.

Notebook access must not expose another Project’s server or files.

## 7.10 Project settings

### UI and functions

- display name and description;
- member list and roles;
- lifecycle controls;
- capability provisioning state;
- audit history;
- archive action;
- destructive-action confirmation.

Engine identifiers may be shown only to administrators in a diagnostics section.

---

## 8. ThingsBoard customization strategy

### 8.1 Product role

ThingsBoard is the operational IoT engine. Its standard Home screen is not the CHERT IoT student Home in v2.

### 8.2 Implementation requirements

- Maintain a pinned ThingsBoard CE source version.
- Create a reproducible `thingsboard-brand/` build pipeline.
- Apply CHERT assets and design tokens at source/build time.
- Maintain Arabic translation as a standard locale.
- Keep layout LTR in both languages.
- Use supported REST APIs for portal integrations.
- Create Project dashboards or portal-native views based on verified API capability.
- Scope entities through the Project’s ThingsBoard **Tenant** (sysadmin-impersonated member session).

### 8.3 Protected native interface

The native ThingsBoard tenant administration interface may remain available only to permitted administrators. It is not linked from student navigation.

### 8.4 Upgrade policy

- Keep CHERT changes in reviewable commits or patch layers.
- Avoid broad forks without documented reasons.
- Rebase onto a pinned upstream version in staging.
- Run locale, build, navigation, API and dashboard regression tests.

---

## 9. Grafana customization strategy

### 9.1 Product role

Grafana provides monitoring and analytics within the selected Project plus protected platform monitoring for administrators.

### 9.2 Implementation requirements

- Maintain a pinned Grafana OSS source version.
- Continue the reproducible `grafana-brand/` pipeline.
- Preserve compiled `ar-SA` LTR locale.
- Apply CHERT design tokens at build time.
- Preserve Generic OAuth, PKCE and auto-login.
- Preserve break-glass local authentication.
- Provision dashboards through version-controlled JSON or the established supported method.
- Separate Project and platform dashboards.

### 9.3 Dashboard rules

- Each dashboard has a stable UID.
- Queries and variables are version controlled.
- Datasources are provisioned without exposing secrets.
- Project variables aid selection but never provide authorization.
- Query result equivalence is tested before and after visual-only changes.

---

## 10. Authentication, authorization and isolation

### 10.1 SSO

Keycloak remains the identity provider.

Required behavior:

- one login for CHERT IoT;
- engine transitions do not prompt for another password;
- logout behavior is documented and tested;
- expired sessions fail safely;
- redirect URIs are explicit and environment-specific;
- no open redirects.

### 10.2 Roles

Define and test at minimum:

- student/Project member;
- Project owner;
- instructor;
- tenant administrator;
- platform administrator;
- break-glass administrator.

Every capability must document allowed actions by role.

### 10.3 Isolation tests

Use at least:

- User Alice with Projects A1 and A2;
- User Bob with Project B1;
- one instructor with permitted broader access;
- one administrator.

Mandatory negative tests:

1. Alice cannot access B1 by changing a portal URL.
2. Alice cannot change a Grafana variable to retrieve B1.
3. Alice cannot substitute a ThingsBoard tenant or device ID from B1.
4. Alice cannot open Bob’s Node-RED instance.
5. Alice cannot open Bob’s ChirpStack Application.
6. Alice cannot open Bob’s Jupyter server.
7. a student cannot open platform monitoring.
8. a Viewer cannot edit Grafana dashboards.

Any cross-Project disclosure is a release blocker.

---

## 11. Error, loading and degraded states

Every capability must implement:

- loading state;
- empty state;
- permission-denied state;
- provisioning-in-progress state;
- engine-unavailable state;
- stale-data warning;
- partial-service degradation;
- retry action when safe;
- support reference or correlation ID.

Do not expose secrets, internal stack traces, tokens or private endpoints.

If one engine is unavailable, the Project shell and other capabilities must remain usable.

---

## 12. Accessibility, responsiveness and localization

- Support current desktop targets and practical tablet/mobile layouts.
- Maintain keyboard navigation and visible focus.
- Give icon-only actions accessible labels.
- Do not encode status by color alone.
- Verify contrast for cream, brown and orange combinations.
- Verify 200% text enlargement.
- Keep English and Arabic content inside the same LTR structural layout.
- Test long Arabic labels for clipping.
- Preserve numbers, identifiers, code, URLs and product acronyms appropriately.

---

## 13. Delivery phases

## V2.0 — Foundation

- v1 snapshot, tag and freeze;
- v2 branch;
- design tokens;
- unified shell;
- global navigation;
- language/session handling;
- canonical Project context;
- feature flags;
- baseline automated tests.

**Exit gate:** shell, authentication and Project selection work on staging without engine integration regressions.

## V2.1 — Project Overview and lifecycle

- Projects portfolio;
- Project Overview;
- provisioning state;
- lifecycle actions;
- audit visibility.

**Exit gate:** existing Projects reconcile correctly and new Project provisioning is idempotent.

## V2.2 — Devices and telemetry

- ThingsBoard Tenant mapping;
- Project device list;
- device details;
- telemetry;
- commands permitted by role;
- Arabic LTR.

**Exit gate:** positive and negative Customer/device isolation tests pass.

## V2.3 — Monitoring

- Project Grafana dashboard;
- portal Monitoring capability;
- SSO transition;
- Project query scoping;
- protected platform monitoring.

**Exit gate:** URL tampering and datasource isolation tests pass; existing infrastructure monitoring remains correct.

## V2.4 — Alerts and flows

- normalized alert presentation;
- acknowledgement policy;
- Node-RED Project capability;
- instance health and launch flow.

**Exit gate:** Project alert and Node-RED isolation pass.

## V2.5 — LoRaWAN and notebooks

- ChirpStack Application capability;
- Jupyter named-server capability;
- status, launch and safe controls.

**Exit gate:** cross-Project Application/server access is denied.

## V2.6 — Unified release candidate

- full visual consistency;
- responsive verification;
- accessibility;
- Arabic/English coverage;
- performance;
- security review;
- restore rehearsal;
- owner browser acceptance.

**Exit gate:** signed GO decision for production.

---

## 14. Testing requirements

### 14.1 Contract tests

- portal-to-engine mappings;
- supported API response handling;
- idempotent provisioning;
- reconciliation of partial failures.

### 14.2 UI tests

- global navigation;
- Project switching;
- every Project capability;
- language switching;
- role-dependent visibility;
- empty/loading/error states;
- responsive behavior.

### 14.3 Regression tests

- MQTT ingestion remains unchanged;
- ThingsBoard telemetry remains available;
- alarms continue processing;
- Grafana infrastructure queries return equivalent values;
- SSO login and logout;
- break-glass access;
- backups and restore.

### 14.4 Security tests

- horizontal Project access;
- direct object reference substitution;
- dashboard-variable tampering;
- engine deep-link access;
- role escalation;
- token leakage;
- redirect validation;
- session expiry.

### 14.5 Evidence

For every phase retain:

- commit SHA;
- image digest;
- test output;
- screenshots;
- affected files;
- configuration diff;
- deployment timestamp;
- rollback identifier;
- owner acceptance.

---

## 15. Deployment and rollback

### 15.1 Environments

- v1 production remains operational during v2 development.
- v2 is deployed to staging under separate, clearly marked endpoints.
- staging uses representative Projects and test identities.
- production data must not be copied to staging without approved sanitization.

### 15.2 Release procedure

```text
Build immutable images
→ deploy staging
→ automated tests
→ isolation tests
→ owner browser walk
→ release evidence
→ final production snapshot
→ controlled maintenance window
→ deploy v2
→ reconcile mappings
→ production smoke tests
→ GO or rollback
```

### 15.3 Rollback

Rollback must restore:

- previous application images by digest;
- compatible database state where migrations are not backward compatible;
- previous routing;
- previous Keycloak configuration where changed;
- previous dashboard provisioning.

Database migrations must be backward compatible where possible. Any irreversible migration requires a verified restore rehearsal and explicit approval.

---

## 16. Claude Code execution protocol

Claude Code must work in bounded stages:

1. **Discover** — inspect and report; no edits or deployment.
2. **Design** — propose exact files, interfaces, risks and rollback.
3. **Approve** — wait for owner authorization.
4. **Implement locally** — make only approved changes.
5. **Verify** — run relevant tests and inspect diffs.
6. **Commit** — use the `chertsa` Git identity and a scoped commit.
7. **Deploy staging** — never production first.
8. **Prove** — provide evidence, including negative isolation tests.
9. **Owner acceptance** — wait for explicit GO.
10. **Deploy production** — deploy immutable approved artifacts.
11. **Post-verify** — validate SSO, Project access, telemetry and monitoring.

Claude Code must stop and ask when:

- actual architecture contradicts this document;
- a supported API is absent;
- a migration may be destructive;
- an engine’s license or edition blocks a requirement;
- Project isolation cannot be enforced server-side;
- unrelated dirty changes overlap the approved files;
- staging does not reproduce the needed integration;
- rollback cannot be proven.

---

## 17. Definition of done

CHERT IoT v2 is complete only when:

- users enter one CHERT IoT product;
- Project is the visible backbone;
- all capabilities retain Project context;
- engine names are implementation details in normal student flows;
- ThingsBoard devices and telemetry are correctly Project-scoped;
- Grafana Project monitoring is isolated;
- platform monitoring is administrator-only;
- SSO is seamless;
- English and Arabic LTR are complete;
- the UI follows the CHERT design system;
- negative cross-Project tests pass;
- v1 remains an independently restorable frozen baseline;
- deployment and rollback evidence is complete.

---

## 18. Required owner decisions before implementation

1. Approve the version name **CHERT IoT v2 — Unified Project-Centric Platform**.
2. Approve the v1 freeze tag and v2 branch names.
3. Confirm whether instructors may view all Projects within their assigned cohort.
4. Confirm who may access platform monitoring.
5. Confirm which roles may acknowledge alerts and send device commands.
6. Confirm whether Project members may invite other members.
7. Confirm retention/export rules for telemetry and reports.
8. Approve the exact CHERT design tokens and official logo asset set.
9. Approve the maintenance window and rollback authority.

Until these decisions are recorded, Claude Code may perform discovery and prepare designs, but must not implement ambiguous authorization behavior.

