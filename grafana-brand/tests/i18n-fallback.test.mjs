import i18next from 'i18next';

// Grafana's init options (packages/grafana-i18n/src/i18n.tsx): partialBundledLanguages,
// returnEmptyString:false, fallbackLng:'en-US', ns:['grafana']. lng='ar-SA' (the new locale).
// Use a dedicated instance and await init so resolvedLanguage is populated deterministically.
const i18n = i18next.createInstance();
await i18n.init({
  partialBundledLanguages: true,
  resources: {},
  returnEmptyString: false,
  fallbackLng: 'en-US',
  supportedLngs: ['en-US', 'ar-SA'],
  ns: ['grafana'],
  defaultNS: 'grafana',
  lng: 'ar-SA',
});

// en-US is embedded in source (loadTranslations skips loading it) — represent that fully.
i18n.addResourceBundle('en-US', 'grafana', {
  present: 'Dashboards',
  onlyEnglish: 'Only in English',
  emptyInArabic: 'English (arabic empty)',
  greet: 'Hello {{name}}',
  missingWithVar: 'Deleted user {{user}}',
  items_one: '{{count}} item',
  items_other: '{{count}} items',
  files_one: '{{count}} file',
  files_other: '{{count}} files',
}, /*deep*/ true, /*overwrite*/ false);

// ar-SA: partial — 'present' translated, 'emptyInArabic' empty, 'onlyEnglish'/'missingWithVar' ABSENT.
// 'items' provides all 6 Arabic CLDR forms; 'files' is ABSENT in ar (must fall back to en plural).
i18n.addResourceBundle('ar-SA', 'grafana', {
  present: 'لوحات المعلومات',
  emptyInArabic: '',
  greet: 'مرحبًا {{name}}',
  items_zero: 'لا عناصر',
  items_one: 'عنصر واحد',
  items_two: 'عنصران',
  items_few: '{{count}} عناصر',
  items_many: '{{count}} عنصرًا',
  items_other: '{{count}} عنصر',
}, /*deep*/ true, /*overwrite*/ false);

const t = i18n.getFixedT('ar-SA', 'grafana');
let failures = 0;
const line = (label, val, expect) => {
  const ok = val === expect;
  if (!ok) failures++;
  console.log(`${ok ? 'PASS' : 'FAIL'} | ${label} => "${val}"  (expected "${expect}")`);
};

// Note: resolvedLanguage stays undefined here because this instance has no backend and empty
// bundled resources (partialBundledLanguages) — it is populated only after an async backend load.
// The authoritative resolvedLanguage === 'ar-SA' assertion lives in registration.ar-SA.test.tsx,
// which runs in Grafana's real i18n environment. This file proves fallback + plural behavior.
console.log('resolvedLanguage(info):', i18n.resolvedLanguage, '| plural categories(ar):',
  new Intl.PluralRules('ar').resolvedOptions().pluralCategories.join(','));
console.log('--- 1) present ar-SA key returns Arabic ---');
line('t(present)', t('present'), 'لوحات المعلومات');
console.log('--- 2) missing ar-SA key falls back to English ---');
line('t(onlyEnglish)', t('onlyEnglish'), 'Only in English');
console.log('--- 3) empty Arabic value falls back to English (returnEmptyString:false) ---');
line('t(emptyInArabic)', t('emptyInArabic'), 'English (arabic empty)');
console.log('--- 4) interpolation survives fallback ---');
line('t(missingWithVar, user=Alice)', t('missingWithVar', { user: 'Alice' }), 'Deleted user Alice');
line('t(greet arabic, name=Sara)', t('greet', { name: 'Sara' }), 'مرحبًا Sara');
console.log('--- 5) Arabic plural forms resolve by count ---');
line('items count=0', t('items', { count: 0 }), 'لا عناصر');
line('items count=1', t('items', { count: 1 }), 'عنصر واحد');
line('items count=2', t('items', { count: 2 }), 'عنصران');
line('items count=3', t('items', { count: 3 }), '3 عناصر');
line('items count=11', t('items', { count: 11 }), '11 عنصرًا');
line('items count=100', t('items', { count: 100 }), '100 عنصر');
console.log('--- 5b) plural group ABSENT in ar falls back to English plural ---');
line('files count=1 (en fallback)', t('files', { count: 1 }), '1 file');
line('files count=5 (en fallback)', t('files', { count: 5 }), '5 files');

console.log(`\n${failures === 0 ? 'ALL PASS' : failures + ' FAILED'}`);
process.exit(failures === 0 ? 0 : 1);
