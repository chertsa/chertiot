"""Portal-wide external-runtime dependency guard (CHERT: zero external runtime assets).

Statically inspects every relevant file under portal/app/templates and portal/app/static and fails
if any external runtime destination appears in a runtime-loading context: script src,
stylesheet/link href, image/media src & srcset, iframe/embed/object sources, CSS @import & url(),
JS static/dynamic import, Worker/SharedWorker, service-worker registration, WebSocket, EventSource,
fetch/XHR, and web-app manifests. Contexts are applied by file type so inert strings (SVG xmlns,
comment URLs) are not misread as loads.

A destination is external when ``urllib.parse.urlparse`` yields an absolute or protocol-relative URL
(scheme http/https/ws/wss, or a bare ``//host``). Only three EXACT CHERT-controlled HTTPS navigation
netlocs are allowed, and only in an anchor (navigation) context — there is NO prefix-based approval,
so a lookalike such as ``evil.grafana.com`` fails.

Executable files inside ``static/vendor/`` ARE scanned (a vendored library must not smuggle an
external runtime load). Only provenance/record files (LICENSE, SOURCE, CHECKSUM) are excluded.
"""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

APP = Path(__file__).resolve().parents[2] / "app"
SCAN_DIRS = [APP / "templates", APP / "static"]
SCANNABLE_SUFFIXES = {
    ".html",
    ".htm",
    ".css",
    ".js",
    ".mjs",
    ".svg",
    ".json",
    ".webmanifest",
    ".xml",
}
PROVENANCE_STEMS = {"license", "source", "checksum"}  # LICENSE.md, SOURCE.txt, CHECKSUM.txt only

# The ONLY approved external-looking destinations: exact CHERT-controlled HTTPS navigation netlocs,
# written against the portal's own hostname. Matched EXACTLY (no startswith), anchor context only.
ALLOWED_NAV_NETLOCS = {
    "grafana.{{ request.url.hostname }}",
    "status.{{ request.url.hostname }}",
    "lab.{{ request.url.hostname }}",
}
_ABSOLUTE_SCHEMES = {"http", "https", "ws", "wss"}

_HTML_CTX = [
    ("script src", r"""<script\b[^>]*\bsrc\s*=\s*["']([^"']+)["']"""),
    ("link href", r"""<link\b[^>]*\bhref\s*=\s*["']([^"']+)["']"""),
    ("img src", r"""<img\b[^>]*\bsrc\s*=\s*["']([^"']+)["']"""),
    ("iframe/embed/frame src", r"""<(?:iframe|embed|frame)\b[^>]*\bsrc\s*=\s*["']([^"']+)["']"""),
    ("object data", r"""<object\b[^>]*\bdata\s*=\s*["']([^"']+)["']"""),
    ("media src", r"""<(?:source|video|audio|track)\b[^>]*\bsrc\s*=\s*["']([^"']+)["']"""),
    ("svg href", r"""<(?:use|image)\b[^>]*?\b(?:xlink:href|href)\s*=\s*["']([^"']+)["']"""),
    ("anchor href", r"""<a\b[^>]*\bhref\s*=\s*["']([^"']+)["']"""),
]
_CSS_CTX = [
    ("css @import", r"""@import\s+(?:url\()?\s*["']?([^"')\s]+)"""),
    ("css url()", r"""url\(\s*["']?([^"')]+?)["']?\s*\)"""),
]
_JS_CTX = [
    ("js import-from", r"""\bimport\b[^;\n]*?\bfrom\s*["']([^"']+)["']"""),
    ("js dynamic import", r"""\bimport\(\s*["']([^"']+)["']"""),
    ("Worker/SharedWorker", r"""new\s+(?:Shared)?Worker\(\s*["']([^"']+)["']"""),
    ("serviceWorker.register", r"""serviceWorker\.register\(\s*["']([^"']+)["']"""),
    ("WebSocket", r"""new\s+WebSocket\(\s*["']([^"']+)["']"""),
    ("EventSource", r"""new\s+EventSource\(\s*["']([^"']+)["']"""),
    ("fetch", r"""\bfetch\(\s*["']([^"']+)["']"""),
    ("XHR open", r"""\.open\(\s*["'][A-Za-z]+["']\s*,\s*["']([^"']+)["']"""),
]
_DATA_URL = ("data url", r"""["']((?:https?:|wss?:)?//[^"']+)["']""")  # json/manifest/xml literals
_SRCSET = re.compile(r"""\bsrcset\s*=\s*["']([^"']+)["']""", re.IGNORECASE)


def _compile(pairs: list[tuple[str, str]]) -> list[tuple[str, re.Pattern[str]]]:
    return [(n, re.compile(rx, re.IGNORECASE)) for n, rx in pairs]


_BY_SUFFIX = {
    ".html": _compile(_HTML_CTX + _CSS_CTX + _JS_CTX),
    ".htm": _compile(_HTML_CTX + _CSS_CTX + _JS_CTX),
    ".svg": _compile(_HTML_CTX + _CSS_CTX),
    ".css": _compile(_CSS_CTX),
    ".js": _compile(_JS_CTX),
    ".mjs": _compile(_JS_CTX),
    ".json": _compile([_DATA_URL]),
    ".webmanifest": _compile([_DATA_URL]),
    ".xml": _compile([_DATA_URL]),
}


def _scannable() -> list[Path]:
    out: list[Path] = []
    for root in SCAN_DIRS:
        for p in root.rglob("*") if root.exists() else []:
            if not p.is_file() or p.suffix.lower() not in SCANNABLE_SUFFIXES:
                continue
            if p.stem.lower() in PROVENANCE_STEMS:  # LICENSE/SOURCE/CHECKSUM records only
                continue
            out.append(p)
    return out


def _is_violation(context: str, url: str) -> bool:
    p = urlparse(url.strip())
    absolute = p.scheme in _ABSOLUTE_SCHEMES or (p.scheme == "" and bool(p.netloc))  # incl. //host
    if not absolute:  # relative, root-relative (/static/...), data:, blob:, mailto:, tel:, #frag
        return False
    # Allowed only for anchor navigation, HTTPS, and an EXACT approved netloc.
    if context == "anchor href" and p.scheme == "https" and p.netloc in ALLOWED_NAV_NETLOCS:
        return False
    return True


def _hits(path: Path) -> list[tuple[str, str]]:
    text = path.read_text("utf-8", errors="replace")
    hits: list[tuple[str, str]] = []
    for name, rx in _BY_SUFFIX.get(path.suffix.lower(), []):
        for m in rx.finditer(text):
            hits.append((name, m.group(1)))
    if path.suffix.lower() in {".html", ".htm", ".svg"}:
        for m in _SRCSET.finditer(text):
            for candidate in m.group(1).split(","):
                token = candidate.strip().split()[0] if candidate.strip() else ""
                if token:
                    hits.append(("srcset", token))
    return hits


def test_no_external_runtime_assets() -> None:
    violations: list[str] = []
    for path in _scannable():
        for context, url in _hits(path):
            if _is_violation(context, url):
                violations.append(f"{path.relative_to(APP.parent)}: [{context}] -> {url}")
    assert not violations, "External runtime asset destination(s) found:\n" + "\n".join(
        sorted(set(violations))
    )


def test_no_cdnjs_reference_anywhere() -> None:
    """Belt-and-braces: the retired cdnjs Chart.js dependency must not reappear."""
    offenders = [
        str(p.relative_to(APP.parent))
        for p in _scannable()
        if "cdnjs.cloudflare.com" in p.read_text("utf-8", errors="replace")
    ]
    assert not offenders, f"cdnjs.cloudflare.com reference(s) found: {offenders}"
