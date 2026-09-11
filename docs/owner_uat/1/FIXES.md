# Owner UAT round 1 — findings & fixes

Owner ran a manual walkthrough on production (2026-09-11) and reported errors. All are fixed,
deployed **staging → production**, and verified.

| # | Reported | Root cause | Fix | Verified |
|---|----------|-----------|-----|----------|
| 1 | **Flows → "Open the editor" → HTTP ERROR 401** | The portal session cookie was host-only to `chertiot.com`, so the browser never sent it to `flows.chertiot.com`; Caddy `forward_auth` (`/flows/auth`) saw no session → 401. | Session cookie scoped to the parent domain (`domain=.chertiot.com`, env≠dev) in `app/main.py`. | End-to-end on prod: OIDC login → cookie `.chertiot.com` → `/flows/auth` = **200**, editor loads **200** (was 401). |
| 2 | **`app.chertiot.com/login` → password → "User account is not active"** | Students are **SSO-only** (D3): TB holds no password, so its native login form always fails. The SSO button was also mislabeled **"Sign in with Sign in with CHERT IoT"** (TB prepends "Sign in with " to the label). | (a) Button label → `CHERT IoT` (now reads "Sign in with CHERT IoT"). (b) **"Open my dashboard"** now routes through TB's OAuth2 authorization URL (Keycloak SSO) instead of the TB login form — one click, no password prompt. | `noauth/oauth2Clients` name = "CHERT IoT"; dashboard link resolves to `…/oauth2/authorization/…`. |
| 3 | **Getting started → `chertiot.com/docs` → `{"detail":"Not Found"}`** | `/docs` (no trailing slash) fell through to the portal (FastAPI) → 404; only `/docs/*` was proxied to the docs site. | Caddy `redir /docs /docs/ 308`; portal links point to `/docs/`. | `/docs` → **308** → `/docs/` → **200**. |

## Worked correctly during the walkthrough (no change needed)
- Devices: add device, access token, starter code (ESP32/RPi/browser), 1/10 quota display.
- LoRaWAN: device registration returned a DevEUI + AppKey (`lora-a9fda5`).
- Alerts: threshold rule created (device → condition → email/alarm action).

## Known, by design (not a bug)
Typing a username/password on TB's own login page will always fail — students authenticate only
through **"Sign in with CHERT IoT"** (Keycloak SSO). With fix #2 the primary path never shows that
form. Fully hiding TB's basic-auth form is a TB customization (BACKLOG) if desired.

## Deploy
Commit `04db495` (+ CLAUDE.md gotcha). Staging first, then production; both green; core endpoints
(portal, TB, flows, lab, docs, status) all 200. Re-run `scripts.setup_tb_oauth2` applied the label
on both servers.

**Please re-run the browser walkthrough** with `docs/uat/UAT-CHECKLIST.md` — the three failing
steps should now pass.
