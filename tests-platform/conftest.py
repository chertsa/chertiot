"""Cross-cutting platform tests (tenancy isolation, flood). Run against the local stack:
    make platform-test        # isolation, fast — runs in CI on every push to main
    make flood-test           # ~1 min, nightly / on demand
They reuse the portal's TB client and provisioning (repo root is on sys.path via pytest rootdir)."""

import os
import sys
import uuid
from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "portal"))

from app.config import Settings  # noqa: E402
from app.provisioning import ProvisionResult, provision_student  # noqa: E402
from app.tb_client import TbClient  # noqa: E402

TB_URL = os.environ.get("TB_ADMIN_URL", "http://127.0.0.1:18080")
MQTT_HOST = os.environ.get("MQTT_HOST", "127.0.0.1")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))


def settings() -> Settings:
    return Settings(portal_secret_key="t", portal_database_url="sqlite://")


@pytest.fixture(scope="session")
def sysadmin() -> Iterator[TbClient]:
    try:
        assert httpx.get(f"{TB_URL}/login", timeout=5).status_code == 200
    except Exception:  # noqa: BLE001
        pytest.skip(f"ThingsBoard not reachable at {TB_URL}")
    c = TbClient(
        TB_URL,
        username=os.environ["TB_SYSADMIN_EMAIL"],
        password=os.environ["TB_SYSADMIN_PASSWORD"],
    )
    yield c
    c.close()


@pytest.fixture
def two_students(sysadmin: TbClient) -> Iterator[tuple[ProvisionResult, ProvisionResult]]:
    emails = [f"pt-{uuid.uuid4().hex[:8]}@test.chertiot.local" for _ in range(2)]
    results = tuple(provision_student(sysadmin, e, settings=settings()) for e in emails)
    yield results  # type: ignore[misc]
    for e in emails:
        t = sysadmin.find_tenant(e)
        if t and t.id:
            sysadmin.delete_tenant(t.id.id)
