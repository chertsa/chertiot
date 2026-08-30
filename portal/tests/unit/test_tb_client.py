import base64
import json
import time

import httpx
import pytest
import respx

from app.tb_client import Device, TbClient, TbError, TbNotFoundError

TB = "http://tb.test"


def jwt(exp_in: float) -> str:
    payload = base64.urlsafe_b64encode(json.dumps({"exp": time.time() + exp_in}).encode()).decode()
    return f"h.{payload.rstrip('=')}.s"


@pytest.fixture
def client() -> TbClient:
    return TbClient(TB, username="a@b", password="x")


@respx.mock
def test_login_then_get(client: TbClient) -> None:
    respx.post(f"{TB}/api/auth/login").respond(json={"token": jwt(9000), "refreshToken": "r"})
    route = respx.get(f"{TB}/api/tenant/devices", params={"deviceName": "d1"}).respond(
        json={"id": {"entityType": "DEVICE", "id": "u1"}, "name": "d1"}
    )
    d = client.find_device("d1")
    assert d is not None and d.name == "d1"
    assert route.calls.last.request.headers["X-Authorization"].startswith("Bearer ")


@respx.mock
def test_refreshes_when_token_near_expiry(client: TbClient) -> None:
    respx.post(f"{TB}/api/auth/login").respond(json={"token": jwt(30), "refreshToken": "r"})
    refresh = respx.post(f"{TB}/api/auth/token").respond(
        json={"token": jwt(9000), "refreshToken": "r2"}
    )
    respx.get(f"{TB}/api/tenant/devices").respond(json={"name": "d"})
    client.find_device("d")
    assert refresh.called


@respx.mock
def test_404_maps_to_none_for_find(client: TbClient) -> None:
    respx.post(f"{TB}/api/auth/login").respond(json={"token": jwt(9000), "refreshToken": "r"})
    respx.get(f"{TB}/api/tenant/devices").respond(404, json={"message": "Device not found"})
    assert client.find_device("nope") is None


@respx.mock
def test_retries_transient_5xx_then_succeeds(client: TbClient) -> None:
    respx.post(f"{TB}/api/auth/login").respond(json={"token": jwt(9000), "refreshToken": "r"})
    route = respx.post(f"{TB}/api/device")
    route.side_effect = [
        httpx.Response(503, json={"message": "busy"}),
        httpx.Response(200, json={"name": "d"}),
    ]
    assert client.save_device(Device(name="d")).name == "d"
    assert route.call_count == 2


@respx.mock
def test_non_transient_error_raises(client: TbClient) -> None:
    respx.post(f"{TB}/api/auth/login").respond(json={"token": jwt(9000), "refreshToken": "r"})
    respx.post(f"{TB}/api/device").respond(
        400, json={"message": "Device with such name already exists"}
    )
    with pytest.raises(TbError) as e:
        client.save_device(Device(name="d"))
    assert e.value.status == 400 and not isinstance(e.value, TbNotFoundError)


@respx.mock
def test_401_triggers_refresh_and_retry(client: TbClient) -> None:
    respx.post(f"{TB}/api/auth/login").respond(json={"token": jwt(9000), "refreshToken": "r"})
    respx.post(f"{TB}/api/auth/token").respond(json={"token": jwt(9000), "refreshToken": "r2"})
    route = respx.get(f"{TB}/api/tenant/devices")
    route.side_effect = [
        httpx.Response(401, json={"message": "expired"}),
        httpx.Response(200, json={"name": "d"}),
    ]
    assert client.find_device("d") is not None
