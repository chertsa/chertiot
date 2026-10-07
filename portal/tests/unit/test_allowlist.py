"""Exact-hostname external-asset allowlist logic (no prefix/suffix/substring matches)."""

from __future__ import annotations

from app.netutil import chert_hosts, external_hosts

DOMAIN = "stage.chertiot.com"


def test_chert_hosts_exact_set() -> None:
    assert chert_hosts(DOMAIN) == {
        "stage.chertiot.com",
        "auth.stage.chertiot.com",
        "app.stage.chertiot.com",
        "lab.stage.chertiot.com",
        "grafana.stage.chertiot.com",
        "status.stage.chertiot.com",
    }


def test_allowed_hosts_are_not_external() -> None:
    seen = ["stage.chertiot.com", "auth.stage.chertiot.com", "grafana.stage.chertiot.com"]
    assert external_hosts(seen, DOMAIN) == []


def test_lookalikes_and_third_parties_are_external() -> None:
    seen = [
        "grafana.stage.chertiot.com.evil.tld",  # suffix attack
        "notstage.chertiot.com",  # prefix attack
        "chertiot.com",  # parent domain (not the staging host)
        "cdn.jsdelivr.net",  # third party
        "fonts.googleapis.com",  # third party
        "",  # ignored
    ]
    assert external_hosts(seen, DOMAIN) == [
        "cdn.jsdelivr.net",
        "chertiot.com",
        "fonts.googleapis.com",
        "grafana.stage.chertiot.com.evil.tld",
        "notstage.chertiot.com",
    ]


def test_substring_of_allowed_is_not_allowed() -> None:
    # a host that merely CONTAINS an allowed host as a substring must still be external
    assert external_hosts(["xgrafana.stage.chertiot.comx"], DOMAIN) == [
        "xgrafana.stage.chertiot.comx"
    ]
