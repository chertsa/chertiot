# UAT v1.1 — checklist (production, https://chertiot.com)

Logins in `docs/uat/UAT-CREDENTIALS.md`. Tick as you go; note failures inline.

## Access & portfolio
- [ ] chertiot.com loads; **Sign in** → Keycloak → back to the portal
- [ ] Alice's portfolio shows a summary strip + 2 project cards (owner + member), with status dots
- [ ] Language toggle (EN/AR) works on the portal

## Project workspace & live data (Alice / Greenhouse Monitor)
- [ ] Dashboard KPIs populate: 2 devices, 2 online, fleet %, 0 alarms
- [ ] 24-hour chart renders temperature + humidity from seeded history
- [ ] Devices table lists greenhouse-sensor + water-tank with readings + last-seen
- [ ] **Report** page: lifecycle header, KPIs, device roster, alarm history, chart
- [ ] Device detail: connection snippet shown; token rotate works
- [ ] Alerts: seeded `temperature > 30` rule present; can add + delete a rule

## Collaboration
- [ ] Alice sees a **pending join request from Dave** → Approve works
- [ ] Alice sees a **pending invite to Carol** with a shareable link
- [ ] Bob (member) sees the same Greenhouse data but **no** Members panel
- [ ] Carol's invite **auto-accepted on login** → Greenhouse appears in her portfolio
- [ ] Dave (after approval) sees Greenhouse in his portfolio
- [ ] Owner can **Disable** a member (member then blocked) and **Enable** again
- [ ] Owner can **Remove** a member (project leaves their portfolio)

## Isolation
- [ ] A device added in one project is **not** visible in another project
- [ ] A non-member opening a project link sees a **Request to join** page, not the data

## Create a new project (finale)
- [ ] **+ New project** creates a provisioned workspace
- [ ] Add a device; publish MQTT to chertiot.com:8883 with its token; it goes **online** on the dashboard
- [ ] Invite a member; add an alert; open the report

## Sign-out
- [ ] Sign out returns to the public site, fully logged out (no residual session)

## Known scope (not defects)
- [ ] Notebooks/Lab not enabled on this host yet (LAB_ENABLED=false)
- [ ] Water Utility 24h chart empty by design (level/flow, not temp/humidity)
- [ ] Full TB-console deep-link for members deferred
