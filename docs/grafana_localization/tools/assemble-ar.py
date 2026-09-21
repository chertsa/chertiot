#!/usr/bin/env python3
"""Assemble grafana-brand/locales/ar-SA/grafana.json from per-namespace Arabic subtrees.

The ar-SA translation is produced namespace-by-namespace (208 top-level namespaces). Each
translated namespace is COMMITTED to the repository as one JSON file
  grafana-brand/locales/ar-SA/namespaces/<namespace>.json
holding exactly that namespace's Arabic subtree (same shape as the English subtree, with English
plural groups expanded to the six Arabic CLDR forms). This is the durable source of truth — never
a scratchpad/tmp copy. This script rebuilds the single authoritative catalog
  grafana-brand/locales/ar-SA/grafana.json
from whatever namespaces are present — order-independent, idempotent, resumable across sessions —
and prints coverage vs the English source so progress is auditable. English extracts are upstream,
not Arabic source-of-truth, so the en file may live in a disposable build clone.

Usage:
  assemble-ar.py <en-grafana.json> [ns-dir] [out]
    ns-dir defaults to <repo>/grafana-brand/locales/ar-SA/namespaces
    out    defaults to <repo>/grafana-brand/locales/ar-SA/grafana.json
  optional flag: --report-only  (compute coverage without writing the catalog)
"""
import json, sys
from pathlib import Path

PL = ("_zero", "_one", "_two", "_few", "_many", "_other")
REPO = Path(__file__).resolve().parents[2]           # <repo>
NS_DIR_DEFAULT = REPO / "grafana-brand/locales/ar-SA/namespaces"
OUT_DEFAULT = REPO / "grafana-brand/locales/ar-SA/grafana.json"


def leaves(d):
    n = 0
    for v in d.values():
        n += leaves(v) if isinstance(v, dict) else 1
    return n


def ar_expected(d):
    """expected ar leaf count for an English subtree: non-plural 1:1; each en group -> 6."""
    groups, nonpl = set(), 0

    def walk(o, p=""):
        nonlocal nonpl
        for k, v in o.items():
            kp = f"{p}.{k}" if p else k
            if isinstance(v, dict):
                walk(v, kp)
            else:
                hit = next((s for s in PL if k.endswith(s)), None)
                if hit:
                    groups.add(kp[: -len(hit)])
                else:
                    nonpl += 1

    walk(d)
    return nonpl + 6 * len(groups)


def main():
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    report_only = "--report-only" in sys.argv
    en_path = Path(a[0])
    ns_dir = Path(a[1]) if len(a) > 1 else NS_DIR_DEFAULT
    out_path = Path(a[2]) if len(a) > 2 else OUT_DEFAULT
    en = json.loads(en_path.read_text("utf-8"))
    done, out, done_leaf, exp_leaf = [], {}, 0, 0
    for ns in sorted(en):
        exp = ar_expected(en[ns]) if isinstance(en[ns], dict) else 1
        exp_leaf += exp
        f = ns_dir / f"{ns}.json"
        if f.exists():
            sub = json.loads(f.read_text("utf-8"))
            out[ns] = sub
            done.append(ns)
            done_leaf += leaves(sub) if isinstance(sub, dict) else 1
    if not report_only:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(f"namespaces: {len(done)}/{len(en)} done")
    print(f"ar leaf keys assembled: {done_leaf}/{exp_leaf}")
    pct = 100 * done_leaf / exp_leaf if exp_leaf else 0
    print(f"coverage: {pct:.1f}%")
    remaining = [ns for ns in sorted(en) if not (ns_dir / f"{ns}.json").exists()]
    print(f"remaining namespaces ({len(remaining)}): "
          + ", ".join(remaining[:12]) + (" ..." if len(remaining) > 12 else ""))


if __name__ == "__main__":
    main()
