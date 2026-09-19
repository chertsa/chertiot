# grafana-alerting namespace — loader proof (item 3)

**Question (approval item 3):** prove that the `grafana-alerting` package's translations reach `ar-SA`
in the deployed app, and make the smallest native change if the loader doesn't include it.

**Method:** read-only inspection of the pinned source (`v13.1.4`, commit `afdab62…`).

## Findings
1. **The app loads exactly one i18n namespace: `grafana`.**
   `public/app/core/internationalization/constants.ts` derives `NAMESPACES` from the per-language
   `loader` map, and the only loader is `grafana → import('../../../locales/<code>/grafana.json')`.
   `public/app/app.ts` calls `initializeI18n({ ns: NAMESPACES, module: loadTranslations })`, and
   `loadTranslations` can only resolve a namespace that appears in that loader map. `initAlerting.tsx`
   registers **no** i18n namespace or loader.
2. **The alerting UI you actually see is in the `grafana` namespace.** `public/locales/en-US/grafana.json`
   contains **2,086 `alerting.*` leaf keys** (of 10,332 total). The app's alerting feature
   (`public/app/features/alerting/unified/**`) uses the default `grafana` namespace, so translating
   `grafana.json` (which we do, in full) localizes the alerting UI.
3. **The `@grafana/alerting` *package* uses a separate `grafana-alerting` namespace (10 keys)** — its
   `i18next.config.ts` sets `defaultNS: 'grafana-alerting'`, output `src/locales/{{language}}/grafana-alerting.json`.
   Only **en-US** ships (`locales/en-US/grafana-alerting.json`); no other language does — the config
   comment says *"Only en-US is updated - Crowdin will PR with other languages."*
4. **This package namespace is NOT loaded by the main app for ANY language.** At runtime the package's
   `t()`/`Trans` (from `@grafana/i18n`) resolve against the host's default namespace (`grafana`), where
   those ~10 keys are **absent** (verified). With `returnEmptyString:false` + `fallbackLng:en-US`, they
   render from the **inline English default** passed to `t()` — for every language, upstream included.

## Decision (standard, no-workaround, zero-risk)
- We DO translate everything the app renders: the complete `grafana.json`, including all 2,086
  `alerting.*` keys. This is where alerting localization actually takes effect.
- We DO ship `packages/grafana-alerting/src/locales/ar-SA/grafana-alerting.json` for package-locale
  completeness/forward-compatibility (mirrors en-US; validated by `validate.py`). It is additive and
  zero-risk.
- We do **NOT** invent an app-side loader to force-load the `grafana-alerting` namespace. Upstream
  deliberately does not load it in-app for any language; adding a bespoke loader would diverge from a
  frozen upstream for ~10 shared-component strings that upstream itself leaves English in-app. That
  would be a workaround, not a standard change.

## Honest consequence
In the deployed CHERT Grafana, ~10 shared-component strings (e.g. "Paused", "Default policy",
"Hide/Show common labels", the routing-tree selector texts) render in **English** under `ar-SA`,
exactly as they do under every official Crowdin language in 13.1.4. Everything the app renders through
the `grafana` namespace — the entire main UI and the 2,086-key alerting feature — is translated.
