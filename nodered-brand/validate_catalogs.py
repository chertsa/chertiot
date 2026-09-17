#!/usr/bin/env python3
"""Arabic (ar-AR) ↔ English (en-US) Node-RED catalog parity + LTR guard.

Fails (exit 1) when the committed ar-AR catalogs drift from the reference en-US catalogs of the
pinned Node-RED image, or when an RTL marker sneaks into the brand layer. Run in CI and locally:

    python3 nodered-brand/validate_catalogs.py            # uses the vendored en-US reference
    NODE_RED_IMAGE=nodered/node-red:5.0.6 ... (reference refreshed out-of-band)

The en-US reference lives beside this script (nodered-brand/reference/en-US/) and is refreshed only
when the Node-RED pin changes (frozen ⇒ ~never). Stdlib only — no test stack pulled in (prompt §5)."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
AR_DIR = HERE / "locales" / "ar-AR"
EN_DIR = HERE / "reference" / "en-US"
FILES = ("editor.json", "infotips.json", "jsonata.json")

# Node-RED interpolation (__name__), i18next namespaced actions ({{core:search}} / {{ x }}),
# and keyboard tokens ([ctrl], [left]) must survive translation unchanged.
TOK_INTERP = re.compile(r"__[a-zA-Z0-9_]+__")
TOK_MUSTACHE = re.compile(r"\{\{[^}]+\}\}")
TOK_KEYCAP = re.compile(r"\[[a-zA-Z]+\]")
TOK_HTML = re.compile(r"</?[a-zA-Z][^>]*>")
TOK_URL = re.compile(r"https?://[^\s\"'<>]+")
# Bidi / direction-control characters are forbidden inside translated strings (prompt §4).
BIDI_CTRL = re.compile(r"[‎‏‪-‮⁦-⁩]")
# Common "not yet translated" sentinels.
SENTINELS = ("TODO", "FIXME", "XXX", "<<", ">>", "�")

errors: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


def flatten(obj: object, prefix: str = "") -> dict[str, object]:
    out: dict[str, object] = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.update(flatten(v, f"{prefix}.{k}" if prefix else k))
    else:
        out[prefix] = obj
    return out


def tokens(s: str) -> dict[str, list[str]]:
    return {
        "interp": sorted(TOK_INTERP.findall(s)),
        "mustache": sorted(TOK_MUSTACHE.findall(s)),
        "keycap": sorted(TOK_KEYCAP.findall(s)),
        "html": sorted(TOK_HTML.findall(s)),
        "url": sorted(TOK_URL.findall(s)),
    }


def check_file(name: str) -> None:
    ar_path, en_path = AR_DIR / name, EN_DIR / name
    if not ar_path.exists():
        err(f"{name}: missing ar-AR catalog at {ar_path}")
        return
    raw = ar_path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        err(f"{name}: has a UTF-8 BOM (forbidden)")
    try:
        ar = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        err(f"{name}: not valid UTF-8 JSON: {e}")
        return
    en = json.loads(en_path.read_text("utf-8"))

    fa, fe = flatten(ar), flatten(en)
    # editor.json legitimately adds the ar-AR self-label; that one extra key is allowed everywhere.
    allowed_extra = {"languages.ar-AR"}
    missing = set(fe) - set(fa)
    extra = set(fa) - set(fe) - allowed_extra
    for k in sorted(missing):
        err(f"{name}: missing key present in en-US: {k}")
    for k in sorted(extra):
        err(f"{name}: unexpected key not in en-US: {k}")

    for k in sorted(set(fa) & set(fe)):
        av, ev = fa[k], fe[k]
        if type(av) is not type(ev):
            err(f"{name}:{k}: type {type(av).__name__} != en-US {type(ev).__name__}")
            continue
        if isinstance(av, str):
            if BIDI_CTRL.search(av):
                err(f"{name}:{k}: contains a Unicode bidi/direction-control character")
            for s in SENTINELS:
                if s in av:
                    err(f"{name}:{k}: contains sentinel/replacement marker {s!r}")
            if tokens(av) != tokens(ev):
                err(f"{name}:{k}: protected tokens diverge from en-US\n"
                    f"      en-US: {tokens(ev)}\n      ar-AR: {tokens(av)}")

    # JSONata arg signatures live in jsonata.json under *.args — must be byte-identical to en-US.
    if name == "jsonata.json":
        for k in sorted(fe):
            if k.endswith(".args") and fa.get(k) != fe.get(k):
                err(f"{name}:{k}: JSONata argument signature changed (must match en-US exactly)")


def check_language_registration() -> None:
    ar = json.loads((AR_DIR / "editor.json").read_text("utf-8"))
    label = (ar.get("languages") or {}).get("ar-AR")
    if label != "العربية":
        err(f"ar-AR/editor.json: languages.ar-AR must be 'العربية', got {label!r}")
    # en-US reference must gain the label too — enforced on the built image, checked here on source.
    en = json.loads((EN_DIR / "editor.json").read_text("utf-8"))
    if "ar-AR" not in (en.get("languages") or {}):
        # reference is upstream-pristine; the Dockerfile transform adds it. Informational only.
        print("note: en-US reference has no ar-AR label (added by the image build transform)")


def check_no_rtl() -> None:
    """Static guard: nothing in the brand layer may introduce RTL (prompt §4)."""
    for p in HERE.rglob("*"):
        if not p.is_file() or p.suffix not in (".json", ".js", ".css", ".html", "", ".Dockerfile"):
            continue
        if p.name == Path(__file__).name:
            continue
        try:
            text = p.read_text("utf-8", errors="ignore")
        except OSError:
            continue
        for pat in ('dir="rtl"', "dir='rtl'", "[dir=rtl]", '[dir="rtl"]', "direction:rtl",
                    "direction: rtl"):
            if pat in text:
                err(f"{p.relative_to(HERE)}: RTL marker {pat!r} is forbidden (LTR-only)")


def main() -> int:
    if not EN_DIR.exists():
        print(f"FAIL: en-US reference missing at {EN_DIR}", file=sys.stderr)
        return 1
    for f in FILES:
        check_file(f)
    check_language_registration()
    check_no_rtl()
    if errors:
        print(f"FAIL: {len(errors)} catalog issue(s):\n", file=sys.stderr)
        for e in errors:
            print("  - " + e, file=sys.stderr)
        return 1
    print("OK: ar-AR catalogs match en-US (keys, types, tokens), registered, LTR-only.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
