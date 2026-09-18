# ADR-001 — Project-centric platform (CHERT IoT is a platform, not a showroom)

**Status:** PROPOSED — v1.1 line (frozen baseline: git tag **v1.7.0**). Blocked on the tenancy
decision (see §Collaboration) before any M5.1 build.
**Date:** 2026-09-18 · **Author:** Claude (Opus 4.8), with owner.
**Owner decisions captured this session:** per-project Node-RED + Jupyter · **fresh rebuild** (build
phase — reset data, no migration/backfill) · **+ collaboration** (owner/members, invite, request-to-
join, enable/disable). Customer-per-project (D13) is **reopened** by collaboration — see §Collaboration.

## Context
Today everything hangs directly off the user: `PortalUser → one TB tenant`, and `FlowInstance`,
`AlertRule`, `LoraDevice` are all keyed by `user_id`. The home page is a grid of tool links, so the
product reads as a **showroom of open-source engines** rather than a place to **build IoT projects**.

Owner direction: make **Project** the backbone. Sign in → create a project → inside it create/register
devices and use the tools *as project capabilities*. A project is a **closed environment** of devices +
code + data + dashboards. One user → many projects; one project → many devices.

## Decision
Introduce **Project** as the first-class entity between the user and everything else. Each engine we
already run has a native per-project container, so a project is real isolation in every system — not a
portal-only fiction.

| Layer | Today (per user) | Target (per **project**) |
|---|---|---|
| Portal | — | **`Project`** row (name, slug, description, **status/lifecycle**, owner, links to each engine's per-project id) — source of truth |
| ThingsBoard | tenant per user; flat devices | user stays the **tenant**; **project = a TB Customer** owned by the tenant admin; devices assigned to it; a **per-project dashboard** assigned to the customer |
| LoRa (ChirpStack) | devices under user | **project = a ChirpStack Application** |
| Node-RED | one instance per user | **one instance per project** (`nodered-<project_id>`), MQTT-scoped to that project's devices |
| Jupyter | one server per user | **JupyterHub named-server per project** |
| Alerts | `AlertRule(user_id,…)` | `AlertRule(project_id,…)` |

**Home** becomes a **Projects portfolio** (cards: device count, online, alarms, last activity, status;
"New project"; a portfolio lifecycle/report view). A project opens into its scoped workspace —
Devices · Flows · Notebook · Alerts · LoRa · Dashboard — every view pre-filtered to the project. The
open-source "Explore the lab" page survives but is **demoted** to a secondary "what powers this" page.

## Relationship to the frozen decisions (D1–D12)
- **D4 (one tenant per student; never customer-per-student — CE customers are read-only):** UPHELD.
  We keep one tenant per student and the student stays **Tenant Admin**. D4's "read-only" concern is
  about **Customer *Users*** (a restricted login); we create **no customer users**. A project is a
  **Customer entity used purely as a grouping**, created and fully controlled by the tenant admin.
- **New → D13 (proposed):** *"Project = a TB Customer within the student's own tenant, used for
  device grouping and a per-project dashboard. The student remains Tenant Admin; no customer-users are
  created. Portal `Project` is the source of truth and mirrors to the TB Customer, a ChirpStack
  Application, a per-project Node-RED instance, and a Jupyter named-server."*
  ⚠️ **Reopened by collaboration (see §Collaboration).** Multi-user projects mean a member is a
  *different* user in a *different* TB tenant, which a Customer inside the owner's tenant cannot serve.
  D13 must be settled together with the collaboration tenancy question **before** M5.1 build.
- **D2/D7/D10** unchanged: no engine changes; portal↔TB stays REST-only via `tb_client.py`; branded
  images untouched. This is portal + provisioning + UX work.

## Data model (portal, SQLAlchemy + Alembic)
- **New `Project`**: `id, user_id(fk), name, slug, description, status(active|paused|archived),
  tb_customer_id, chirpstack_application_id, created_at, archived_at`.
- **Re-grain** (fresh rebuild — replace, don't migrate):
  - `FlowInstance`: PK/owner `project_id` (container `nodered-<project_id>`); drop the per-user grain.
  - `AlertRule`: `project_id` replaces `user_id`.
  - `LoraDevice`: add `project_id`.
- Devices themselves stay in TB (D10); the portal reads them via a **customer-scoped** query. A thin
  cache table is added only if query cost demands it (decide during the M5.1 spike).

## Provisioning (idempotent, sysadmin-impersonation per D10/`as_student`)
- **On user signup:** provision the tenant as today, **minus** the flat starter content; create nothing
  project-specific until the first project.
- **On project create:** ① TB **Customer** (title `proj:<slug>`) under the tenant; ② copy the starter
  dashboard **assigned to that customer** (D5 pattern, per-project); ③ ChirpStack **Application** (if
  `LORA_ENABLED`); ④ lazily spawn Node-RED on first Flows open; ⑤ Jupyter named-server on first Lab open.
- **On device create:** create in the tenant, **assign to the project's Customer**; token issued as today.
- **On project archive/delete:** unassign/delete customer + dashboard, delete ChirpStack app, stop +
  remove the Node-RED instance (volume too, on delete), stop the named-server. All idempotent.

## `tb_client.py` additions (REST only)
Customer CRUD; assign/unassign device ↔ customer; assign dashboard ↔ customer; **customer-scoped Entity
Data Query** (the one real spike — confirm the CE query shape that filters devices by `customerId`;
fall back to selecting the `customerId` field and filtering in the portal if needed).

## Fresh-rebuild strategy (owner-approved; build phase)
No backfill. Sequenced, **staging first**: reset the portal DB (new baseline Alembic revision), wipe
test tenants/data in TB + ChirpStack, redeploy, re-provision, and reseed a **demo *project*** (replacing
the current demo tenant). Prod reset only after staging is green end-to-end.

## Phased delivery (each phase: staging → verify → prod)
- **M5.1 — Backbone.** `Project` model + Alembic baseline; Project CRUD; Projects home + workspace shell;
  TB Customer per project; device create/list scoped to the customer; per-project dashboard + SSO open.
  *Accept:* create 2 projects, add devices to each, see them isolated, open each project's dashboard.
- **M5.2 — Flows per project.** Node-RED instance per project; forward_auth by project ownership;
  MQTT token scoped to the project. *Accept:* each project's editor is separate; cross-project denied.
- **M5.3 — Alerts + Notebooks per project.** `AlertRule(project_id)`; Jupyter named-server per project.
  *Accept:* alerts fire only for the project's devices; each project has its own notebook workspace.
- **M5.4 — LoRa per project.** ChirpStack Application per project; register LoRa devices into it.
  *Accept:* uplink from a project's LoRa device lands only on that project's dashboard.
- **M5.5 — Lifecycle & reports.** Portfolio dashboard + per-project lifecycle/report view (devices,
  uptime, message volume, alarms, activity timeline). Demote the showroom to "Explore the stack".
- **M5.6 — Collaboration.** Owner/members, invite by email, request-to-join + approval, enable/disable
  members — implemented per the tenancy option chosen above.
- **M5.7 — Fresh reset + demo project.** Prod reset, reseed the demo *project*, docs/UAT refresh.

## Collaboration & membership (v1.1 — owner-added 2026-09-18)
Requirements: a project has an **owner** and **members**; a user can **invite** others to a project;
users can **request to join** a project; the owner can **disable/enable** members.

**Portal model (additive):**
- `ProjectMember(project_id, user_id, role: owner|member, status: active|disabled, added_at)`.
- `ProjectInvite(id, project_id, invited_email, token, status: pending|accepted|revoked, created_at)`
  — invite by email; on accept the invitee (existing or new signup) becomes a `member`.
- `ProjectJoinRequest(id, project_id, user_id, status: pending|approved|denied, created_at)` — the
  owner approves/denies; approval creates a `ProjectMember`.
- Enable/disable flips `ProjectMember.status`; disabled members lose access immediately (portal gate +
  revoke the engine-side grant).

**⚠️ Tenancy decision this forces (must resolve before M5.1):** members are separate TB tenants, and
TB CE tenants are isolated — so a project shared across users **cannot** be a Customer inside one
owner's personal tenant (breaks D13 as written). Options:
1. **Project = its own TB tenant** (shared project tenant); members are users *in that tenant* (scoped
   roles). Abandons "Customer per project"; needs a way to make one portal user an admin/member across
   several tenants (today's OAuth2 mapper is tenant-per-email — this is the main spike).
2. **Portal-mediated access:** project data stays in the owner's tenant; members never log into TB
   directly — the portal renders everything (dashboards, devices, flows) on their behalf via the
   owner's tenant using impersonation, gated by `ProjectMember`. Keeps D13; loses direct TB SSO for
   members; heavier portal rendering.
3. **Hybrid:** solo projects = Customer in the owner's tenant (D13); the moment a project gains a 2nd
   member it is promoted to a shared project tenant (option 1). Most flexible, most work.

Recommendation to be finalized with the owner + a spike; my lean is **Option 1 (project = tenant)** for
a clean, collaborative-by-design model, accepting the multi-tenant-per-user auth spike. This may
supersede D13 (project = tenant, not customer). **No build until this is chosen.**

## Risks / open items
- **Customer-scoped Entity Data Query in CE** — the one thing to prove in an M5.1 spike before building
  on it (portal filtering is the fallback).
- **Instance sprawl** — per-project Node-RED/named-servers multiply with projects; the 30-min idle
  culler keeps only *active* ones running, and capacity stays governed by concurrent-open, not totals.
- **Naming/URLs** — project-scoped paths (`/projects/<id>/…`, Node-RED `/p/<project_id>/`); settle in M5.1.

## Approval requested (next)
1. **Choose the tenancy model** for projects given collaboration: Option 1 (project = tenant,
   supersedes D13) / Option 2 (portal-mediated, keeps D13) / Option 3 (hybrid). My lean: Option 1.
2. After that, record the final decision (D13 or its replacement) and green-light **Phase M5.1**.
