#!/usr/bin/env python3
"""Deep-merge Arabic UI translations into the branded ThingsBoard ar_AR locale (build step, D7).

Adds professional MSA translations (locale-ar_AR-additions.json, flat dotted keys) for newer TB
features whose keys ship untranslated in upstream's Arabic locale. LOCALE-ONLY — display strings
only; nothing in TB's structure, code, or functions changes. Idempotent; validates against en_US so
a stray/renamed key fails the build instead of shipping a dead entry.

Usage: merge-ar-additions.py <path-to-locale.constant-ar_AR.json> [<path-to-locale.constant-en_US.json>]
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _get(d: dict, dotted: str):
    cur = d
    for p in dotted.split("."):
        if not isinstance(cur, dict) or p not in cur:
            return None
        cur = cur[p]
    return cur


def _set(d: dict, dotted: str, val: str) -> None:
    parts = dotted.split(".")
    for p in parts[:-1]:
        nxt = d.get(p)
        if not isinstance(nxt, dict):
            nxt = {}
            d[p] = nxt
        d = nxt
    d[parts[-1]] = val


def main() -> int:
    ar_path = Path(sys.argv[1])
    en_path = Path(sys.argv[2]) if len(sys.argv) > 2 else ar_path.with_name(
        "locale.constant-en_US.json"
    )
    additions = json.loads((HERE / "locale-ar_AR-additions.json").read_text("utf-8"))
    ar = json.loads(ar_path.read_text("utf-8"))
    en = json.loads(en_path.read_text("utf-8")) if en_path.exists() else None

    missing_en = [k for k in additions if en is not None and _get(en, k) is None]
    if missing_en:
        print(f"FAIL: these keys are not in en_US (typo/renamed): {missing_en}", file=sys.stderr)
        return 1

    for dotted, val in additions.items():
        _set(ar, dotted, val)
    ar_path.write_text(json.dumps(ar, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(f"merged {len(additions)} Arabic translations into {ar_path.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
