# grafana-brand — CHERT Grafana with Arabic (ar-SA, LTR)

Native source-built Grafana image adding **Arabic `ar-SA` («العربية»)** as an LTR editor language.
Mirrors `thingsboard-brand/` / `nodered-brand/`: consume a pinned upstream, apply CHERT changes at
build time, produce one immutable GHCR image. **No runtime patches / mounted files / container edits.**

## Provenance & pinning (fail-closed)
- Upstream: `github.com/grafana/grafana`, tag **`v13.1.4`**.
- Required commit: **`afdab62868c728d60df3f87657e68c8ed6dbb926`** — `build.sh` aborts if `HEAD` differs
  (no mutable branch, no unverified source).
- Image: **`ghcr.io/chertsa/chertiot-grafana:13.1.4-b<BUILD_NUMBER>`** (published by `images.yml`).
- Licensing: Grafana is **AGPL-3.0**; we add only locale JSON + a small registration edit and keep all
  upstream copyright/AGPL notices. Source changes are recorded as `apply-registration.py` + `locales/`.

## What the build does (`build.sh`)
1. Clone the pinned tag; **verify commit** (fail closed).
2. `apply-registration.py` → register `ar-SA` in `packages/grafana-i18n/src/{constants.ts,languages.ts,languages.test.ts}` (idempotent). No RTL/`dir` code — Grafana is LTR by default.
3. Install CHERT locales: `locales/ar-SA/grafana.json → public/locales/ar-SA/grafana.json`;
   `locales/ar-SA/grafana-alerting.json → packages/grafana-alerting/src/locales/ar-SA/grafana-alerting.json`.
4. `validate.py --require-complete` (schema-aware; fail closed) — see below.
5. `docker build` via Grafana's root `Dockerfile` (OSS) → tag + `LAST_IMAGE`.

## Validation (`validate.py`)
Schema-aware, NOT a naive diff: every non-plural en-US key required once; each English plural group
must have EXACTLY the six Arabic CLDR forms (`_zero/_one/_two/_few/_many/_other`); rejects extra/missing
keys; verifies `{{vars}}` + indexed `<n>` tags per form; flags invalid JSON, empty values, ar==en
(except allowlisted identifiers), bidi-control chars, translated protected identifiers, and glossary
inconsistency. `--require-complete` makes missing keys fail (the release gate). English is the runtime
fallback for any untranslated key (proven: `scratchpad/i18n-fallback-test`).

## Deploy & rollback
- Deploy: set `GRAFANA_IMAGE=ghcr.io/chertsa/chertiot-grafana:13.1.4-bN` in the server `.env`, `pull`,
  recreate `grafana`. **Staging first; production requires separate approval.**
- Rollback: set `GRAFANA_IMAGE=grafana/grafana:13.1.4` (official) + recreate `grafana`.

## Status
Pipeline + registration + validator are in place and verified. The `ar-SA` translation content
(target ~10,762 keys) is produced in validator-gated tranches; the image is only built/released once
`validate.py --require-complete` passes (no partial UI released as "complete").
