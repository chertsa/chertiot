# ADR-001 — Project-centric platform (CHERT IoT is a platform, not a showroom)

**Status:** ACCEPTED (v1.1 line; frozen baseline git tag **v1.7.0**). Tenancy resolved: **Project =
TB Tenant** (D13). Building **M5.1** next.
**Date:** 2026-09-18 · **Author:** Claude (Opus 4.8), with owner.
**Owner decisions captured this session:** **Project = TB Tenant** (supersedes D4 tenant-per-student
and the draft Customer-per-project) · per-project Node-RED + Jupyter · **fresh rebuild** (build phase —
reset data, no migration/backfill) · **collaboration** (owner/members, invite, request-to-join,
enable/disable) · not in production yet, so no staging-gate ceremony — but **no workarounds/temp fixes**.

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
| ThingsBoard | tenant per user; flat devices | **project = a TB Tenant**; owner + members are **Tenant Admin users** in it (full rights, native isolation); the portal brokers per-project sessions via sysadmin impersonation tokens |
| LoRa (ChirpStack) | devices under user | **project = a ChirpStack Application** |
| Node-RED | one instance per user | **one instance per project** (`nodered-<project_id>`), MQTT-scoped to that project's devices |
| Jupyter | one server per user | **JupyterHub named-server per project** |
| Alerts | `AlertRule(user_id,…)` | `AlertRule(project_id,…)` |

**Home** becomes a **Projects portfolio** (cards: device count, online, alarms, last activity, status;
"New project"; a portfolio lifecycle/report view). A project opens into its scoped workspace —
Devices · Flows · Notebook · Alerts · LoRa · Dashboard — every view pre-filtered to the project. The
open-source "Explore the lab" page survives but is **demoted** to a secondary "what powers this" page.

## Relationship to the frozen decisions (D1–D12) — amended for collaboration
Collaboration (owner + members with full rights, shared across users) can only be served the standard
TB way by a **shared tenant per project**. This supersedes D4 and the first draft of D13:
- **D4 (one tenant per student):** **SUPERSEDED** → *one tenant per **project***. A user no longer has
  a personal tenant; they get Tenant-Admin membership in the tenants of the projects they own or join.
  D4's original goal (every builder is a full-rights Tenant Admin, never a read-only customer-user) is
  **preserved and extended** — now to every project member.
- **D13 (final form):** *"Project = a TB **Tenant**. Owner and members are **Tenant Admin** users
  within it (full rights; projects natively isolated). One human = one Keycloak identity mapped to one
  TB user per project-tenant they belong to. The portal is the identity broker: it creates/removes
  those TB users as membership changes and issues per-project TB sessions via sysadmin impersonation
  (`GET /user/{id}/token`, `user_token_access_enabled=true`). Portal `Project` is the source of truth
  and mirrors to the TB Tenant, a ChirpStack Application, a per-project Node-RED instance, and a
  Jupyter named-server. No TB Customers, no customer-users."*
- **D2/D7/D10** unchanged: no engine changes; portal↔TB stays REST-only via `tb_client.py`; branded
  images untouched. This is portal + provisioning + UX work.

## Data model (portal, SQLAlchemy + Alembic)
- **New `Project`**: `id, slug, name, description, status(active|paused|archived), tb_tenant_id,
  chirpstack_application_id, created_at, archived_at`. (No single `user_id` — ownership/membership is
  in `ProjectMember`.)
- **`ProjectMember`**: `project_id, user_id, role(owner|member), tb_user_id, status(active|disabled),
  added_at` — the TB Tenant-Admin user for that human in that project-tenant.
- **`ProjectInvite`** / **`ProjectJoinRequest`**: see §Collaboration.
- **Re-grain** (fresh rebuild — replace, don't migrate):
  - `FlowInstance`: owner `project_id` (container `nodered-<project_id>`); drop the per-user grain.
  - `AlertRule`: `project_id` replaces `user_id`.
  - `LoraDevice`: add `project_id`.
- Devices live in the **project-tenant** (D10); the portal reads them with an ordinary tenant-scoped
  Entity Data Query using the acting member's TB session — no customer filtering needed (isolation is
  the tenant boundary).

## Provisioning (idempotent, sysadmin-impersonation per D10)
- **On user signup:** create the Keycloak identity + portal user only. **No TB tenant** until they own
  or join a project.
- **On project create:** ① create a TB **Tenant** (name `proj:<slug>`) + apply the student tenant
  profile (quotas); ② create the creator as a **Tenant Admin** user in it, record `tb_user_id`, and add
  a `ProjectMember(role=owner)`; ③ copy the starter dashboard into that tenant (D5 pattern);
  ④ ChirpStack **Application** (if `LORA_ENABLED`); ⑤ Node-RED spawned lazily on first Flows open;
  ⑥ Jupyter named-server on first Lab open.
- **On add member (invite accept / join approve):** create their Tenant-Admin user in the project-tenant,
  record `tb_user_id`, add `ProjectMember(role=member)`.
- **On device create:** create in the project-tenant using the acting member's session; token as today.
- **On disable/enable member:** disable/enable (or delete/recreate) their TB user in the project-tenant.
- **On project archive/delete:** delete the ChirpStack app, stop+remove the Node-RED instance (volume on
  delete), stop the named-server, and delete the TB Tenant (on delete). All idempotent.

## `tb_client.py` additions (REST only)
Tenant CRUD + tenant-profile apply; Tenant-Admin **user** CRUD within a tenant; **impersonation-session
broker** (`GET /user/{id}/token`) to open a project for a member. The one spike: confirm TB CE's native
"act-as / login-as-user" token-consumption flow (the mechanism behind D6) so the browser lands in the
project-tenant UI via that token — the standard path, no localStorage hacks.

## Fresh-rebuild strategy (owner-approved; build phase)
No backfill. Sequenced, **staging first**: reset the portal DB (new baseline Alembic revision), wipe
test tenants/data in TB + ChirpStack, redeploy, re-provision, and reseed a **demo *project*** (replacing
the current demo tenant). Prod reset only after staging is green end-to-end.

## Phased delivery (each phase: staging → verify → prod)
- **M5.1 — Backbone. ✅ DONE (staging, 2026-09-18).** `Project`/`ProjectMember` + Alembic 0005; Project
  CRUD; projects portfolio home + workspace; **TB tenant per project** (D13); device + tools scoped to
  `/projects/{id}/…`; portal-rendered per-project dashboard. E2E verified on staging: 2 isolated
  tenants, device isolation, MQTT ingest, dashboard/quota.
- **M5.2 — Flows per project.** Node-RED instance per project; forward_auth by project ownership;
  MQTT token scoped to the project. *Accept:* each project's editor is separate; cross-project denied.
- **M5.3 — Alerts + Notebooks per project.** `AlertRule(project_id)`; Jupyter named-server per project.
  *Accept:* alerts fire only for the project's devices; each project has its own notebook workspace.
- **M5.4 — LoRa per project.** ChirpStack Application per project; register LoRa devices into it.
  *Accept:* uplink from a project's LoRa device lands only on that project's dashboard.
- **M5.5 — Lifecycle & reports.** Portfolio dashboard + per-project lifecycle/report view (devices,
  uptime, message volume, alarms, activity timeline). Demote the showroom to "Explore the stack".
- **M5.6 — Collaboration. ✅ DONE (staging, 2026-09-18).** Owner/members, link-based invites (+auto-
  accept on login), request-to-join + approve/deny, enable/disable/remove. Members are Tenant-Admins of
  the shared project tenant. E2E verified on staging. (Email delivery of invites = later; links for now.)
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

**Tenancy decision — RESOLVED (2026-09-18): Project = TB Tenant** (D13 final form above). Members are
Tenant-Admin users in the project-tenant; the portal brokers their sessions via sysadmin impersonation.
This is the native TB model for a shared, full-rights, isolated environment — chosen over
customer-in-owner-tenant (can't serve members) and portal-only rendering (a workaround) per the
no-workarounds policy. The only spike is the CE act-as-user token-consumption flow (§tb_client).

## Risks / open items
- **Customer-scoped Entity Data Query in CE** — the one thing to prove in an M5.1 spike before building
  on it (portal filtering is the fallback).
- **Instance sprawl** — per-project Node-RED/named-servers multiply with projects; the 30-min idle
  culler keeps only *active* ones running, and capacity stays governed by concurrent-open, not totals.
- **Naming/URLs** — project-scoped paths (`/projects/<id>/…`, Node-RED `/p/<project_id>/`); settle in M5.1.

## Next
Start **M5.1 backbone** on the Project = Tenant model, beginning with the act-as-user token spike
(prove the CE flow) before wiring provisioning + UX. Fresh rebuild throughout; no production gate.
