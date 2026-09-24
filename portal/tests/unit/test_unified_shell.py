"""Durable guards for the v2 unified visual system (Phase 5).

Every project-scoped page must render inside the one shared shell (`_project_nav.html`) so the
global header, project identity header and capability sub-nav are identical everywhere — this is
the check that caught the standalone Reports page. The sub-nav order and external-destination
marking are pinned so a reordering or an un-marked external link fails loudly.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import PortalUser, Project, ProjectMember

TEMPLATES = Path(__file__).resolve().parents[2] / "app" / "templates"

# Every template a `/projects/{id}/...` GET route renders. A NEW project page must be added here
# (a conscious choice) — and it must then carry the shared shell, or the test below fails.
PROJECT_PAGE_TEMPLATES = [
    "project.html",  # Overview
    "devices.html",
    "telemetry.html",
    "monitoring.html",
    "alerts.html",
    "flows.html",
    "lora.html",
    "notebooks.html",  # Notebooks capability landing
    "notebooks_unavailable.html",  # controlled degraded Notebooks page
    "project_report.html",  # Reports
    "project_settings.html",  # Members & Settings
]

# The one canonical capability sub-nav order (§3), as it must read on every page.
EXPECTED_TAB_ORDER = [
    "Overview",
    "Devices",
    "Telemetry",
    "Monitoring",
    "Alerts",
    "Flows",
    "LoRaWAN",
    "Notebooks",
    "Reports",
    "ThingsBoard",
    "Members & Settings",
]


def _nav_source() -> str:
    return (TEMPLATES / "_project_nav.html").read_text("utf-8")


def test_every_project_page_uses_the_shared_shell() -> None:
    """Each project page extends base.html AND includes the shared nav (no standalone pages)."""
    missing: list[str] = []
    for name in PROJECT_PAGE_TEMPLATES:
        src = (TEMPLATES / name).read_text("utf-8")
        if 'extends "base.html"' not in src or "_project_nav.html" not in src:
            missing.append(name)
    assert not missing, f"project pages not on the shared shell: {missing}"


def test_shared_nav_tab_order_is_canonical() -> None:
    """The sub-nav labels appear in the exact §3 order — identical on every page."""
    nav = _nav_source()
    # labels are gettext calls: _("Overview"), _("Members & Settings"), ...
    found = re.findall(r'_\(\s*"([^"]+)"\s*\)', nav)
    ordered = [lbl for lbl in found if lbl in EXPECTED_TAB_ORDER]
    # de-dup preserving order (a label appears once per tab anchor)
    seen: list[str] = []
    for lbl in ordered:
        if lbl not in seen:
            seen.append(lbl)
    assert seen == EXPECTED_TAB_ORDER, f"sub-nav order drifted: {seen}"


def test_thingsboard_tab_marked_external() -> None:
    """ThingsBoard is the engine/admin console: opened in a new tab and marked as external (↗)."""
    nav = _nav_source()
    m = re.search(r"<a[^>]*/thingsboard[^>]*>.*?</a>", nav, re.DOTALL)
    assert m, "ThingsBoard tab not found in shared nav"
    anchor = m.group(0)
    assert 'target="_blank"' in anchor and 'rel="noopener"' in anchor
    assert "↗" in anchor  # visible external-destination marker


def test_shared_nav_has_accessible_landmarks() -> None:
    """The project sub-nav is a labelled navigation landmark and shows a single active tab class."""
    nav = _nav_source()
    assert "aria-label=" in nav and 'class="subnav"' in nav
    assert "is-active" in nav  # active-state hook present for keyboard/visual orientation


def test_project_pages_have_single_h1() -> None:
    """The shared nav renders the project name as the page's one <h1>; each tab's section title
    is an <h2>. A second <h1> in a tab body breaks the heading hierarchy (a11y §7)."""
    offenders: list[str] = []
    for name in PROJECT_PAGE_TEMPLATES:
        body = (TEMPLATES / name).read_text("utf-8")
        if "<h1" in body:  # the only h1 must come from the included _project_nav.html
            offenders.append(name)
    assert not offenders, f"project pages with a second <h1> in the body: {offenders}"


def test_reports_page_renders_inside_shared_shell(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reports serves through the shared project shell (not a disconnected standalone page)."""
    u = PortalUser(id="u1", email="owner@x.io", kc_user_id="kc-u1", role="student")
    p = Project(
        id="p1", slug="p1", name="P1", provisioning_state="provisioned", tb_tenant_id="t-p1"
    )
    m = ProjectMember(
        project_id="p1", user_id="u1", role="owner", tb_user_id="tb-u1", status="active"
    )
    db.add_all([u, p, m])
    db.commit()
    monkeypatch.setattr("app.project.load_user", lambda request, db: u)
    r = client.get("/projects/p1/report")
    assert r.status_code == 200
    assert 'class="subnav"' in r.text  # shared capability sub-nav present
    assert 'id="report-print"' in r.text  # print-friendly control
    # the old standalone "← Workspace" back-button is gone (the nav replaces it)
    assert "← " not in r.text or "Workspace" not in r.text
