"""Portal-wide external-runtime dependency guard (CHERT: zero external runtime assets).

Statically inspects every relevant file under portal/app/templates and portal/app/static and
fails if any external runtime destination appears in a runtime-loading context: script src,
stylesheet/link href, image/media src & srcset, iframe/embed/object sources, CSS @import & url(),
JS static/dynamic import, Worker/SharedWorker, service-worker registration, WebSocket, EventSource,
fetch/XHR, and web-app manifests.

A destination is "external" when it is absolute (``https://``, ``http://`` or protocol-relative
``//host``) and its host is not the portal's own origin. Only explicitly approved CHERT-controlled
top-level *navigation* subdomains are allow-listed by exact host prefix; this test does NOT exempt
all anchors, and does NOT exempt all HTTPS URLs.

The vendored, integrity-pinned third-party directory ``static/vendor/`` is excluded from scanning:
those assets are checksum-verified (CHECKSUM.txt), license-recorded (LICENSE.md/SOURCE.txt) and
served locally; the offline test proves they issue no external runtime load.
"""

from __future__ import annotations

import re
from pathlib import Path

APP = Path(__file__).resolve().parents[2] / "app"
SCAN_DIRS = [APP / "templates", APP / "static"]
EXCLUDE_PARTS = {"vendor"}  # static/vendor/** : pinned third-party, verified separately
TEXT_SUFFIXES = {".html", ".htm", ".css", ".js", ".mjs", ".svg", ".json", ".webmanifest", ".xml"}

# The ONLY approved external-looking hosts: CHERT-controlled top-level navigation subdomains,
# always written against the portal's own hostname (e.g. grafana.<portal-host>).
ALLOWED_HOST_PREFIXES = ("grafana.", "status.", "lab.")

# (context name, compiled regex with the URL in group 1)
_CONTEXTS = [
    ("script src", r"""<script\b[^>]*\bsrc\s*=\s*["']([^"']+)["']"""),
    ("link href", r"""<link\b[^>]*\bhref\s*=\s*["']([^"']+)["']"""),
    ("img src", r"""<img\b[^>]*\bsrc\s*=\s*["']([^"']+)["']"""),
    ("iframe/embed/frame src", r"""<(?:iframe|embed|frame)\b[^>]*\bsrc\s*=\s*["']([^"']+)["']"""),
    ("object data", r"""<object\b[^>]*\bdata\s*=\s*["']([^"']+)["']"""),
    ("media src", r"""<(?:source|video|audio|track)\b[^>]*\bsrc\s*=\s*["']([^"']+)["']"""),
    ("svg href", r"""<(?:use|image)\b[^>]*?\b(?:xlink:href|href)\s*=\s*["']([^"']+)["']"""),
    ("anchor href", r"""<a\b[^>]*\bhref\s*=\s*["']([^"']+)["']"""),
    ("css @import", r"""@import\s+(?:url\()?\s*["']?([^"')\s]+)"""),
    ("css url()", r"""url\(\s*["']?([^"')]+?)["']?\s*\)"""),
    ("js import-from", r"""\bimport\b[^;\n]*?\bfrom\s*["']([^"']+)["']"""),
    ("js dynamic import", r"""\bimport\(\s*["']([^"']+)["']"""),
    ("Worker/SharedWorker", r"""new\s+(?:Shared)?Worker\(\s*["']([^"']+)["']"""),
    ("serviceWorker.register", r"""serviceWorker\.register\(\s*["']([^"']+)["']"""),
    ("WebSocket", r"""new\s+WebSocket\(\s*["']([^"']+)["']"""),
    ("EventSource", r"""new\s+EventSource\(\s*["']([^"']+)["']"""),
    ("fetch", r"""\bfetch\(\s*["']([^"']+)["']"""),
    ("XHR open", r"""\.open\(\s*["'][A-Za-z]+["']\s*,\s*["']([^"']+)["']"""),
]
CONTEXTS = [(name, re.compile(rx, re.IGNORECASE)) for name, rx in _CONTEXTS]
_SRCSET = re.compile(r"""\bsrcset\s*=\s*["']([^"']+)["']""", re.IGNORECASE)
_ABSOLUTE = re.compile(r"^\s*(?:https?:)?//", re.IGNORECASE)


def _iter_files() -> list[Path]:
    files: list[Path] = []
    for root in SCAN_DIRS:
        if not root.exists():
            continue
        for p in root.rglob("*"):
            if not p.is_file() or p.suffix.lower() not in TEXT_SUFFIXES:
                continue
            if EXCLUDE_PARTS & set(p.relative_to(root).parts):
                continue
            files.append(p)
    return files


def _is_external(url: str) -> bool:
    """True when the URL is an absolute/protocol-relative destination outside CHERT's own origin."""
    url = url.strip()
    if url.startswith("data:"):
        return False
    if not _ABSOLUTE.match(url):
        # relative, root-relative (/static/...), fragment, mailto:, tel:, or templated path
        return False
    host = re.sub(r"^\s*(?:https?:)?//", "", url, flags=re.IGNORECASE).split("/")[0].lower()
    return not host.startswith(ALLOWED_HOST_PREFIXES)


def _urls_in(text: str) -> list[tuple[str, str]]:
    hits: list[tuple[str, str]] = []
    for name, rx in CONTEXTS:
        for m in rx.finditer(text):
            hits.append((name, m.group(1)))
    for m in _SRCSET.finditer(text):  # comma-separated "url descriptor" candidates
        for candidate in m.group(1).split(","):
            token = candidate.strip().split()[0] if candidate.strip() else ""
            if token:
                hits.append(("srcset", token))
    return hits


def test_no_external_runtime_assets() -> None:
    violations: list[str] = []
    for path in _iter_files():
        text = path.read_text("utf-8", errors="replace")
        for context, url in _urls_in(text):
            if _is_external(url):
                violations.append(f"{path.relative_to(APP.parent)}: [{context}] -> {url}")
    assert not violations, "External runtime asset destination(s) found:\n" + "\n".join(
        sorted(set(violations))
    )


def test_no_cdnjs_reference_anywhere() -> None:
    """Belt-and-braces: the retired cdnjs Chart.js dependency must not reappear."""
    offenders = [
        str(p.relative_to(APP.parent))
        for p in _iter_files()
        if "cdnjs.cloudflare.com" in p.read_text("utf-8", errors="replace")
    ]
    assert not offenders, f"cdnjs.cloudflare.com reference(s) found: {offenders}"
