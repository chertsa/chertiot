# CHERT IoT — UAT Checklist

User-acceptance test script for **<https://chertiot.com>** (production). Work top to bottom;
tick each row as **Pass / Fail** and note anything odd. Logins and URLs are in the local
`UAT-CREDENTIALS.md` (not in git). Use a plain student account unless a step says otherwise.

- **Env:** production · **Tester:** ______________ · **Date:** ____________ · **Build:** v1.6.0
- Legend: ☐ not run · ✅ pass · ❌ fail (add a note)

---

## 0. Access & identity (Phase 0–1)

| # | Step | Expected | Result |
|---|------|----------|--------|
| 0.1 | Open <https://chertiot.com> | Portal home loads over HTTPS (valid cert) | ☐ |
| 0.2 | Click **Sign in**, log in as **Student 1** | Keycloak login → lands back in the portal, signed in | ☐ |
| 0.3 | From the portal, open **My dashboard** (ThingsBoard) | Opens ThingsBoard **without a second login** (SSO) | ☐ |
| 0.4 | Confirm tenant identity in ThingsBoard | You are **Tenant Admin of your own tenant** (only your devices visible) | ☐ |
| 0.5 | Sign out, sign back in | Clean logout and re-login; no error loop | ☐ |

## 1. Signup & verification (real flow)

| # | Step | Expected | Result |
|---|------|----------|--------|
| 1.1 | Go to `/signup`, register a **new** email you control | Form requires **age attestation**; accepts optional class code | ☐ |
| 1.2 | Enter class code `UAT-E620` during signup | Account is tagged into the `uat-class` cohort | ☐ |
| 1.3 | Check inbox → click the verification link | Keycloak confirms → returns to portal ("verified — sign in") | ☐ |
| 1.4 | Sign in with the new account | Auto-provisioned: own tenant + starter device + starter dashboard exist | ☐ |
| 1.5 | Try signing up 6× quickly from one browser | Rate limit (5/hour/IP) kicks in | ☐ |

## 2. Devices & telemetry (Phase 1)

| # | Step | Expected | Result |
|---|------|----------|--------|
| 2.1 | Open **My Devices** | Starter device listed with last-seen / online state | ☐ |
| 2.2 | **Add a device** (name it) | Device created; access token shown | ☐ |
| 2.3 | Open the device page → copy a **firmware snippet** (e.g. ESP32 or RPi) | Token, broker host/port, device name are pre-filled | ☐ |
| 2.4 | Publish telemetry over **MQTTS 8883** using the token (snippet or `mosquitto_pub`) | Message accepted; appears in the dashboard within seconds | ☐ |
| 2.5 | **Issue new token** on the device | Old token stops working immediately; new one works | ☐ |
| 2.6 | Try to add an **11th device** | Blocked by the 10-device quota | ☐ |
| 2.7 | Rename, then delete a device | Both succeed; dashboard updates | ☐ |

## 3. Dashboards (Phase 1)

| # | Step | Expected | Result |
|---|------|----------|--------|
| 3.1 | Open the starter **"My devices"** dashboard | Live charts render for your device(s) | ☐ |
| 3.2 | Edit a widget, save | Change persists (it's your tenant) | ☐ |
| 3.3 | Use **Reset starter dashboard** | Pristine template re-imported; devices & data untouched | ☐ |

## 4. Isolation & limits (Phase 1)

| # | Step | Expected | Result |
|---|------|----------|--------|
| 4.1 | As **Student 1**, note a device token; as **Student 2**, try to read Student 1's tenant/devices | **Denied** — no cross-tenant visibility | ☐ |
| 4.2 | Publish a rapid burst (>10 msg/s) from one device | Excess throttled; device may be disconnected; neighbours unaffected | ☐ |

## 5. Node-RED flows — `/flows` (Phase 3, M3.1)

| # | Step | Expected | Result |
|---|------|----------|--------|
| 5.1 | Open **Flows** from the portal | Your Node-RED editor loads (spawns on first use) | ☐ |
| 5.2 | Build a small flow (inject → debug), deploy | Runs; debug shows output | ☐ |
| 5.3 | Copy your flows URL, open it **while logged in as another user** | **403** — you can't reach someone else's editor | ☐ |
| 5.4 | Leave idle ~30 min, return | Instance was culled and respawns cleanly | ☐ |

## 6. JupyterHub lab — `lab.chertiot.com` (Phase 3, M3.2)

| # | Step | Expected | Result |
|---|------|----------|--------|
| 6.1 | Open <https://lab.chertiot.com> | Login via the same SSO (no new account) | ☐ |
| 6.2 | Start a server, open an example notebook | Notebook runs (pandas/matplotlib available) | ☐ |
| 6.3 | Use `chertiot.py` helper to fetch **your** telemetry and plot it | Chart of your own data renders | ☐ |
| 6.4 | Attempt to query another tenant's data | **Denied** (your JWT only sees your tenant) | ☐ |

## 7. Instructor console — `/teach` (Phase 3, M3.3)

*Log in as the **Instructor** account.*

| # | Step | Expected | Result |
|---|------|----------|--------|
| 7.1 | Open `/teach` | Console loads (student accounts do **not** see it) | ☐ |
| 7.2 | Create a **class code** (set expiry / max uses) | Code created; usable at `/join` | ☐ |
| 7.3 | View the **roster** | Shows last-seen, device counts, message volume — **no** private telemetry | ☐ |
| 7.4 | **Suspend** a student, then have them try to log in | Login blocked (Keycloak-disabled + TB flag) | ☐ |

## 8. Alerts & export (Phase 3, M3.4)

| # | Step | Expected | Result |
|---|------|----------|--------|
| 8.1 | Define a threshold alert (e.g. temp > X) | Rule created on your tenant | ☐ |
| 8.2 | Publish a value that crosses the threshold | Alarm fires; email/webhook received | ☐ |
| 8.3 | Export your telemetry as **CSV** and **JSON** (a time range) | Download streams; scoped to **your** data only | ☐ |
| 8.4 | Try to export another tenant's data | **404 / denied** | ☐ |

## 9. LoRaWAN — `/lora` (Phase 4, M4.1)

| # | Step | Expected | Result |
|---|------|----------|--------|
| 9.1 | Visit `lora.chertiot.com` | Redirects to `chertiot.com/lora` | ☐ |
| 9.2 | Register a LoRa device (DevEUI) via `/lora` | Device created in ChirpStack + your TB tenant | ☐ |
| 9.3 | Send a simulated uplink (or a real gateway uplink) | Decoded telemetry lands on **your** dashboard | ☐ |

## 10. Docs, i18n & status

| # | Step | Expected | Result |
|---|------|----------|--------|
| 10.1 | Open `/docs/` | Getting-started + guides render | ☐ |
| 10.2 | Toggle **Arabic** (portal + `/docs/ar/`) | UI switches to Arabic, right-to-left layout | ☐ |
| 10.3 | Open <https://status.chertiot.com/status/chert-iot> | Public status page shows the monitors up | ☐ |
| 10.4 | Open the **privacy** and **fair-use** pages | Both load, plain-language content | ☐ |

---

## Sign-off

| Area | Pass | Fail | Notes |
|---|---|---|---|
| Identity & signup (0–1) | | | |
| Devices & telemetry (2–4) | | | |
| Flows & lab (5–6) | | | |
| Instructor, alerts, export (7–8) | | | |
| LoRaWAN (9) | | | |
| Docs / i18n / status (10) | | | |

**Overall UAT verdict:** ☐ Accepted ☐ Accepted with notes ☐ Rejected

**Tester signature:** __________________  **Date:** ____________

> Found a bug? Note the step number, the account used, and what you saw vs. expected.
> Reset the UAT accounts anytime by re-running `portal/scripts/seed_uat.py` (idempotent).
