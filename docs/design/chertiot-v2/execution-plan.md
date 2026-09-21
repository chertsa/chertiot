# CHERT IoT v2 — execution plan

**Status:** ACTIVE. Owner approved starting Phase 0 (2026-09-21).
**Branch:** `release/chertiot-v2-unified`, cut from the frozen v1 code baseline
(`chertiot-v1-as-is-final` → `9a02579`; branch created from `main`, whose code tree is identical to
that commit — only docs were added since).
**Basis:** `engineering-review.md` + `project-monitoring-design.md` (both approved).

## Governance (every phase)
- **Prod stays on frozen v1** until one final cutover. **Staging is the v2 preview.**
- **Feature-flagged:** each new capability ships dark (`app/features.py` + a `Settings` flag), enabled
  staging-first.
- **Staging-first + isolation tests:** each phase passes functional **and** negative cross-project
  tests before the next. Any cross-project disclosure is a release blocker.
- **Reuse, don't rebuild:** the portal already implements Devices/Flows/LoRa/Alerts/Lab/Report/
  Members as `/projects/{id}/…`, server-side membership-gated. v2 finishes the shell.
- **Rollback:** additive; final cutover rolls back by image digest to the v1 tag.

## Phases & exit gates

| Phase | Delivers | Exit gate |
|---|---|---|
| **0 Foundation** | v2 branch; security-headers/CSP middleware (`default-src 'self'`, zero external subresources; inline script/style permitted interim); feature-flag scaffolding (`app/features.py`, `MONITORING_ENABLED`); status design tokens (`--chert-ok/warn/crit`); this plan. | Shell + SSO + project selection work on staging; existing tests green; no regressions; CSP header present. |
| **1 Unified nav + Overview** (V2.1) | shared `_project_nav.html` (Overview·Devices·Telemetry·Monitoring·Alerts·Flows·LoRaWAN·Notebooks·Settings) + project header (slug reference, never `tb_tenant_id`); `/projects/{id}` redesigned into an Overview with an at-a-glance mini-monitoring panel. | Every capability page shares the shell; Overview renders; isolation intact. |
| **2 Project Monitoring** (V2.3) | the fully-designed capability: `GET …/monitoring`, `…/monitoring/data`, `POST …/alarms/{id}/ack`; device+numeric-key selector; typed `MonitoringSnapshot`; polling+cache; all states; role gating; audit; **§20 negative matrix**. Grafana stays platform-only, admin-only. | **Blocking spike first:** verify TB tenant-scoped alarm-read endpoint (404/403 out-of-tenant) before ack. §20 matrix passes; KPIs/charts match TB; offline/no-external holds. |
| **3 Telemetry + isolation hardening** (V2.2) | portal-native Telemetry tab (device/key/range) reusing the monitoring data layer; add negative-isolation tests for devices/alerts/lora/report/members. | Positive + negative device/telemetry isolation pass. |
| **4 Role model** | persisted roles/permissions (member/owner/instructor/platform-admin) per the approved matrix; Keycloak→Grafana role mapping; platform-Grafana admin-only; **resolves instructor/admin tenant-session** with its own security review. | Role + break-glass audited tests green. |
| **5 Visual system** | CHERT design tokens across the portal + Grafana theme (visual-only, query-equivalence tested). | Consistent look; no behavior/data change. |
| **6 Release candidate** (V2.6) | accessibility, responsive, EN/AR-LTR coverage, performance, security review, restore rehearsal, owner browser acceptance. | Signed GO. |
| **Cutover** | prod snapshot → maintenance window → deploy v2 images → reconcile mappings → smoke → GO/rollback by digest. | Production on v2, rollback proven. |

## Known items resolved in-phase
- TB alarm-read endpoint spike — Phase 2 (blocks ack).
- Instructor/admin tenant-session resolution — Phase 4 (until then, active `ProjectMember`s only).

## Phase 0 deliverables (this commit)
- `release/chertiot-v2-unified` branch off the frozen baseline.
- Security-headers/CSP middleware in `portal/app/main.py` (zero external runtime assets, interim
  inline allowance documented; the external-asset guard test already enforces no external refs).
- Feature-flag scaffolding: `portal/app/features.py` (`features` in templates), `Settings.monitoring_enabled`,
  `MONITORING_ENABLED` in `.env.example`.
- Status design-token aliases in `portal/app/static/chert-tokens.css`.
- This execution plan.
Behavior-identical to v1 (CSP + inert flags only); deployed to staging as the v2 baseline.
