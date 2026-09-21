# Grafana Arabic (ar-SA, LTR) localization kit

A portable, self-contained kit to add **Arabic (`ar-SA` / `العربية`, LTR only — no RTL)** as a
selectable Grafana UI language in another project **without repeating the translation work**. It
bundles the finished translations, the build/validation tooling, the tests, the glossary, and a
ready-to-follow task brief.

> Produced from a real source-built **Grafana 13.1.4** branded image: 208 namespaces, **10,748**
> translated keys, validator-clean (0/0), deployed and browser-verified LTR.

## Start here

1. Read **[PROMPT.md](PROMPT.md)** — the proposal/task brief to hand to Claude Code in the target
   project. It is self-contained and works stage by stage.
2. Skim **[GUIDE.md](GUIDE.md)** — how Grafana i18n works, why a source build is required, and the
   specific pitfalls already solved.
3. Keep **[glossary.md](glossary.md)** open while translating any delta.

## The key constraint

Grafana compiles locales into the frontend **at build time**, so a language can only be added via a
**source-built image** (the "grafana-brand" pattern) pinned to an exact version+commit — **not** by
patching a prebuilt `grafana/grafana:*` image at runtime. `PROMPT.md`/`GUIDE.md` cover this.

## Contents

| Path | What it is |
|---|---|
| `PROMPT.md` | Task brief for Claude Code (start here) |
| `GUIDE.md` | Architecture + lessons + pitfalls |
| `glossary.md` | Approved Modern-Standard-Arabic glossary (29 core terms) |
| `tools/apply-registration.py` | Register `ar-SA` in `packages/grafana-i18n/src` (idempotent, fail-closed) |
| `tools/assemble-ar.py` | Build `grafana.json` from the per-namespace files |
| `tools/validate.py` | Schema-aware validator (`--require-complete` gates the build) |
| `tools/build.sh.reference` | Proven clone→verify→register→install→validate→build script (adapt) |
| `tools/smoke.sh.reference` | Proven image smoke script (adapt) |
| `tests/registration.ar-SA.test.tsx` | Grafana jest: registration, LTR (no dir/rtl), `resolvedLanguage`, plurals |
| `tests/i18n-fallback.test.mjs` | Node: fallback + six Arabic plural forms |
| `tests/package.json` | Deps for the node test |
| `locale/ar-SA/grafana.json` | Complete assembled Arabic catalog (10,748 keys, for 13.1.4) |
| `locale/ar-SA/namespaces/*.json` | Per-namespace **source of truth** (208 files) — ports across versions |
| `locale/ar-SA/grafana-alerting.json` | `@grafana/alerting` package completeness file |

## Reuse in one line

- **Pinning Grafana 13.1.4?** Use `locale/ar-SA/grafana.json` **as-is** (already complete + clean).
- **Any other version?** Copy `locale/ar-SA/namespaces/`, run `tools/assemble-ar.py <that version's
  en-US grafana.json>`, then `tools/validate.py <src> --require-complete`; translate **only** the
  keys it reports missing (glossary + MSA), reassemble, re-validate to 0/0. Matching keys carry over.

## Guardrails

LTR only (never RTL) · pin fail-closed (never `:latest`) · source build, no runtime patches ·
staging before production · commit the Arabic source of truth (never leave it in a temp clone).
