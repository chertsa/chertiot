# Plan — Arabic (`ar-AR`) in Node-RED, LTR-only, as a standard branded image

**Status:** ✅ APPROVED (Option A + Arabic-default) and IMPLEMENTED on staging + production
(2026-09-18). See the evidence report: `docs/audit/node-red-arabic-ltr-standard-installation-report.md`.
**Author:** Claude (Opus 4.8) · **Date:** 2026-09-18
**Scope binding:** Arabic localization inside the **existing LTR** Node-RED editor. **No RTL.** (per `docs/ar-AR/NODE_RED_ARABIC_LTR_STANDARD_INSTALLATION_MASTER_PROMPT.md`)

---

## 1. Findings — how Node-RED i18n actually works in our pinned image

Verified against the real `nodered/node-red:5.0.6` image (staging host):

- Catalogs live at
  `/usr/src/node-red/node_modules/@node-red/editor-client/locales/<lang>/{editor,infotips,jsonata}.json`.
  Present today: `de, en-US, es-ES, fr, ja, ko, pt-BR, ru, zh-CN, zh-TW`.
- These JSON files are **served verbatim at runtime** — the editor-client build copies `locales/`
  unchanged; there is **no bundling/transform step** for catalogs. So a file placed in that dir in
  the built image is byte-identical to what a from-source build would emit.
- The **language selector** is populated from the `languages` map inside `editor.json`; the
  **catalog** for a selected language is loaded from its `locales/<lang>/` dir. Both are required:
  1. add `"ar-AR": "العربية"` to the `languages` map (so it appears in the menu), and
  2. ship `locales/ar-AR/{editor,infotips,jsonata}.json` (so selecting it loads real strings).
- Selection persists client-side via the standard `editor-language` preference; missing keys fall
  back to `en-US`; browser `Accept-Language` can select `ar-AR` when no explicit preference is set.
  (All standard Node-RED behaviour — we add nothing custom.)

### Supplied catalogs (`docs/ar-AR/`) — review result
- `editor.json` (83 KB, 37 top-level keys — **matches** en-US's 37), `infotips.json` (1 key),
  `jsonata.json` (69 keys). All valid UTF-8 JSON.
- ⚠️ **Gap to fix:** the supplied `editor.json` `languages` map translates the *other* languages
  into Arabic but is **missing its own `"ar-AR": "العربية"` self-entry**. The prompt (§3) requires
  it in both `ar-AR/editor.json` and `en-US/editor.json`. → We add it.
- Full recursive key/type/token **parity vs en-US** (interpolation `__x__`, i18next `{{core:…}}`,
  HTML tags, URLs, JSONata `args` signatures, keyboard `[ctrl]` tokens) is **not yet verified** —
  that is step 3 below and is a hard gate.

## 2. Architectural decision (needs your ruling)

The master prompt's letter says: use the **canonical Node-RED source repo or an approved fork**,
build from source, and never touch `node_modules`. **We have no Node-RED fork**, and CHERT's
established, frozen-pin model is: *consume the official upstream image, brand it into one immutable
CI-built GHCR image per component* — exactly what `thingsboard-brand/` does for ThingsBoard.

Two ways to satisfy the prompt's **intent** (source-controlled, immutable, discovered by the normal
i18n mechanism, LTR-only, survives restart/redeploy, no runtime copy/mount/init):

### ✅ Option A — Branded image layer (RECOMMENDED)
A new `nodered-brand/` in this repo, mirroring `thingsboard-brand/`:
- `Dockerfile` `FROM nodered/node-red:5.0.6` that **COPYs** the three committed `ar-AR` catalogs into
  the canonical locales path and runs an **idempotent build-time transform** injecting
  `"ar-AR": "العربية"` into every `locales/*/editor.json` `languages` map.
- Built + pushed by CI (`images.yml`) → `ghcr.io/chertsa/chertiot-nodered:5.0.6-b1`.
- `flows.py` spawns that pinned image instead of `nodered/node-red:5.0.6`.

*Why this is standard, not a workaround:* the catalog JSONs ship verbatim at runtime, so the built
artifact is identical to a from-source build; the files are **committed source in our repo**; the
image is **immutable + versioned**; discovery uses the **normal** i18n dir-scan + `languages` map;
nothing is copied into a running container, mounted, or injected by an init script. It honours every
substantive requirement and every stop-condition except the literal "must be the node-red monorepo",
which does not fit our deployment model (we don't fork engines; we brand upstream images).

- **Effort:** ~half a day. **Risk:** low (no upstream build; pin unchanged). **Ongoing:** re-run the
  parity test whenever the Node-RED pin ever changes (it's frozen, so ~never).

### Option B — Fork the Node-RED monorepo, build from source
Literal reading of the prompt: fork `node-red/node-red` at `v5.0.6`, add catalogs to
`packages/node_modules/@node-red/editor-client/locales/ar-AR/`, run the full grunt/webpack editor
build, produce our own image.
- **Effort:** multi-day. **Risk:** high — we'd own and maintain a full engine fork + a heavy,
  fragile CI build, for a payload that ships **byte-identical** to Option A. Disproportionate for 3
  JSON files that are served unmodified. **Not recommended.**

**My recommendation: Option A.** It is the correct, standard CHERT approach and produces the same
runtime result Option B would.

## 3. Implementation steps (Option A)

**Commit 1 — catalogs + registration**
1. `git mv`/copy the three files to `nodered-brand/locales/ar-AR/{editor,infotips,jsonata}.json`
   (canonical committed source in our repo).
2. Add `"ar-AR": "العربية"` to `nodered-brand/locales/ar-AR/editor.json`'s `languages` map.
3. Write `nodered-brand/Dockerfile` (`FROM nodered/node-red:5.0.6`, `COPY` the dir, `RUN node` a
   tiny idempotent transform that adds the `ar-AR` label to every existing
   `locales/*/editor.json` `languages` map). Add `nodered-brand/BUILD_NUMBER` (=1) and a `README.md`.
4. Add the `nodered` job to `.github/workflows/images.yml` → build + push
   `ghcr.io/chertsa/chertiot-nodered:5.0.6-b1` (same login/tag pattern as the tb/caddy jobs).

**Commit 2 — parity + LTR validation test (hard CI gate)**
5. `nodered-brand/validate_catalogs.py` (stdlib only), run in CI and via a make target. Asserts, per
   the prompt §5: parse all three ar-AR files; recursive key-path + value-type parity vs en-US;
   per-key interpolation tokens (`__name__`, `__count__`, …); i18next action tokens (`{{core:…}}`);
   embedded HTML tags/entities/URLs; unchanged JSONata `args` signatures; no translation sentinels /
   malformed Unicode; `languages.ar-AR` present in ar-AR + en-US; and a static assertion that the
   change introduces **no `dir="rtl"`/RTL CSS** anywhere. If en-US has keys ar-AR lacks, the test
   lists them and fails (I translate those to MSA, preserving protected tokens, before proceeding).

**Commit 3 — wiring, docs, evidence**
6. `flows.py`: `NODERED_IMAGE` default → `ghcr.io/chertsa/chertiot-nodered:5.0.6-b1` via a
   `NODERED_IMAGE` env var; add `NODERED_IMAGE=…` to `.env.example` (+ both servers' `.env`).
   (`spawn()`'s `images.pull` already handles a GHCR ref; server daemon is already GHCR-authed for
   the tb image — verified as part of deploy.)
7. Update `flows.py` `settings.js` comment/inventory to list `ar-AR` as supported.
8. Evidence report `docs/audit/node-red-arabic-ltr-standard-installation-report.md` (repo/branch,
   base image + digest, changed files, catalog counts, parity/token results, discovery explanation,
   runtime proof, LTR proof, restart/redeploy proof, rollback). Update CLAUDE.md gotchas + a memory.

**Build → staging → prod (staging first, always)**
9. Trigger `images.yml` → publish `-b1`. Point `NODERED_IMAGE` on **staging**, restart a student's
   flow instance, prove: `العربية` in the selector; selecting it loads `locales/ar-AR/*` with **no
   404s**; layout stays **LTR** (`<html dir>` not `rtl`, header/palette/canvas unmoved); MQTT topics/
   JSON/JSONata stay LTR; persists across reload; English restores cleanly; survives container
   replacement. Capture the 4 screenshots the prompt requires.
10. Repeat on **prod**. Fill the evidence report with runtime results + digests.

## 4. Explicit LTR guarantees (owner decision honoured)
No `dir="rtl"`; no mirrored header/menu/palette/sidebar/canvas/ports; no RTL CSS or `[dir="rtl"]`
rules; no direction toggle; no Unicode direction-control chars injected into strings; code/JSON/
JSONata/MQTT/URL/IP/ID surfaces stay LTR. Arabic renders as Unicode text inside the unchanged LTR UI.
A CI assertion guards this.

## 4b. Arabic as the default language (owner directive, 2026-09-18)
Owner amended the earlier "available only" choice: **Arabic must be the default**, not English.
Node-RED exposes **no server-side setting** for the default editor language — verified in
`red.js`: `localStorage["editor-language"] || RED.i18n.detectLanguage()`, and
`detectLanguage(){ return navigator.language }`, with i18next `fallbackLng: en-US`. So the default
can only be changed by (a) writing localStorage from a client script — the exact "manual browser
storage" workaround the prompt forbids — or (b) a **build-time change to `detectLanguage()`** baked
into our immutable branded image. We take (b): the brand build patches `detectLanguage()` to return
`"ar-AR"` (the unique, function-name-agnostic anchor `){return navigator.language}` in `red.min.js`,
count-asserted; plus `red.js`). Result: the editor **opens in Arabic** for anyone with no stored
preference; English remains one click away in the standard selector and **persists** once chosen;
en-US fallback still covers any gap. This is committed source, versioned, reproducible, and survives
restart/redeploy — not a runtime injection.

## 5. Honest limitations / out of scope
- Delivered behaviour = Arabic is the **default**, **switchable**, and the choice **persists**
  (§4b). This is an owner-directed change to the editor client's default-language resolver, beyond
  the master prompt's original "available + browser-detected" scope — recorded here and in the
  evidence report as an approved deviation.
- Node-RED node **help/docs** contributed by individual nodes are localized by each node package, not
  by these three core catalogs; core editor UI is covered, third-party node help is not.
- We brand the upstream image (Option A); we do **not** fork the Node-RED monorepo (Option B).

## 6. Stop conditions I will honour mid-execution
Halt and report (no workaround) if: catalog parity can't be reconciled safely; the change would
require mutating a running container; the branded image fails to build or the parity/LTR test fails;
GHCR pull auth for the new image can't be satisfied on a server; or anything would introduce RTL.

---

### Decision requested
1. **Approve Option A** (branded `nodered-brand/` image) vs Option B (full fork) — I recommend **A**.
2. Confirm the **LTR-only, no-auto-default** delivered behaviour in §5 is acceptable.
On approval I'll execute commits 1–3, trigger the CI build, and roll out **staging → prod** with the
screenshot + runtime evidence report.
