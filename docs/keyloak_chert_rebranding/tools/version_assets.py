#!/usr/bin/env python3
"""Stamp content-hash versions (?v=<sha256[:10]>) on every CHERT login-theme asset reference.

Why: Keycloak serves theme resources at /resources/<keycloak-build>/login/<theme>/... with
`cache-control: max-age=2592000` (30 days) and that path does NOT change when the theme changes.
Without a per-content version, browsers keep the previous CSS/JS/icons for a month and render new
markup with old styles. Run this after ANY change under resources/ (apply_project.py runs it).

Usage:  python3 tools/version_assets.py <path-to-theme>/login        (rewrites in place)
        python3 tools/version_assets.py <path-to-theme>/login --check  (exit 1 if stale; for CI)
"""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:10]


def stamp(login_dir: Path, check: bool = False) -> list[str]:
    res = login_dir / "resources"
    changes: list[str] = []

    props = login_dir / "theme.properties"
    text = props.read_text("utf-8")

    def props_line(m: re.Match[str]) -> str:
        key, refs = m.group(1), m.group(2).split()
        out = []
        for ref in refs:
            path = ref.split("?v=", 1)[0]
            new = f"{path}?v={digest(res / path)}"
            if new != ref:
                changes.append(f"theme.properties {key}: {ref} -> {new}")
            out.append(new)
        return f"{key}={' '.join(out)}"

    new_props = re.sub(r"^(styles|scripts)=(.+)$", props_line, text, flags=re.M)

    ftl = login_dir / "template.ftl"
    ftl_text = ftl.read_text("utf-8")

    def ftl_ref(m: re.Match[str]) -> str:
        path = m.group(1)
        # Only this theme's own files. Template variables (${style}) and files inherited from the
        # parent keycloak.v2 theme (js/passwordVisibility.js, js/authChecker.js) are left untouched.
        if "${" in path or not (res / path).is_file():
            return m.group(0)
        new = f"${{url.resourcesPath}}/{path}?v={digest(res / path)}"
        if new != m.group(0):
            changes.append(f"template.ftl: {path} -> ?v={digest(res / path)}")
        return new

    new_ftl = re.sub(r"\$\{url\.resourcesPath\}/([^\"'?\s]+)(?:\?v=[0-9a-f]*)?", ftl_ref, ftl_text)

    if not check:
        props.write_text(new_props, "utf-8")
        ftl.write_text(new_ftl, "utf-8")
    return changes


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    login = Path(sys.argv[1]).resolve()
    check = "--check" in sys.argv[2:]
    changed = stamp(login, check=check)
    for line in changed:
        print(("STALE  " if check else "stamped ") + line)
    if check and changed:
        sys.exit(1)
    if not changed:
        print("all asset versions current")
