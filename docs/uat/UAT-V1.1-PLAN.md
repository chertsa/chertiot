# UAT v1.1 — project-centric platform (production)

**Start here: https://chertiot.com** · Environment: **production**, v1.1 (D13 project model).
Logins & seeded data: `docs/uat/UAT-CREDENTIALS.md` (git-ignored — 4 users: Alice, Bob, Carol, Dave).
Seeded: 3 projects across owners + cross-membership, 4 devices with **7 days of history**, 2 alarm
rules, one pending invite and one pending join request. Checklist: `UAT-V1.1-CHECKLIST.md`.

The platform is now **project-centric**: sign in → your **projects portfolio** → open a project → its
isolated workspace (devices, flows, notebook, alerts, LoRa, dashboard, report). A project is its own
ThingsBoard tenant; owners and members are full tenant admins of it.

---

## Scenario A — Owner with rich data (Alice)
1. Go to **https://chertiot.com** → **Sign in** → `alice@chertiot.dev`.
2. **Portfolio** (`/home`): expect a summary strip (Projects / Owned / Shared with me) and two cards —
   **Greenhouse Monitor** (owner) and **City Weather Station** (member). "Learn" section below.
3. Open **Greenhouse Monitor**. Expect the live dashboard to populate within a second or two:
   - KPIs: **2 devices, 2 online**, fleet 100%, 0 active alarms.
   - **Last-24h chart** with temperature + humidity curves (real seeded history).
   - Devices table (greenhouse-sensor, water-tank) with latest readings + last-seen.
4. **Members panel** (owner-only, lower on the page): Alice (owner), Bob (member); a **pending request
   to join from Dave** → click **Approve**. A **pending invite to carol@chertiot.dev** with a link.
5. Open **Report** (tool card or `/report`): lifecycle header (status, created, members), KPIs, device
   roster, **alarm history**, and the 24-hour chart.
6. **Devices**: open greenhouse-sensor → copy connection snippet / rotate token / see it's scoped to
   this project only.
7. **Alerts**: confirm the seeded `temperature > 30` rule is listed; add another and delete it.
8. Sign out (top-right) → confirm you land back on the public site, logged out.

## Scenario B — Collaboration & isolation (Bob, Carol, Dave)
9. Sign in as **bob@chertiot.dev**. Portfolio shows **City Weather Station** (owner) + **Greenhouse
   Monitor** (member). Open Greenhouse Monitor → Bob sees the **same** devices/dashboard as Alice
   (shared tenant), but **no** Members-management panel (he's not the owner).
10. Open **City Weather Station** → its own device (weather-station) + 24h chart; wind/pressure in the
    device readings. Confirm Bob does **not** see Alice's or Carol's other projects.
11. Sign in as **carol@chertiot.dev**. She owns **Water Utility** (reservoir-1, level/flow, `level<25`
    alarm rule). She also had a **pending invite** to Greenhouse Monitor — it should have **auto-accepted
    on login**, so Greenhouse Monitor now appears in her portfolio as a member. (Open it to confirm.)
12. Sign in as **dave@chertiot.dev**. If Alice approved his request (step 4), **Greenhouse Monitor**
    now appears in his portfolio. Open it — he sees the shared data as a member.
13. **Enable/disable a member** (as Alice, owner of Greenhouse): in the Members panel, **Disable** Bob →
    sign in as Bob → opening Greenhouse Monitor now shows "access disabled". **Enable** Bob again → access
    restored. **Remove** a member and confirm the project drops off their portfolio.

## Scenario C — You create a new project (the finale)
14. Sign in as **dave@chertiot.dev** (or any account) → **+ New project** → name it (e.g. "My Pilot") →
    Create. It provisions its own tenant and lands on the workspace.
15. **Devices → + add a device** → open it → use the shown MQTT snippet (host `chertiot.com`, port 8883,
    username = the device token) to publish a reading, or send from an ESP32/Pi. Watch it appear on the
    project dashboard and go **online**.
16. Invite a teammate by email from the **Members** panel (copy the invite link), add an **alert**, and
    open the **Report**.

## Notes / known scope
- **Notebooks (Lab):** the per-project notebook link is wired, but JupyterHub is not enabled on this host
  yet (`LAB_ENABLED=false`) — the notebook won't spawn until it's turned on. Flag if you want it enabled.
- **Full ThingsBoard console** deep-link for members is deferred; the portal dashboard + report cover
  project data. (Rationale in ADR-001.)
- The **Water Utility** 24h chart is empty by design — the built-in chart plots temperature/humidity;
  level/flow show in the KPIs and device table.
- Report anything off in `docs/owner_uat/` (screenshots + notes) as before, or list issues and I'll fix.
