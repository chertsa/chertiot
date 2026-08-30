"""Success criterion 2: zero cross-tenant visibility. Student A (tenant admin of A) must not read,
list, or write anything in tenant B — via REST with A's JWT, and via MQTT with A's device token."""

import json
import time

import paho.mqtt.client as mqtt
import pytest
from app.provisioning import ProvisionResult
from app.tb_client import TbClient, TbError

from conftest import MQTT_HOST, MQTT_PORT, TB_URL


def _as(sysadmin: TbClient, r: ProvisionResult) -> TbClient:
    return sysadmin.impersonate(r.user_id)


def test_rest_reads_are_scoped(
    sysadmin: TbClient, two_students: tuple[ProvisionResult, ProvisionResult]
) -> None:
    a, b = two_students
    as_a = _as(sysadmin, a)
    # Own data visible.
    assert [d.id.id for d in as_a.list_devices() if d.id] == [a.device_id]
    # B's entities: every read path is denied (403) or not found (404) — never 200.
    for path in (
        f"/tenant/{b.tenant_id}",
        f"/device/{b.device_id}",
        f"/device/{b.device_id}/credentials",
        f"/dashboard/{b.dashboard_id}",
        f"/user/{b.user_id}",
        f"/plugins/telemetry/DEVICE/{b.device_id}/values/timeseries?keys=temperature",
        f"/plugins/telemetry/DEVICE/{b.device_id}/values/attributes/SERVER_SCOPE",
    ):
        with pytest.raises(TbError) as e:
            as_a._get(path)
        assert e.value.status in (403, 404), (path, e.value.status)
    # Listing endpoints as A never leak B's ids.
    assert b.device_id not in {d.id.id for d in as_a.list_devices() if d.id}
    infos = as_a._get("/tenant/dashboards", pageSize=100, page=0)["data"]
    assert b.dashboard_id not in {d["id"]["id"] for d in infos}
    as_a.close()


def test_rest_writes_are_scoped(
    sysadmin: TbClient, two_students: tuple[ProvisionResult, ProvisionResult]
) -> None:
    a, b = two_students
    as_a = _as(sysadmin, a)
    # Rename B's device, post telemetry to B's device, delete B's device — all denied.
    with pytest.raises(TbError) as e:
        as_a._post(f"/plugins/telemetry/DEVICE/{b.device_id}/timeseries/ANY", {"temperature": 99})
    assert e.value.status in (403, 404)
    with pytest.raises(TbError) as e:
        as_a._delete(f"/device/{b.device_id}")
    assert e.value.status in (403, 404)
    device_b = sysadmin.impersonate(b.user_id).get_device(b.device_id)
    device_b.name = "hijacked"
    with pytest.raises(TbError) as e:
        as_a.save_device(device_b)
    assert e.value.status in (403, 404)
    assert sysadmin.impersonate(b.user_id).get_device(b.device_id).name != "hijacked"
    as_a.close()


def test_mqtt_token_writes_only_its_own_device(
    sysadmin: TbClient, two_students: tuple[ProvisionResult, ProvisionResult]
) -> None:
    a, b = two_students
    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    c.username_pw_set(a.device_access_token)
    c.connect(MQTT_HOST, MQTT_PORT)
    c.loop_start()
    c.publish("v1/devices/me/telemetry", json.dumps({"isolation": "A"}), qos=1).wait_for_publish(10)
    # Gateway-style topics addressing another device by name must not work for a plain device.
    # TB rejects this without an ACK (a plain device has no gateway session): fire-and-forget,
    # because paho's loop_stop() blocks forever on an un-ACKed QoS 1 message.
    gw_payload = {
        "my-first-device": [{"ts": int(time.time() * 1000), "values": {"isolation": "A-gw"}}]
    }
    c.publish("v1/gateway/telemetry", json.dumps(gw_payload), qos=0)
    time.sleep(1)
    c.disconnect()
    c.loop_stop()
    as_b = _as(sysadmin, b)
    time.sleep(1.5)
    latest = as_b.latest_timeseries(b.device_id, ["isolation"])
    assert not latest.get("isolation"), f"A's token wrote into B's device: {latest}"
    as_b.close()
    as_a = _as(sysadmin, a)
    assert as_a.latest_timeseries(a.device_id, ["isolation"]).get("isolation")
    as_a.close()


def test_portal_device_pages_are_scoped() -> None:
    """Portal-level scoping is exercised in portal/tests/e2e (device page for another tenant's id
    → 404 via TB's own authorization). Placeholder keeps the intent visible here."""
    assert TB_URL
