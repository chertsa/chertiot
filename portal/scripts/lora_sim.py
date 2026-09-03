"""Simulate a ChirpStack uplink event (seed data for M4.1 acceptance) — publishes the exact
application-up JSON the lora-bridge consumes, so the bridge→mapping→TB path is exercised without
LoRa hardware. Radio decode is ChirpStack's own tested code; this tests OUR integration.

    DEV_EUI=... TEMP=21.5 uv run python -m scripts.lora_sim
"""

from __future__ import annotations

import json
import os
import sys
import time

import paho.mqtt.client as mqtt

MQTT_HOST = os.environ.get("LORA_MQTT_HOST", "mosquitto")


def main() -> int:
    dev_eui = os.environ["DEV_EUI"].lower()
    obj = {
        "temperature": float(os.environ.get("TEMP", "21.5")),
        "battery": int(os.environ.get("BATTERY", "95")),
    }
    event = {
        "deduplicationId": os.urandom(8).hex(),
        "time": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
        "deviceInfo": {"devEui": dev_eui, "deviceName": f"lora-{dev_eui[:6]}"},
        "fPort": 2,
        "object": obj,
        "rxInfo": [{"rssi": -92, "snr": 7.5}],
    }
    topic = f"application/sim/device/{dev_eui}/event/up"
    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    c.connect(MQTT_HOST, 1883, keepalive=10)
    c.loop_start()
    info = c.publish(topic, json.dumps(event), qos=1)
    info.wait_for_publish(10)
    c.disconnect()
    c.loop_stop()
    print(f"simulated uplink published to {topic}: {obj}")
    return 0 if info.is_published() else 1


if __name__ == "__main__":
    sys.exit(main())
