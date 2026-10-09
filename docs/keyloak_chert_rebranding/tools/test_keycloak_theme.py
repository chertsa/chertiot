"""CI guard for the CHERT Keycloak login theme — copy into the project's test suite.

Set CHERT_THEME_DIR to the theme's login directory (default: keycloak/themes/chert/login relative
to the repo root, i.e. the current working directory when pytest runs).

Fails when:
  - an asset changed without its ?v= content hash (browsers would keep a 30-day-old copy);
  - the stock language <select> came back instead of the CHERT pill;
  - required project text is missing in English or Arabic;
  - the theme stops forcing LTR or turns dark mode back on.
"""

import hashlib
import os
import re
from pathlib import Path

LOGIN = Path(os.environ.get("CHERT_THEME_DIR", "keycloak/themes/chert/login")).resolve()
REQUIRED_KEYS = ["chertProduct", "chertAuthEyebrow", "chertAuthTitle", "chertAuthTitleAccent",
                 "chertAuthLead", "chertAuthPoint1", "chertAuthPoint2", "chertAuthPoint3", "loginTitle"]


def _h(rel: str) -> str:
    return hashlib.sha256((LOGIN / "resources" / rel).read_bytes()).hexdigest()[:10]


def test_assets_are_versioned_by_content_hash() -> None:
    props = (LOGIN / "theme.properties").read_text("utf-8")
    for line in re.findall(r"^(?:styles|scripts)=(.+)$", props, re.M):
        for ref in line.split():
            path, _, v = ref.partition("?v=")
            assert v == _h(path), f"{path}: run tools/version_assets.py (has ?v={v!r}, needs {_h(path)})"
    ftl = (LOGIN / "template.ftl").read_text("utf-8")
    for path, v in re.findall(r"\$\{url\.resourcesPath\}/([^\"'?\s$]+)\?v=([0-9a-f]+)", ftl):
        assert v == _h(path), f"template.ftl {path}: run tools/version_assets.py"
    own_unversioned = [p for p in re.findall(r"\$\{url\.resourcesPath\}/([^\"'?\s$]+)[\"']", ftl)
                       if (LOGIN / "resources" / p).is_file()]
    assert not own_unversioned, f"unversioned theme assets in template.ftl: {own_unversioned}"


def test_language_pill_and_layout_rules() -> None:
    ftl = (LOGIN / "template.ftl").read_text("utf-8")
    assert "login-select-toggle" not in ftl, "stock language <select> is back; use the CHERT pill"
    assert "chert-lang__pill" in ftl and "chertLangSwitchPath" in ftl
    props = (LOGIN / "theme.properties").read_text("utf-8")
    assert re.search(r"^darkMode=false$", props, re.M), "darkMode must stay false"
    assert re.search(r"^locales=en,ar$", props, re.M)
    css = (LOGIN / "resources" / "css" / "chert.css").read_text("utf-8")
    assert 'html[dir="rtl"], html[lang="ar"] { direction: ltr !important; }' in css, "LTR rule removed"


def test_project_text_present_in_both_languages() -> None:
    for lang in ("en", "ar"):
        text = (LOGIN / "messages" / f"messages_{lang}.properties").read_text("utf-8")
        keys = dict(l.split("=", 1) for l in text.splitlines() if "=" in l and not l.startswith("#"))
        missing = [k for k in REQUIRED_KEYS if not keys.get(k, "").strip()]
        assert not missing, f"messages_{lang}: missing {missing}"
