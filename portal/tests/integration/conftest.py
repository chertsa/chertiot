import os
import uuid
from collections.abc import Iterator

import httpx
import pytest

from app.tb_client import TbClient

TB_URL = os.environ.get("TB_ADMIN_URL", "http://127.0.0.1:18080")


def _tb_up() -> bool:
    try:
        return httpx.get(f"{TB_URL}/login", timeout=5).status_code == 200
    except httpx.HTTPError:
        return False


@pytest.fixture(scope="session")
def sysadmin() -> Iterator[TbClient]:
    if not _tb_up():
        pytest.skip(f"ThingsBoard not reachable at {TB_URL} (run `make dev`)")
    c = TbClient(
        TB_URL,
        username=os.environ["TB_SYSADMIN_EMAIL"],
        password=os.environ["TB_SYSADMIN_PASSWORD"],
    )
    yield c
    c.close()


@pytest.fixture
def student_email(sysadmin: TbClient) -> Iterator[str]:
    """A throwaway student identity; its tenant is deleted after the test."""
    email = f"it-{uuid.uuid4().hex[:8]}@test.chertiot.local"
    yield email
    t = sysadmin.find_tenant(email)
    if t and t.id:
        sysadmin.delete_tenant(t.id.id)
