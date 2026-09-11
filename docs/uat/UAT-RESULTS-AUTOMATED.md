# CHERT IoT — Automated UAT Results

Machine-verifiable UAT checks run against **production** (real external device path).

- **Run:** 2026-09-11 00:44 UTC · **Env:** <https://chertiot.com> · **Result:** 13/13 passed

| Check | Result | Detail |
|---|---|---|
| 10 portal healthz | ✅ PASS | HTTP 200 |
| 10 docs EN | ✅ PASS | HTTP 200 |
| 10 docs AR | ✅ PASS | HTTP 200 |
| 10 status page | ✅ PASS | HTTP 200 |
| 9.1 lora redirect | ✅ PASS | HTTP 200 |
| 0 OIDC discovery | ✅ PASS | HTTP 200 |
| 0.4 TB sysadmin login | ✅ PASS |  |
| 0.4 impersonate student1 | ✅ PASS |  |
| 2.1 starter device present | ✅ PASS | my-first-device |
| 2.4a MQTTS 8883 connect (TLS, token auth) | ✅ PASS | rc=Success |
| 2.4b telemetry visible via TB REST | ✅ PASS | sent 453.875, read 453.875 |
| 4.1 cross-tenant device read denied | ✅ PASS | HTTP 404 |
| 1.4 UAT accounts enabled+verified | ✅ PASS |  |

## What this proves
- **Device data path (D8):** MQTTS/TLS on `chertiot.com:8883` with access-token auth → telemetry stored → read back through the TB REST API, verbatim.
- **Tenant isolation (D4/D10):** one student's credentials cannot read another student's device (HTTP 404).
- **Identity:** all UAT accounts enabled + email-verified, no pending required actions; OIDC discovery live.
- **Public surface:** portal, docs (EN + AR), public status page, and the `lora.` → `/lora` redirect all serve 200.

## Not covered here (need a human/browser — see UAT-CHECKLIST.md)
Interactive SSO redirect, Node-RED editor UX, JupyterHub notebooks, the `/teach` console, alert email delivery, LoRa device registration UI, and the Arabic RTL toggle. Run those manually with the checklist.

> Reproduce: `scratchpad/uat_exec.py` (non-destructive; uses the starter device + sysadmin impersonation).
