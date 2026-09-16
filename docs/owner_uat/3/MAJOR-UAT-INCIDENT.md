# Major UAT — backbone test result + production incident

**Date:** 2026-09-16 · **Env:** production

## Headline
The major UAT built the full backbone dataset successfully — **except the one thing that connects
everything: telemetry persistence is currently DOWN on production.** Every device telemetry
message fails silently at ThingsBoard's rule-engine **"Save Timeseries"** node, so new readings
never reach the database or dashboards. This affects **all tenants**. This is exactly the
"backbone" you intuited — and the UAT found it.

## Users created
| Role | Email | Password | Cohort |
|---|---|---|---|
| Teacher (instructor) | major.teacher@chertiot.com | `Uat-c33bfe96-2026` | major-uat |
| Student | major.student@chertiot.com | `Uat-8c54c638-2026` | major-uat |

Class code: `UAT-FBF4`. (On "comments/approvals": the platform has no such workflow — the teacher's
real powers are class codes, roster, and suspend; the nearest thing to approval is alarm ack/clear.)

## What was built OK (master data + services)
- **4 devices** in the student tenant — greenhouse-sensor, weather-station, water-tank, hvac-unit —
  each with **server attributes** (location, firmware, model…).
- **1 asset** "Greenhouse A" + **4 Contains relations** (asset → each device).
- **1 entity view** "Greenhouse A - Public view".
- **3 alarms** (2 active: High Temperature, HVAC Power Spike; 1 cleared: Low Water Level).
- **Node-RED flow** "Greenhouse monitor" deployed; **LoRa device** `lora-30be20` registered.
- **Map walk: 22/24 passed** — the only 2 failures are telemetry (below).

## The incident (the 2 failures)
- **Symptom:** device telemetry (both MQTTS `:8883` and HTTP API) is accepted (HTTP 200) but never
  stored. **Zero** device rows land in `ts_kv`; API reads return `null`.
- **Failure point:** the rule engine **"Save Timeseries"** node — logged as *"Failed to process
  message … Save Timeseries"* with **no exception** (silent).
- **Scope:** all tenants (including `uat.student1`, whose telemetry worked in UAT round 1).
- **Survives:** a TB restart **and** a full `core`-profile restart.
- **Ruled out:** disk (22% used, 122 GB free), memory (~4 GB free), Postgres (healthy; non-device
  internal stats still write to `ts_kv`).

## Root cause identified — and fixed
`ensure_student_profile` re-saved the **DEFAULT** tenant profile on **every login**. Each save
broadcasts a *tenant-profile-update* that reinitializes the rule-engine actors of **every** tenant
using that profile. The heavy UAT testing (many logins) churned the rule engine into a wedged state
where Save Timeseries fails.

**Fixed & deployed** (commit on `main`): the profile save is now **idempotent** — it only re-saves
when the intended config actually changed. This prevents recurrence, but did **not** un-wedge the
already-broken state (restarts don't clear it either → the bad state is persistent, not just
in-memory).

## Why it matters
Telemetry is the spine linking **devices → dashboards → alerts → Node-RED → JupyterHub**. While it's
down, those surfaces show no live data. Everything non-telemetry works (SSO, device/asset/entity/
alarm CRUD, flows editor, LoRa registration, docs, status, isolation).

## Recommended remediation — needs your call
1. **Deep root-cause (non-destructive, my recommendation):** turn on TB rule-node debug for one
   tenant's *Save Timeseries* node, send one reading, capture the real error, then fix.
2. **Rebuild the Root Rule Chain** from TB's default template if the rule-chain state is corrupt.
3. **Restore from the last good nightly backup** (before the churn) — reliable but loses recent data;
   heavy-handed since these are all test tenants in building phase.

I've **paused** to avoid adding more load. I can proceed with **(1)** autonomously (non-destructive)
on your go, and escalate to (2)/(3) only if needed.
