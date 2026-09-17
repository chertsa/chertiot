# Node-RED Arabic (ar-AR) LTR — Standard Installation Evidence Report

**Verdict:** ✅ Completed (staging + production).
**Date:** 2026-09-18 · **Implementer:** Claude (Opus 4.8), authorized by owner.
**Prompt:** `docs/ar-AR/NODE_RED_ARABIC_LTR_STANDARD_INSTALLATION_MASTER_PROMPT.md`
**Plan:** `docs/ar-AR/PLAN-node-red-arabic-ltr.md`

## 1. Canonical implementation
- **Repository / branch:** `chertsa/chertiot` @ `main`.
- **Model:** CHERT brands the pinned upstream engine image via a build layer (the `thingsboard-brand`
  precedent); we do **not** fork the Node-RED monorepo. Owner-approved **Option A**.
- **Base image:** `nodered/node-red:5.0.6` (frozen pin, `NODERED_VERSION`).
- **Brand layer:** `nodered-brand/` — `Dockerfile`, `locales/ar-AR/*.json` (committed source),
  `reference/en-US/*.json` (parity reference), `validate_catalogs.py`, `BUILD_NUMBER`, `README.md`.
- **Canonical locale path (in the built image):**
  `/usr/src/node-red/node_modules/@node-red/editor-client/locales/ar-AR/{editor,infotips,jsonata}.json`.
- **Built artifact:** `ghcr.io/chertsa/chertiot-nodered:5.0.6-b1` (CI `images.yml` → GHCR).

## 2. Catalog validation (`nodered-brand/validate_catalogs.py`, CI-gated)
Recursive parity of the three `ar-AR` catalogs against `en-US` of the exact pinned image:
- Valid UTF-8 JSON, no BOM.
- **editor.json:** 37 top-level keys — identical key set/types to en-US (+ the one allowed extra
  `languages.ar-AR`). **infotips.json / jsonata.json:** identical key sets.
- Protected tokens preserved per key: interpolation `__x__`, i18next `{{core:…}}`, keyboard `[ctrl]`,
  HTML tags/entities, URLs. **JSONata `.args` signatures byte-identical** to en-US.
- No bidi/direction-control characters; no translation sentinels / replacement chars.
- `languages.ar-AR = "العربية"` present in ar-AR (source) and injected into **every** locale's
  `editor.json` by the build.
- Static LTR guard: no `dir="rtl"` / RTL CSS anywhere in the brand layer.
- Result: **OK** (exit 0).

## 3. Language registration & default (discovery is standard)
- Node-RED discovers catalogs by serving `locales/<lang>/*` verbatim and builds the selector from the
  `languages` map in the active `editor.json`. We add both: the `ar-AR/` dir **and** the label.
- **Default = Arabic (owner directive).** Node-RED has no server setting for the default editor
  language — `red.js`: `localStorage["editor-language"] || detectLanguage()`,
  `detectLanguage(){ return navigator.language }`, i18next `fallbackLng: en-US`. The build patches
  `detectLanguage()` to return `"ar-AR"` in `red.min.js` (anchor `){return navigator.language}`) and
  `red.js` (`return navigator.language`), **each replacement count-asserted (==1) or the build fails**.
- English remains one click away in the standard selector and **persists** via `editor-language`;
  en-US fallback covers any future gap.

## 4. LTR proof (owner decision honoured)
No `dir="rtl"` introduced (grep on built `red.min.js` = 0); no mirroring, no RTL CSS, no direction
toggle, no bidi control chars in strings. Arabic renders as Unicode inside the unchanged LTR editor;
code/JSON/JSONata/MQTT/URL surfaces stay LTR.

## 5. Build & local acceptance (pre-CI, on workstation Docker 29.5.2)
- `docker build nodered-brand/` → success (all build-time asserts passed).
- In the built image: `locales/ar-AR/*` present; `languages.ar-AR = العربية` in en-US, de, ar-AR;
  `){return"ar-AR"}` present in `red.min.js`; `return "ar-AR"` in `red.js`; `dir="rtl"` count = 0.
- Runtime container smoke: `GET /locales/editor?lng=ar-AR` → Arabic (`menu.label.import = "استيراد"`,
  `languages.ar-AR = العربية`); served `red/red.min.js` contains the default-lang patch; editor `/` → 200.

## 6. Wiring
- `portal/app/flows.py`: `NODERED_IMAGE` env (defaults to the branded GHCR ref; upstream fallback).
- `docker-compose.yml`: portal env gains `NODERED_IMAGE`; the `nodered-image` warm service uses it.
- `.env.example`: `NODERED_IMAGE=ghcr.io/chertsa/chertiot-nodered:5.0.6-b1`.
- `.github/workflows/images.yml`: new `nodered` job — runs the validator, builds, pushes `-b1`.

## 7. CI build & deployment
- CI `images.yml` run 35287568750 → `nodered` job **success**; pushed
  `ghcr.io/chertsa/chertiot-nodered:5.0.6-b1`, digest
  `sha256:175e98e697336f9f4d6223b38d5de466d518a80c0e4235c398161e66fafa8ade`.
- **Staging** (`stage.chertiot.com`, 161.35.119.46): `.env` `NODERED_IMAGE` set to the branded ref;
  image pulled (auth OK); portal rebuilt (core+flows). Branded-image container smoke: Arabic served
  (`استيراد`), default-lang patch in served `red.min.js`, `dir="rtl"` = 0. **Portal-spawner E2E:**
  `flows.spawn` for a provisioned user created a container on image `chertiot-nodered:5.0.6-b1`
  (status running); `GET /u/<id>/locales/editor?lng=ar-AR` → `استيراد`; served `red.min.js` carries
  the default patch. Test instance removed (volume preserved).
- **Production** (`chertiot.com`, 134.122.31.32): same steps; image pulled, portal rebuilt.
  **Portal-spawner E2E:** spawned container on `chertiot-nodered:5.0.6-b1`; instance served
  `استيراد`; default patch present. Test instance removed (volume preserved).

## 8. Runtime durability
- **Image is the sole source** of the ar-AR catalogs + default — no runtime copy/mount/init.
  A container replacement (`docker rm` + respawn) reproduces Arabic from the same immutable image;
  student flows/credentials survive because they live in the per-user named volume, not the container.
- **Version-bump migration:** `flows.py` `spawn()` now recreates a student's container when its image
  ≠ `NODERED_IMAGE` (commit d3464c7), so a future `-bN` reaches existing students on next open; the
  named volume preserves their flows. Idle-culled/stopped containers likewise recreate on the new image.
- **Persistence / round-trip:** English remains selectable in the standard selector and is remembered
  via the `editor-language` preference; en-US fallback covers any missing key. (Client-side prefs are
  per-browser, standard Node-RED behaviour.)

## 9. Rollback
Set `NODERED_IMAGE` back to `nodered/node-red:5.0.6` (or the previous `-bN`) in `.env`, re-warm, and
stop/respawn instances — student volumes/flows/credentials are untouched (the change is image-only).

## 10. Limitations
- Third-party contributed-node help is localized by each node package, not by the three core catalogs.
- Arabic-default is an owner-directed change to the editor client's default-language resolver, beyond
  the master prompt's original "available + browser-detected" scope (recorded here as approved).
