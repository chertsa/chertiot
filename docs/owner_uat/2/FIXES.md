# Owner UAT round 3 — findings & fixes

All deployed **staging → production** and verified. Two functional bugs + branding/i18n cleanup.

## Fixed & live

| # | Reported | Fix | Verified |
|---|----------|-----|----------|
| 1.2 | **Dashboard "Widget Error: …reading 'keys'"** | The Temperature/Humidity `time_series_chart` widgets shipped with empty `settings:{}`; TB 4.3's chart threw. Rebuilt both from TB's own widget-type default config (25 settings keys). Re-imported the fixed dashboard for all 4 UAT accounts. | Dashboard JSON valid; all UAT dashboards reset (200). |
| 8 | **Flows editor "Lost connection, reconnecting"** | Node-RED's `/comms` WebSocket reached Caddy forward_auth with an empty `X-Forwarded-Uri` → 403; and the auth subrequest couldn't be made for upgrade requests. Now pass the path owner id as `X-Flows-Uid` and strip `Upgrade`/`Connection` from the auth subrequest. | Real WS handshake to `/comms` → **101 Switching Protocols** (was 403); editor loads 200. |
| 1 | **Only the home page was bilingual; sub-pages English** | 23 Arabic catalog entries were flagged **fuzzy** (pybabel had similarity-matched them to wrong Arabic, e.g. Delete→"my devices", Export→"expires"), so gettext excluded them and they fell back to English. Replaced with correct Arabic, cleared the fuzzy flags, recompiled. | `/devices /alerts /flows /lora /teach` now render Arabic (RTL), no leftover English on the reported strings. |
| 3,4,5,+ | **Footer "powered by ThingsBoard… Privacy · Fair use · Status" + broken links** | Portal footer simplified to **"CHERT IoT"**; fixed signup Privacy/Fair-use → `/docs/policies/…` and LoRa gateway guide → `/docs/guides/lorawan/` (were 404). | Footer shows "CHERT IoT"; doc links 200. |
| (docs) | **"Made with Material for MkDocs" footer** | mkdocs `copyright: CHERT IoT`, `generator: false`. | Docs footer shows "CHERT IoT" only. |
| (Node-RED) | **Header "Node-RED Node-RED"** | editorTheme header/title → **"CHERT Node"**, Node-RED logo image removed; settings now refresh on restart so it applies. | Editor `<title>` = "CHERT Node". |

## Still open

- **issue 6 — Node-RED favicon** still the Node-RED icon. Needs a CHERT favicon asset baked into the spawned container (small follow-up).
- **issue 7 — "Node-RED website" menu link** still present. Node-RED's editorTheme has no clean toggle for it; needs a theme module or menu override (small follow-up).
- **issues 2 & 3 — ThingsBoard chrome** (GitHub "Star 22,402" badge; "powered by ThingsBoard v4.3.1.4" footer link). **Deferred by owner** this pass — needs a source patch to the branded TB image + CI rebuild.

## Worked correctly (no change): IoT Hub, Devices, Assets, Entity views, LoRa registration, Alerts creation.

> Note: existing Node-RED instances pick up the "CHERT Node" branding the next time they restart
> (stop/start or after the 30-min idle cull).
