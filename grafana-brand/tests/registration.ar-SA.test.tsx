// CHERT ar-SA registration test. Installed by build.sh into
// public/app/core/internationalization/ and run by Grafana's jest in CI (images.yml).
// Complements: upstream languages.test.ts (pinned expected-language list, amended to include ar-SA)
// and grafana-brand/tests/i18n-fallback.test.mjs (runtime fallback + Arabic plural resolution).
import i18next from 'i18next';

import { ARABIC_SAUDI_ARABIA } from '@grafana/i18n';

import { LANGUAGES, VALID_LANGUAGES, NAMESPACES, GRAFANA_NAMESPACE } from './constants';

describe('CHERT ar-SA locale registration', () => {
  const def = LANGUAGES.find((l) => l.code === 'ar-SA');

  it('exposes the ARABIC_SAUDI_ARABIA constant as the canonical BCP-47 code', () => {
    expect(ARABIC_SAUDI_ARABIA).toBe('ar-SA');
    expect(Intl.getCanonicalLocales('ar-SA')[0]).toBe('ar-SA');
    const loc = new Intl.Locale('ar-SA');
    expect(loc.language).toBe('ar');
    expect(loc.region).toBe('SA');
  });

  it('is registered as a supported language named العربية', () => {
    expect(VALID_LANGUAGES).toContain('ar-SA');
    expect(def).toBeDefined();
    expect(def!.name).toBe('العربية');
  });

  it('has a grafana-namespace loader (so webpack bundles public/locales/ar-SA/grafana.json)', () => {
    expect(NAMESPACES).toContain(GRAFANA_NAMESPACE);
    expect(typeof def!.loader[GRAFANA_NAMESPACE]).toBe('function');
  });

  it('is LTR: the definition carries no direction/rtl field (Grafana has no per-locale dir)', () => {
    // TranslationDefinition is { code, name }; app adds { loader }. Nothing may imply RTL.
    expect(Object.keys(def!).sort()).toEqual(['code', 'loader', 'name']);
    expect('dir' in def!).toBe(false);
    expect('rtl' in def!).toBe(false);
  });

  it('resolves the six Arabic CLDR plural categories (validator enforces all six per group)', () => {
    const cats = new Intl.PluralRules('ar-SA').resolvedOptions().pluralCategories.sort();
    expect(cats).toEqual(['few', 'many', 'one', 'other', 'two', 'zero']);
  });

  // The authoritative resolvedLanguage assertion the standalone (undefined) result cannot give.
  it("resolves ar-SA as the active resolvedLanguage, with English fallback for missing keys", async () => {
    const inst = i18next.createInstance();
    await inst.init({
      lng: 'ar-SA',
      fallbackLng: 'en-US',
      supportedLngs: VALID_LANGUAGES,
      returnEmptyString: false,
      ns: ['grafana'],
      defaultNS: 'grafana',
      resources: {
        'en-US': { grafana: { present: 'Dashboards', onlyEnglish: 'Only in English' } },
        'ar-SA': { grafana: { present: 'لوحات المعلومات' } },
      },
    });
    // Registered + selected: the active language is exactly ar-SA (not a fallback).
    expect(inst.resolvedLanguage).toBe('ar-SA');
    // A present ar-SA key returns Arabic…
    expect(inst.t('present')).toBe('لوحات المعلومات');
    // …and a key missing from ar-SA falls back to the English value.
    expect(inst.t('onlyEnglish')).toBe('Only in English');
  });
});
