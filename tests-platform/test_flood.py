"""Success criterion 4: a flooding device (1000 msg/s attempted) is throttled by the tenant profile
and does not degrade a control device in another tenant.

The flooder runs in a separate process so the measurement loop is not slowed by the GIL. Each
control message is published once per second and its end-to-end visibility (publish → readable via
REST) is timed with a hard per-call timeout. Slow (~1 min): nightly / `make flood-test`."""

import json
import statistics
import subprocess
import sys
import time

import httpx
import paho.mqtt.client as mqtt
import pytest
from app.provisioning import ProvisionResult
from app.tb_client import TbClient

from conftest import MQTT_HOST, MQTT_PORT, TB_URL

FLOOD_SECONDS = 25
CONTROL_MESSAGES = 20
DEVICE_LIMIT_PER_MIN = 300  # templates-tb/tenant-profile-student.json: "10:1,300:60"

FLOODER = r"""
import sys, time, paho.mqtt.client as mqtt
host, port, token, seconds = sys.argv[1], int(sys.argv[2]), sys.argv[3], float(sys.argv[4])
c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2); c.username_pw_set(token)
c.reconnect_delay_set(1, 1); c.connect(host, port, keepalive=30); c.loop_start()
n = 0; end = time.time() + seconds
while time.time() < end:
    for _ in range(50):
        c.publish("v1/devices/me/telemetry", '{"flood":1}', qos=0); n += 1
    time.sleep(0.05)   # ~1000 msg/s
print(n, flush=True)
c.disconnect(); c.loop_stop()
"""


@pytest.mark.flood
def test_flooder_is_throttled_and_control_unaffected(
    sysadmin: TbClient, two_students: tuple[ProvisionResult, ProvisionResult]
) -> None:
    flooder, control = two_students
    as_control = sysadmin.impersonate(control.user_id)
    as_flooder = sysadmin.impersonate(flooder.user_id)
    auth = {"X-Authorization": f"Bearer {as_control._tokens.token}"}  # type: ignore[union-attr]
    latest_url = f"{TB_URL}/api/plugins/telemetry/DEVICE/{control.device_id}/values/timeseries"
    start_ms = int(time.time() * 1000)

    proc = subprocess.Popen(  # noqa: S603 — our own flooder script, our interpreter
        [
            sys.executable,
            "-c",
            FLOODER,
            MQTT_HOST,
            str(MQTT_PORT),
            flooder.device_access_token,
            str(FLOOD_SECONDS),
        ],
        stdout=subprocess.PIPE,
        text=True,
    )
    time.sleep(2)  # let the flood ramp up before measuring

    cc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    cc.username_pw_set(control.device_access_token)
    cc.connect(MQTT_HOST, MQTT_PORT, keepalive=30)
    cc.loop_start()
    latencies: list[float] = []
    rest_calls: list[float] = []
    lost = 0
    with httpx.Client(timeout=2.0) as http:
        for seq in range(1, CONTROL_MESSAGES + 1):
            sent = time.time()
            cc.publish("v1/devices/me/telemetry", json.dumps({"seq": seq}), qos=1)
            visible = None
            while time.time() - sent < 5.0:
                t0 = time.time()
                try:
                    rows = http.get(latest_url, params={"keys": "seq"}, headers=auth).json()
                    rest_calls.append(time.time() - t0)
                    value = (rows.get("seq") or [{}])[0].get("value")
                    if value is not None and int(value) >= seq:
                        visible = time.time()
                        break
                except (httpx.HTTPError, ValueError):
                    rest_calls.append(time.time() - t0)
                time.sleep(0.05)
            if visible is None:
                lost += 1
            else:
                latencies.append(visible - sent)
            time.sleep(max(0.0, 1.0 - (time.time() - sent)))
    cc.disconnect()
    cc.loop_stop()
    attempted = int(proc.communicate(timeout=FLOOD_SECONDS + 10)[0].strip() or 0)
    time.sleep(2)

    end_ms = int(time.time() * 1000)
    rows = as_flooder._get(
        f"/plugins/telemetry/DEVICE/{flooder.device_id}/values/timeseries",
        keys="flood",
        startTs=start_ms,
        endTs=end_ms,
        limit=100000,
        agg="NONE",
    )
    accepted = len(rows.get("flood", [])) if isinstance(rows, dict) else 0
    allowed = DEVICE_LIMIT_PER_MIN * (FLOOD_SECONDS / 60) + 10 * 2  # minute budget + burst slack
    p50 = statistics.median(latencies) if latencies else float("nan")
    p95 = (
        statistics.quantiles(latencies, n=20)[18]
        if len(latencies) >= 20
        else max(latencies, default=0)
    )
    rest_p95 = (
        statistics.quantiles(rest_calls, n=20)[18] if len(rest_calls) >= 20 else max(rest_calls)
    )
    print(
        f"\nflooder: attempted={attempted} accepted={accepted} allowed≈{allowed:.0f}"
        f"\ncontrol: n={len(latencies)} lost={lost} p50={p50:.3f}s p95={p95:.3f}s"
        f" rest_p95={rest_p95:.3f}s"
    )
    as_control.close()
    as_flooder.close()

    assert accepted < attempted, "nothing was throttled"
    assert accepted <= allowed * 1.5, f"flooder accepted {accepted} msgs; limit not enforced"
    assert lost == 0, f"control device lost {lost} of {CONTROL_MESSAGES} messages during the flood"
    assert p95 < 1.0, f"control p95 latency {p95:.3f}s during the flood"
