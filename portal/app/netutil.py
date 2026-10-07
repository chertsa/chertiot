"""External-host allowlist logic (durable, testable mirror of the browser-check allowlist).

A CHERT page must load only from the platform's own hosts. Membership is by **exact hostname**
match — never prefix/suffix/substring — so a look-alike like `grafana.stage.chertiot.com.evil.tld`
or `notstage.chertiot.com` is correctly flagged external.
"""

from __future__ import annotations

from collections.abc import Iterable

_SUBDOMAINS = ("auth", "app", "lab", "grafana", "status")


def chert_hosts(domain: str) -> set[str]:
    """Exact hostnames a CHERT page may contact for `domain` (e.g. stage.chertiot.com)."""
    return {domain, *(f"{s}.{domain}" for s in _SUBDOMAINS)}


def external_hosts(seen: Iterable[str], domain: str) -> list[str]:
    """Hostnames in `seen` that are NOT in the exact CHERT allowlist for `domain`, sorted."""
    allow = chert_hosts(domain)
    return sorted({h for h in seen if h and h not in allow})
