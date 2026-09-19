#!/usr/bin/env python3
"""Schema-aware validator for CHERT's Grafana ar-SA locale (D7). LOCALE-ONLY; no TB/Grafana code.

Not a naive "no added keys" diff — Arabic legitimately expands each English plural group into the
six CLDR categories. This validator:
  * requires every non-plural English key exactly once in Arabic;
  * identifies plural groups semantically and requires EXACTLY the 6 Arabic categories per group;
  * rejects unrelated/extra keys and missing plural forms;
  * verifies interpolation vars {{x}} and indexed tags <n>/<n/> are preserved per form;
  * flags invalid JSON, empty Arabic, Arabic == English (except allowlisted identifiers),
    bidi-control chars, accidentally-translated protected identifiers, and glossary inconsistency.

Usage:
  validate.py <grafana-src-root> [--require-complete]     # validates the standard file pairs
  validate.py --pair <en.json> <ar.json> [--require-complete]   # validate one pair (self-test)
"""

import json
import re
import sys
from pathlib import Path

AR_CATEGORIES = ("zero", "one", "two", "few", "many", "other")
EN_PLURAL_SUFFIXES = ("_zero", "_one", "_two", "_few", "_many", "_other")
VAR_RE = re.compile(r"\{\{[^}]+\}\}")
TAG_RE = re.compile(r"</?\d+/?>")
BIDI_RE = re.compile("[‎‏‪-‮⁦-⁩؜]")
# Identifiers that must stay Latin; if present in EN they must remain in AR.
PROTECTED = ["Grafana", "Prometheus", "Loki", "MQTT", "HTTP", "HTTPS", "JSON", "SQL", "API",
             "URL", "UID", "CPU", "RAM", "TBEL", "OAuth", "Kafka", "Redis", "gRPC"]
# EN values equal to one of these may legitimately be identical in AR (kept Latin): protected
# identifiers plus format/query-language/protocol/product tokens that are conventionally not
# translated in an Arabic UI.
IDENTICAL_OK = set(PROTECTED) | {
    "Grafana", "Prometheus", "Loki", "API", "JSON", "URL", "UID", "SQL", "HTTP", "MQTT",
    "CPU", "RAM", "OK", "ID",
    "HTML", "Markdown", "CSV", "TSV", "XML", "YAML", "YML", "PDF", "PNG", "SVG", "JPEG",
    "GeoJSON", "PromQL", "LogQL", "TraceQL", "UTC", "LDAP", "SAML", "OAuth2", "JWT", "gRPC",
    "GET", "POST", "PUT", "PATCH", "DELETE", "InfluxDB", "Graphite", "Tempo", "Pyroscope",
    "Grafana Cloud", "Grafana Enterprise", "Grafana Labs", "Grafana Alerting", "Grafana Assistant",
    "Grafana Live", "Grafana Play", "Geohash", "GeoJSON",
    "Cloud", "Enterprise",  # Grafana edition/tier badge labels, kept as the product tier name
    "Bind DN", "Search base DNS",  # standard LDAP field names, conventionally kept Latin
    "RTL", "LTR",  # direction acronyms used as compact option labels
}
# Duration/interval literals (Grafana's own input syntax) are code, not prose — kept identical.
DURATION_RE = re.compile(r"^\d+(?:\.\d+)?(?:ns|µs|us|ms|s|m|h|d|w|y|M)$")
GLOSSARY = {
    "dashboard": "لوحة المعلومات", "panel": "لوحة عرض", "data source": "مصدر البيانات",
    "query": "استعلام", "alert": "تنبيه", "alerting": "التنبيهات", "alert rule": "قاعدة تنبيه",
    "rule": "قاعدة", "folder": "مجلد", "organization": "منظمة", "user": "مستخدم",
    "explore": "استكشاف", "variable": "متغير", "annotation": "تعليق زمني",
    "transformation": "تحويل", "threshold": "عتبة", "provisioning": "التهيئة التلقائية",
    "team": "فريق", "service account": "حساب خدمة", "preferences": "التفضيلات",
    "settings": "الإعدادات", "save": "حفظ", "apply": "تطبيق", "cancel": "إلغاء",
    "delete": "حذف", "edit": "تعديل", "search": "بحث", "sign in": "تسجيل الدخول",
    "sign out": "تسجيل الخروج",
}


def flatten(obj, prefix=""):
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.update(flatten(v, f"{prefix}.{k}" if prefix else k))
    else:
        out[prefix] = obj
    return out


def base_and_suffix(dotted):
    seg = dotted.rsplit(".", 1)[-1]
    for s in EN_PLURAL_SUFFIXES:
        if seg.endswith(s):
            return dotted[: -len(s)], s[1:]
    return None, None


def tokens(s):
    return (frozenset(VAR_RE.findall(s)), frozenset(TAG_RE.findall(s))) if isinstance(s, str) else (frozenset(), frozenset())


def validate_pair(en_path: Path, ns: str, ar_path: Path, require_complete: bool):
    errors, warnings = [], []
    try:
        en = flatten(json.loads(en_path.read_text("utf-8")))
    except json.JSONDecodeError as e:
        return [f"[{ns}] en-US invalid JSON: {e}"], []
    if not ar_path.exists():
        return ([f"[{ns}] missing Arabic file {ar_path}"] if require_complete else []), \
               ([] if require_complete else [f"[{ns}] Arabic file not present yet: {ar_path}"])
    try:
        ar = flatten(json.loads(ar_path.read_text("utf-8")))
    except json.JSONDecodeError as e:
        return [f"[{ns}] ar-SA invalid JSON: {e}"], []

    # classify EN into plural groups + non-plural, and build the expected AR key set
    groups, nonplural = {}, []
    for k, v in en.items():
        b, suf = base_and_suffix(k)
        if b is not None:
            groups.setdefault(b, {})[suf] = v
        else:
            nonplural.append(k)
    expected = set(nonplural)
    for b in groups:
        for c in AR_CATEGORIES:
            expected.add(f"{b}_{c}")

    # 1) missing (required) keys
    for k in sorted(expected - set(ar)):
        (errors if require_complete else warnings).append(f"[{ns}] missing ar key: {k}")
    # 2) unauthorized extra keys
    for k in sorted(set(ar) - expected):
        errors.append(f"[{ns}] unauthorized extra ar key: {k}")

    # per-value checks
    for k, av in ar.items():
        if k not in expected:
            continue
        # source EN value for token comparison
        b, suf = base_and_suffix(k)
        if b is not None:
            en_src = groups.get(b, {})
            en_vars = frozenset().union(*[tokens(x)[0] for x in en_src.values()]) if en_src else frozenset()
            en_tags = frozenset().union(*[tokens(x)[1] for x in en_src.values()]) if en_src else frozenset()
            en_val = en_src.get("other") or en_src.get("one") or ""
        else:
            en_vars, en_tags = tokens(en.get(k, ""))
            en_val = en.get(k, "")
        if isinstance(av, str) and av.strip() == "":
            # An empty Arabic value is only wrong when the English source has text to translate.
            if not (isinstance(en_val, str) and en_val.strip() == ""):
                errors.append(f"[{ns}] empty ar value: {k}")
            continue
        av_vars, av_tags = tokens(av)
        if b is not None:
            # Plural form: i18next injects {{count}} implicitly, and some Arabic categories
            # (zero/two) read better without spelling the number. So {{count}} is optional per
            # form, but every NON-count variable must survive and no new variable may appear.
            required = en_vars - {"{{count}}"}
            if not (required <= av_vars <= en_vars):
                errors.append(f"[{ns}] {k}: interpolation vars differ en={sorted(en_vars)} ar={sorted(av_vars)}")
            if not (av_tags <= en_tags):
                errors.append(f"[{ns}] {k}: indexed tags differ en={sorted(en_tags)} ar={sorted(av_tags)}")
        else:
            if av_vars != en_vars:
                errors.append(f"[{ns}] {k}: interpolation vars differ en={sorted(en_vars)} ar={sorted(av_vars)}")
            if av_tags != en_tags:
                errors.append(f"[{ns}] {k}: indexed tags differ en={sorted(en_tags)} ar={sorted(av_tags)}")
        if BIDI_RE.search(av if isinstance(av, str) else ""):
            errors.append(f"[{ns}] {k}: contains bidi-control character")
        if isinstance(av, str) and isinstance(en_val, str) and av == en_val and en_val.strip() and en_val not in IDENTICAL_OK:
            # Skip values with no translatable text once {{vars}}/tags are removed (punctuation,
            # numbers, or interpolation-only strings are legitimately identical).
            stripped = TAG_RE.sub("", VAR_RE.sub("", en_val))
            toks = [t for t in re.split(r"[,\s]+", en_val.strip()) if t]
            all_durations = bool(toks) and all(DURATION_RE.match(t) for t in toks)
            if re.search(r"[A-Za-z]", stripped) and not all_durations:
                warnings.append(f"[{ns}] {k}: ar identical to en ('{en_val[:40]}')")
        if isinstance(en_val, str) and isinstance(av, str):
            for p in PROTECTED:
                if p in en_val and p not in av:
                    errors.append(f"[{ns}] {k}: protected identifier '{p}' missing/translated in ar")
        # glossary consistency: EN value that IS a glossary term must use the glossary Arabic
        if isinstance(en_val, str) and en_val.strip().lower() in GLOSSARY and isinstance(av, str):
            want = GLOSSARY[en_val.strip().lower()]
            if av.strip() != want:
                warnings.append(f"[{ns}] {k}: '{en_val}' should be '{want}', got '{av}'")
    return errors, warnings


def main() -> int:
    args = sys.argv[1:]
    require = "--require-complete" in args
    args = [a for a in args if a != "--require-complete"]
    pairs = []
    if args and args[0] == "--pair":
        pairs = [(Path(args[1]), "test", Path(args[2]))]
    else:
        root = Path(args[0])
        pairs = [
            (root / "public/locales/en-US/grafana.json", "grafana",
             root / "public/locales/ar-SA/grafana.json"),
            (root / "packages/grafana-alerting/src/locales/en-US/grafana-alerting.json",
             "grafana-alerting",
             root / "packages/grafana-alerting/src/locales/ar-SA/grafana-alerting.json"),
        ]
    all_err, all_warn = [], []
    for en_path, ns, ar_path in pairs:
        e, w = validate_pair(en_path, ns, ar_path, require)
        all_err += e
        all_warn += w
    for w in all_warn[:50]:
        print("WARN:", w)
    for e in all_err[:100]:
        print("ERROR:", e)
    print(f"\n{len(all_err)} error(s), {len(all_warn)} warning(s)"
          + ("" if all_warn[:50] == all_warn else " (truncated)"))
    return 1 if all_err else 0


if __name__ == "__main__":
    sys.exit(main())
