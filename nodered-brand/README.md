# nodered-brand — branded Node-RED (Arabic, LTR-only)

Adds **Arabic (`ar-AR`)** to Node-RED as a first-class, **left-to-right** editor language and makes it
the **default**, baked into an immutable image built by CI. Mirrors `thingsboard-brand/`: we consume
the pinned upstream image and brand it via a build layer — we do **not** fork the Node-RED monorepo.

## What the build does (`Dockerfile`, all at build time)
1. Copies the committed `locales/ar-AR/{editor,infotips,jsonata}.json` into the canonical
   `@node-red/editor-client/locales/ar-AR/` path (served verbatim by Node-RED's runtime i18n).
2. Registers `"ar-AR": "العربية"` in every locale's `editor.json` `languages` map (Arabic shows in
   the selector regardless of the active UI language).
3. Sets the **default** editor language to Arabic by patching `detectLanguage()` in the built client
   (`red.min.js` + `red.js`). Each edit is **count-asserted** — a zero-hit replace fails the build.

English stays one click away in the standard selector and **persists** once chosen; missing keys
fall back to `en-US`. **No RTL**: no `dir="rtl"`, no mirroring, no RTL CSS (guarded by the validator).

## Files
- `locales/ar-AR/*.json` — the committed Arabic catalogs (source of truth).
- `reference/en-US/*.json` — upstream `en-US` catalogs of the pinned image, for the parity test.
  Refresh **only** when the Node-RED pin changes (it is frozen ⇒ ~never).
- `validate_catalogs.py` — parity + protected-token + LTR gate (run in CI and via `make`).
- `BUILD_NUMBER` — bumps the image tag `chertiot-nodered:<ver>-bN`.

## Build / release
CI (`.github/workflows/images.yml`) builds and pushes
`ghcr.io/chertsa/chertiot-nodered:<NODERED_VERSION>-b<BUILD_NUMBER>`. The portal spawns that pinned
image via `NODERED_IMAGE` (see `.env.example`, `portal/app/flows.py`).

## Upgrade policy
Node-RED is frozen. If the pin ever changes: refresh `reference/en-US/`, re-run
`validate_catalogs.py` (translate any newly-added en-US keys into MSA, preserving protected tokens),
re-confirm the two JS anchors still match, bump `BUILD_NUMBER`, rebuild, redeploy staging→prod.
