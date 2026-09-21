# Proposal prompt — add Arabic (ar-SA, LTR) to Grafana

Copy this whole file to the target project (e.g. `chertkatula`) as the task brief for Claude Code,
together with the rest of this `grafana_localization/` kit (`tools/`, `tests/`, `locale/`,
`glossary.md`, `GUIDE.md`). Paste it as your instruction and follow it stage by stage.

---

## Goal

Add **Arabic (`ar-SA`, display name `العربية`)** as a selectable Grafana UI language, **LTR only —
no RTL layout**, reusing the finished translations and tooling in this kit so the work is **not
repeated**. Ship it as a **reproducible, source-built branded Grafana image** — never as a runtime
patch.

## The one hard architectural fact — read first

**You cannot add a language to a prebuilt Grafana image.** A Grafana locale is registered in the
`@grafana/i18n` package and its catalog is **webpack-compiled into the frontend bundle at build
time**. `chertkatula` today runs the prebuilt `grafana/grafana:latest`; to get Arabic you must
switch that service to a **source-built image** produced from a pinned Grafana source tree (the
"grafana-brand" pattern in `GUIDE.md`). Do **not**: mount/replace locale JSON in a running
container, inject browser scripts, or edit files inside a running container — none of those register
a language and all are non-reproducible.

## Non-negotiable constraints

1. **LTR only.** Do not introduce any RTL layout or `dir="rtl"`/`direction:rtl` wiring for `ar-SA`.
   Grafana has no per-locale direction switch by default; keep it that way. Prove LTR (see Verify).
2. **Pin, fail closed.** Choose one **exact** Grafana version tag **and** its commit SHA. The build
   must abort if the cloned `HEAD` ≠ the pinned commit. **Never build from `:latest`** or a mutable
   branch — the translation key set and reproducibility depend on an immutable pin.
3. **No runtime patches / no mounted locale replacements / no in-container edits.** Source build
   only.
4. **Six Arabic CLDR plural forms** (`_zero/_one/_two/_few/_many/_other`) wherever English has a
   plural group (`_one/_other`). The validator enforces exactly this.
5. **Staging before production.** Build → validate → smoke → deploy staging → verify → production
   only on explicit approval.
6. **Reuse, don't re-translate.** Start from `locale/ar-SA/` in this kit (see Reuse rules).

## What this kit gives you

- `locale/ar-SA/grafana.json` — the **complete assembled Arabic catalog** (done for Grafana 13.1.4;
  10,748 leaf keys, validator-clean).
- `locale/ar-SA/namespaces/*.json` — the **per-namespace source of truth** (208 files) the catalog
  is assembled from. This is what ports across versions.
- `locale/ar-SA/grafana-alerting.json` — the `@grafana/alerting` package completeness file.
- `tools/apply-registration.py` — registers `ar-SA` in `packages/grafana-i18n/src`
  (`constants.ts`, `languages.ts`, `index.ts` barrel, `languages.test.ts`). Idempotent, fail-closed
  on missing anchors.
- `tools/assemble-ar.py` — rebuilds `grafana.json` from the per-namespace files.
- `tools/validate.py` — schema-aware validator (parity, 6 plural forms, glossary consistency,
  no-unauthorized-keys, English-identical audit). `--require-complete` gates the build.
- `tools/build.sh.reference`, `tools/smoke.sh.reference` — the proven build/smoke scripts to adapt.
- `tests/registration.ar-SA.test.tsx`, `tests/i18n-fallback.test.mjs`, `tests/package.json` — the
  repo-level and standalone tests.
- `glossary.md` — the approved MSA glossary; `GUIDE.md` — the full architecture + lessons.

## Reuse rules (do not repeat translation work)

- **If you pin Grafana 13.1.4:** reuse `locale/ar-SA/grafana.json` **as-is** (it is already
  complete and validator-clean for that version). Also reuse `grafana-alerting.json`.
- **If you pin any other version:** copy `locale/ar-SA/namespaces/` into your build inputs, run
  `tools/assemble-ar.py <that version's public/locales/en-US/grafana.json>` to reassemble, then
  `tools/validate.py <src> --require-complete`. The validator will report **only the missing/new
  keys** for that version — translate **just those** using `glossary.md` + Modern Standard Arabic,
  drop them into the matching `namespaces/*.json`, reassemble, and re-validate until 0/0. Matching
  keys carry over unchanged, so you translate a small delta, not 10k keys.

## Plan — work in bounded stages, stop for approval between design and implementation

1. **Discover.** Confirm how `chertkatula` runs Grafana (image, digest, compose service,
   auth/SSO, dashboards, provisioning). Decide the pinned Grafana **version tag + commit SHA**
   (match the current `:latest` digest's version, or choose a stable release). Report findings and
   the exact pin. No edits yet.
2. **Design.** Propose: the `grafana-brand/`-style build layout for this repo; the pinned tag/commit;
   the branded image name/tag; which reuse rule applies (13.1.4 → direct, else delta-translate);
   the staging→prod rollout; and the exact files you will add. Wait for owner approval.
3. **Implement (source tree).** In a disposable clone of the pinned Grafana tag (verify commit, fail
   closed): run `apply-registration.py` to register `ar-SA`; install `public/locales/ar-SA/grafana.json`
   and the alerting package file; install the registration test.
4. **Translate the delta** (only if not 13.1.4) per the Reuse rules until `validate.py
   --require-complete` = **0 errors / 0 warnings**. Commit per-namespace files + regenerated catalog
   to your repo as the durable source of truth (never leave them only in a temp clone).
5. **Test.** Run the standalone `i18n-fallback.test.mjs` (fallback + 6 plural forms) and Grafana's
   jest for `registration.ar-SA.test.tsx` (**must assert `resolvedLanguage === 'ar-SA'`** and that
   the language definition carries **no `dir`/`rtl` field**) plus the amended `languages.test.ts`.
6. **Build** the branded image (source Dockerfile, OSS build tags). Record image tag + digest.
7. **Smoke** the image: `ar-SA` compiled into `build/*.js`; the Arabic catalog present (compiled
   chunk carries `\u06xx` Arabic escapes, or the raw `public/locales/ar-SA/grafana.json` ships);
   container `/api/health` OK; **LTR** preserved. Do **not** grep the minified one-line bundle with a
   proximity regex for RTL — that false-positives; rely on the jest LTR assertion + the fact that
   Grafana has no language→direction wiring.
8. **Deploy to staging**, set the branded image for the Grafana service, and **verify in a browser**
   (see Verify). Stop with evidence; **production only on explicit approval.**

## Verify (staging, then prod on approval)

- Grafana lists **العربية** and a user can select it; the UI renders Arabic and stays **LTR**
  (served shell `<html ... >` has **no `dir="rtl"`**; page layout unchanged).
- `window.Chart`… is irrelevant here — instead confirm the Grafana frontend served the **compiled
  `ar-SA`** (the language appears in the built bundle; a known Arabic catalog string is served).
- No RTL wiring for `ar-SA` was introduced (jest LTR test green; source has no `i18next.dir()` /
  `documentElement.dir` / per-locale direction).
- If the target enforces zero external runtime assets, confirm no new external origin is introduced
  by the localization (it should not be).

## Deliverables

- A `grafana-brand/`-style build dir in `chertkatula` (pinned tag+commit, `apply-registration.py`,
  `assemble-ar.py`, `validate.py`, `build.sh`, `smoke.sh`, tests, and `locales/ar-SA/` source of
  truth) wired into CI to build+push the branded image.
- The Grafana compose service switched from `grafana/grafana:latest` to the branded image.
- A short report: version pinned; namespaces/keys translated (or reused); validator errors/warnings
  (must be 0/0); image tag + digest; staging browser evidence; **confirmation the UI is LTR**.

## Guardrails

Pin fail-closed · LTR only, never RTL · source build, no runtime patches · staging before production
· production only on explicit approval · commit the Arabic source of truth (never leave it in a temp
clone). See `GUIDE.md` for the detailed architecture and the specific pitfalls already solved.
