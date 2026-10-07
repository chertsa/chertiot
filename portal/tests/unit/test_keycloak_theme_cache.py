"""Keycloak login-theme assets must be cache-busted by content.

Keycloak serves theme resources at /resources/<keycloak-build>/login/chertiot/... with
`cache-control: max-age=2592000` (30 days), and that path does not change when our theme changes.
Without a per-content version, browsers keep the previous CSS/JS for a month and render the new
template.ftl markup unstyled (UAT-08 regression). theme.properties therefore references each asset
as `<path>?v=<first 10 hex of its sha256>`; this test fails when a file changes without its ?v=
being bumped. Fix: set ?v= to the value printed in the assertion message.
"""

import hashlib
import re
from pathlib import Path

THEME = Path(__file__).resolve().parents[3] / "keycloak" / "theme" / "chertiot" / "login"


def _props() -> str:
    return (THEME / "theme.properties").read_text("utf-8")


def test_theme_assets_are_versioned_by_content_hash() -> None:
    props = _props()
    refs = re.findall(r"^(?:styles|scripts)=(.+)$", props, re.M)
    assert refs, "theme.properties declares no styles/scripts"
    for line in refs:
        for ref in line.split():
            path, _, version = ref.partition("?v=")
            digest = hashlib.sha256((THEME / "resources" / path).read_bytes()).hexdigest()[:10]
            assert version == digest, f"{path}: set ?v={digest} in theme.properties (has {version!r})"
