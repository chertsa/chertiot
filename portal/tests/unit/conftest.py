from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db import Base, get_engine
from app.main import app
from app.routers.signup import get_kc


class FakeKeycloak:
    def __init__(self) -> None:
        self.created: list[tuple[str, str]] = []
        self.verify_sent: list[tuple[str, str]] = []
        self.existing: set[str] = set()

    def create_user(
        self, email: str, password: str, first_name: str = "", last_name: str = ""
    ) -> str:
        from app.keycloak_admin import KeycloakUserExistsError

        if email in self.existing:
            raise KeycloakUserExistsError(409, "exists")
        self.created.append((email, first_name))
        return f"kc-{len(self.created)}"

    def send_verify_email(self, user_id: str, redirect_uri: str) -> None:
        self.verify_sent.append((user_id, redirect_uri))


@pytest.fixture(autouse=True)
def fresh_db() -> Iterator[None]:
    Base.metadata.drop_all(get_engine())
    Base.metadata.create_all(get_engine())
    yield


@pytest.fixture
def kc() -> Iterator[FakeKeycloak]:
    fake = FakeKeycloak()
    app.dependency_overrides[get_kc] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_kc, None)


@pytest.fixture
def client(kc: FakeKeycloak) -> TestClient:
    return TestClient(app, follow_redirects=False)


@pytest.fixture
def db() -> Iterator[Session]:
    with Session(get_engine()) as s:
        yield s
