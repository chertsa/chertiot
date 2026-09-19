#!/usr/bin/env python3
"""Register ar-SA ('العربية') in the Grafana source tree (idempotent; build-time).

Edits the authoritative registry in @grafana/i18n (packages/grafana-i18n/src) — this is where
v13.1.4 keeps the supported-language list (the contribute doc's public/app path is stale). No RTL,
no layout change: TranslationDefinition is {code,name} only, so registering Arabic keeps the UI LTR.

Usage: apply-registration.py <grafana-src-root>
"""

import re
import sys
from pathlib import Path

CODE = "ar-SA"
NAME = "العربية"
CONST = "ARABIC_SAUDI_ARABIA"


def edit(path: Path, transform):
    text = path.read_text("utf-8")
    new = transform(text)
    if new != text:
        path.write_text(new, "utf-8")
        print(f"  updated {path.name}")
    else:
        print(f"  {path.name} already registered (idempotent)")


def main() -> int:
    root = Path(sys.argv[1])
    i18n = root / "packages/grafana-i18n/src"

    # 1) constants.ts — add the code constant after CHINESE_TRADITIONAL.
    def add_const(t: str) -> str:
        if CONST in t:
            return t
        anchor = "export const CHINESE_TRADITIONAL = 'zh-Hant';"
        if anchor not in t:
            raise SystemExit("constants.ts: anchor not found (upstream changed)")
        return t.replace(anchor, f"{anchor}\nexport const {CONST} = '{CODE}';")

    # 2) languages.ts — import the constant and append the LANGUAGES entry.
    def add_language(t: str) -> str:
        if CONST in t:
            return t
        t = t.replace("  TURKISH_TURKEY,\n} from './constants';",
                      f"  TURKISH_TURKEY,\n  {CONST},\n}} from './constants';")
        t = t.replace("  { code: TURKISH_TURKEY, name: 'Türkçe' },\n];",
                      f"  {{ code: TURKISH_TURKEY, name: 'Türkçe' }},\n"
                      f"  {{ code: {CONST}, name: '{NAME}' }},\n];")
        return t

    # 3) languages.test.ts — add ar-SA to the pinned expectedLanguages list.
    def add_test(t: str) -> str:
        if f"code: '{CODE}'" in t:
            return t
        return t.replace("  { code: 'tr-TR', name: 'Türkçe' },\n];",
                         f"  {{ code: 'tr-TR', name: 'Türkçe' }},\n"
                         f"  {{ code: '{CODE}', name: '{NAME}' }},\n];")

    edit(i18n / "constants.ts", add_const)
    edit(i18n / "languages.ts", add_language)
    edit(i18n / "languages.test.ts", add_test)

    # sanity: the code must be canonical and match Grafana's subtag regex
    if not re.match(r"^[a-z]{2}-[a-zA-Z]+$", CODE):
        raise SystemExit(f"{CODE} fails Grafana's locale-code regex")
    print(f"registered {CODE} ({NAME})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
