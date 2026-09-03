"""lora-bridge (M4.1): subscribe to ChirpStack uplink events on the internal MQTT broker and push
each decoded uplink into the owning student's ThingsBoard device.

Topic: application/{appId}/device/{devEui}/event/up  (ChirpStack v4 JSON). We forward the decoded
`object` (or fPort/data) as telemetry to the student's TB device, mapped by DevEUI in the portal DB.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import signal
import sys
from typing import Any

import paho.mqtt.client as mqtt

from app.db import session_factory
from app.models import LoraDevice, PortalUser
from app.onboarding import sysadmin_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s lora-bridge %(message)s")
log = logging.getLogger("lora-bridge")

MQTT_HOST = os.environ.get("LORA_MQTT_HOST", "mosquitto")
TOPIC = "application/+/device/+/event/up"


def _telemetry_from_uplink(payload: dict[str, Any]) -> dict[str, Any]:
    obj = payload.get("object")
    if isinstance(obj, dict) and obj:
        return {k: v for k, v in obj.items() if isinstance(v, int | float | str | bool)}
    data = payload.get("data")
    out: dict[str, Any] = {"fPort": payload.get("fPort")}
    if data:
        out["raw_b64"] = data
        try:
            out["raw_hex"] = base64.b64decode(data).hex()
        except (ValueError, TypeError):
            pass
    rx = (payload.get("rxInfo") or [{}])[0]
    if rx.get("rssi") is not None:
        out["rssi"] = rx["rssi"]
    if rx.get("snr") is not None:
        out["snr"] = rx["snr"]
    return out


def _forward(dev_eui: str, telemetry: dict[str, Any]) -> None:
    with session_factory()() as db:
        mapping = db.get(LoraDevice, dev_eui.lower())
        if mapping is None:
            log.info("uplink for unmapped DevEUI %s — ignored", dev_eui)
            return
        user = db.get(PortalUser, mapping.user_id)
        device_name = mapping.tb_device_name
    if user is None or not user.tb_user_id:
        return
    sysadmin = sysadmin_client()
    try:
        student = sysadmin.impersonate(user.tb_user_id)
        try:
            device = student.find_device(device_name)
            if device is None or not device.id:
                log.warning("TB device %s missing for %s", device_name, dev_eui)
                return
            creds = student.get_device_credentials(device.id.id)
            student._request(
                "POST",
                f"/v1/{creds.credentials_id}/telemetry",
                json=telemetry,
            )
            log.info("forwarded uplink %s -> %s %s", dev_eui, device_name, telemetry)
        finally:
            student.close()
    finally:
        sysadmin.close()


def on_message(_c: mqtt.Client, _u: object, msg: mqtt.MQTTMessage) -> None:
    try:
        payload = json.loads(msg.payload.decode())
        dev_eui = (payload.get("deviceInfo") or {}).get("devEui") or msg.topic.split("/")[3]
        _forward(dev_eui.lower(), _telemetry_from_uplink(payload))
    except Exception:  # noqa: BLE001 — one bad message must not kill the bridge
        log.exception("failed to process uplink on %s", msg.topic)


def main() -> int:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="chertiot-lora-bridge")
    client.on_message = on_message

    def _on_connect(c, u, f, rc, props=None):  # noqa: ANN001, ANN202
        c.subscribe(TOPIC)
        log.info("connected, subscribed %s", TOPIC)

    client.on_connect = _on_connect
    client.connect(MQTT_HOST, 1883, keepalive=30)
    signal.signal(signal.SIGTERM, lambda *_: client.disconnect())
    log.info("lora-bridge starting against %s", MQTT_HOST)
    client.loop_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
