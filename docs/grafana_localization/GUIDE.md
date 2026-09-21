# Grafana Arabic (ar-SA, LTR) localization — architecture & lessons

Reference for the `PROMPT.md` task. Everything here was proven on a real source-built Grafana 13.1.4
branded image (208 namespaces, 10,748 keys, validator-clean, deployed and browser-verified LTR).

## 1. How Grafana i18n works (why a source build is required)

- Grafana uses **i18next + react-i18next + `@grafana/i18n`**. The **supported-language registry**
  lives in `packages/grafana-i18n/src/`:
  - `constants.ts` — per-language code constants (e.g. `ENGLISH_US = 'en-US'`, …).
  - `languages.ts` — the `LANGUAGES` array of `{ code, name }`.
  - `index.ts` — the package **barrel** that re-exports each code constant.
  - `languages.test.ts` — a pinned expected-language list (fails if the registry changes without it).
- The **app-side loader** is derived in `public/app/core/internationalization/constants.ts`:
  ```ts
  loader: { [GRAFANA_NAMESPACE]: () => import(`../../../locales/${locale}/grafana.json`) }
  ```
  This is a **webpack template-literal dynamic import** → webpack bundles every
  `public/locales/<lang>/grafana.json` into **lazy JS chunks** at build time. So the catalog is
  compiled into the frontend; **placing `public/locales/ar-SA/grafana.json` + registering the
  language is what makes Arabic real** — and it only takes effect through a **source build**. A
  prebuilt official image cannot be localized after the fact.
- `resolvedLanguage` is populated only after a backend/store load or with populated resources; it is
  `undefined` with empty resources and no backend (matters for the tests, below).

## 2. Registering ar-SA (what `apply-registration.py` does, idempotent, fail-closed)

- `constants.ts`: add `export const ARABIC_SAUDI_ARABIA = 'ar-SA';`.
- `languages.ts`: import that constant and append `{ code: ARABIC_SAUDI_ARABIA, name: 'العربية' }`.
- `index.ts`: **re-export `ARABIC_SAUDI_ARABIA` from the barrel** (easy to miss — the registration
  test imports it from `@grafana/i18n`; without the barrel export it is `undefined`).
- `languages.test.ts`: add `{ code: 'ar-SA', name: 'العربية' }` to the pinned list.
- Each edit checks for an anchor and aborts if the upstream structure changed (fail closed).

## 3. Arabic plural forms

English catalogs use two forms (`key_one`, `key_other`). Arabic (CLDR) needs **six**:
`_zero, _one, _two, _few, _many, _other`. For every English plural group, produce all six Arabic
forms; keep `{{count}}` interpolation. `validate.py` enforces *exactly* six forms per group and no
unauthorized extra keys (a stray plural on a non-plural key is a hard error).

## 4. Namespaces

- The main catalog is the **`grafana`** namespace (one big `grafana.json`, ~10.7k leaf keys across
  ~208 dotted top-level namespaces like `alerting.*`, `dashboard.*`, …). The per-namespace files in
  `locale/ar-SA/namespaces/` are the **durable source of truth**; `assemble-ar.py` merges them into
  `grafana.json`.
- The **`@grafana/alerting` package** has its **own** `grafana-alerting` namespace (a handful of
  shared-component strings). Upstream does **not** load it in-app for any language, so those ~10
  strings render in English in-app regardless of locale. Ship the `ar-SA` package file for
  completeness, but do **not** add a bespoke loader (that would diverge from frozen upstream). The
  `alerting.*` keys inside the main `grafana.json` DO render and ARE fully translated.

## 5. Validation (`validate.py`)

Gates the build. Rules: en↔ar parity; exactly six Arabic plural forms per group; `{{count}}` var
optional per form; glossary consistency (see `glossary.md`); **no unauthorized keys**; and an
**English-identical audit** — a value equal to English is only allowed for an allowlist of product
names, acronyms, code identifiers, format placeholders, units, and protected tokens
(`URL`, `UID`, `UUID`, `LDAP`, `Mimir`, `Alertmanager`, `PromQL`, product names, `hh:mm`, …).
`--require-complete` demands **0 errors / 0 warnings**.

## 6. Tests

- `tests/registration.ar-SA.test.tsx` (Grafana jest): asserts the `ARABIC_SAUDI_ARABIA` constant and
  canonical `ar-SA`; that it is registered as `العربية`; that the definition is `{code,loader,name}`
  with **no `dir`/`rtl` field** (the authoritative **LTR** assertion); the six plural categories;
  and — with **populated resources** — that `resolvedLanguage === 'ar-SA'` with English fallback for
  missing keys. (The standalone node test cannot assert `resolvedLanguage` because empty-resource
  init leaves it `undefined`; that assertion must live here.)
- `tests/i18n-fallback.test.mjs` (node, no Grafana toolchain): a dedicated `i18next.createInstance()`
  proving present-key → Arabic, missing-key → English fallback (`returnEmptyString:false`), empty
  value → English, interpolation survives fallback, and the six Arabic plural forms resolve by count.
- Amended `packages/grafana-i18n/src/languages.test.ts` (pinned list includes `ar-SA`).

## 7. Build (`build.sh.reference`)

Clone the pinned tag → **verify `HEAD` == pinned commit, abort otherwise** → `apply-registration.py`
→ `assemble-ar.py` → install `public/locales/ar-SA/grafana.json` and the alerting package file →
install the registration test → `validate.py --require-complete` → run the node fallback test →
(CI) `yarn install --immutable` + `yarn jest` the registration + languages tests → `docker build`
the Grafana source Dockerfile (OSS build tags) → record image tag + digest.

## 8. Smoke (`smoke.sh.reference`) — the subtle bits

- Verify **through the built output**, not raw JSON assumptions: `ar-SA` appears in the compiled
  `build/*.js` (registration compiled in); the catalog ships (the executable chunk carries the
  Arabic as `\u06xx` escapes — terser escapes non-ASCII — and/or the raw
  `public/locales/ar-SA/grafana.json` is copied into the image); container `/api/health` OK.
- **Do not** grep the minified, single-line bundle with a proximity regex like `ar-SA.*rtl` — every
  RTL locale's data shares that one line, so it always false-positives. LTR is proven by the jest
  test (no `dir`/`rtl` field) and by source: Grafana has **no language→direction mechanism**
  (no `i18next.dir()` / `documentElement.dir` wiring; the only `direction:'rtl'` in the tree is an
  unrelated number-input style).
- Note: the literal Arabic survives in `*.js.map` (source map) and in the raw JSON, while the
  executable `*.js` chunk holds the `\u06xx`-escaped form — check the escaped form or the raw JSON,
  not a literal-string grep over the whole bundle.

## 9. Pitfalls already solved (don't rediscover)

- Missing barrel export of the code constant → test import is `undefined` (fixed by editing
  `index.ts`).
- Applying a plural expansion to a non-plural key → "unauthorized extra key" errors.
- Dropping a protected identifier (`URL`/`UID`) while translating → keep them; add to the allowlist.
- Glossary drift (e.g. `القاعدة` vs `قاعدة`) → validator flags inconsistency; keep terms consistent.
- BSD vs GNU `install -D` differences on macOS vs CI — prefer `mkdir -p && cp` for local mirrors.
- `resolvedLanguage` is `undefined` without a backend/populated resources — assert it in jest, not
  in the standalone node test.
- Minified-bundle RTL regex is unsound (see §8).

## 10. LTR guarantee

Registering `ar-SA` keeps the UI LTR because Grafana has no per-locale direction switch. Keep it so:
never add `dir="rtl"`, a `direction:rtl` binding, an `i18next.dir()` call, or a `documentElement.dir`
assignment for the locale. The `TranslationDefinition` is `{code,name}` (+ app `loader`); nothing may
imply RTL. Confirm on staging that the served shell has no `dir="rtl"` and the layout is unchanged.
