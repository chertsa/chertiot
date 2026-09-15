# CHERT IoT — UAT Plan

**Product:** CHERT IoT (chertiot.com) · **Build:** v1.6.0 · **Phase:** pre-launch UAT
**Environment under test:** production — <https://chertiot.com>

## 1. Purpose
Confirm that a real student/instructor can complete the full journey — sign up, connect a device,
see live data, use the lab tools, and that isolation, alerts and LoRaWAN work — on the production
platform, before public launch.

## 2. Scope
**In scope:** portal (signup, login/SSO, devices, dashboards, flows, lab, alerts, LoRa, instructor
console, sign-out), ThingsBoard tenant isolation, MQTTS telemetry, docs, Arabic/RTL, public status.
**Out of scope this round:** load/performance, penetration testing, billing, mobile-native apps.
**Known-open (don't file as new):** Node-RED favicon still Node-RED's; "Node-RED website" menu link;
ThingsBoard's GitHub "Star" badge and "powered by ThingsBoard" footer (branded-image change pending).

## 3. Environment & data
- Production, real SMTP (SMTP2GO), real TLS, MQTTS on `chertiot.com:8883`.
- Pre-seeded test accounts (see `UAT-CREDENTIALS.md`) — pre-verified & provisioned (own TB tenant +
  starter device + dashboard). Plus one **self-registered** account to exercise the real signup path.
- Test class join code: `UAT-E620`.
- Reset a test account's dashboard anytime with **"Reset starter dashboard"** on the home page.

## 4. Roles
| Role | Who | Uses |
|---|---|---|
| Student | tester | uat.student1 / uat.student2 |
| Instructor | tester | uat.instructor (has `/teach`) |
| Admin/observer | owner | uat.admin + back-office (Keycloak/TB/Grafana/Kuma) |

## 5. Entry criteria
- All public endpoints 200 (portal, app, auth, flows, lab, docs, status) — currently met.
- CI + nightly green — currently met.
- Test accounts log in — verified 2026-09-15.

## 6. Exit / acceptance criteria
- **Must pass (blockers):** signup+verify, SSO login, device create + MQTTS telemetry visible,
  dashboard renders (no widget errors), tenant isolation holds, sign-out fully logs out,
  alerts fire, CSV/JSON export scoped to owner.
- **Should pass:** Node-RED editor stays connected, JupyterHub notebook plots own data,
  instructor roster + suspend, LoRa register → uplink on dashboard, Arabic/RTL on all pages.
- **Verdict:** Accepted / Accepted-with-notes / Rejected, recorded on the checklist.

## 7. Execution
Work through **`UAT-CHECKLIST.md`** top to bottom per role; mark Pass/Fail with notes. Capture a
screenshot for any failure. Aim: a fresh student reaches live data in **under 10 minutes** using
only the docs.

## 8. Defect handling
Log each defect with: checklist step #, account used, URL, what you saw vs expected, screenshot.
Drop the notes + screenshots into a `docs/owner_uat/<round>/` folder (as in rounds 1–3); I fix,
deploy staging→production, verify, and reply with a fix report.

- **Severity 1 (blocker):** journey cannot complete (e.g. can't log in, no telemetry) — fix now.
- **Severity 2 (major):** feature broken but has a workaround — fix this round.
- **Severity 3 (minor/cosmetic):** wording, branding, layout — batch.

## 9. Schedule
Single focused pass now; re-test of any fixes same day. Rotate all test-account passwords before
public launch (owner task).

## 10. History
- Round 1 — flows 401, TB login UX, /docs 404 → fixed.
- Round 2 — sign-out invalid-redirect + stale cookie → fixed.
- Round 3 — dashboard widget error, flows "lost connection", full Arabic, footers/links, CHERT Node → fixed.
