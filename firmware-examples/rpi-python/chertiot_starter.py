#!/usr/bin/env python3
"""CHERT IoT starter — Raspberry Pi / any Linux box with Python 3.

    pip install paho-mqtt
    python3 chertiot_starter.py

Sends a reading every 10 s over MQTT/TLS. Placeholders {{...}} are filled in by the portal."""

import json
import random
import ssl
import time

import paho.mqtt.client as mqtt

MQTT_HOST = "{{MQTT_HOST}}"
MQTT_PORT = {{MQTT_PORT}}  # 8883 = TLS
ACCESS_TOKEN = "{{ACCESS_TOKEN}}"  # device access token = MQTT username
TOPIC = "v1/devices/me/telemetry"

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="{{DEVICE_NAME}}")
client.username_pw_set(ACCESS_TOKEN)
if MQTT_PORT == 8883:
    client.tls_set(cert_reqs=ssl.CERT_REQUIRED)
client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
client.loop_start()

try:
    while True:
        # Replace with a real sensor read (e.g. a DS18B20 on 1-Wire). Random values keep the demo alive.
        reading = {"temperature": round(20 + random.random() * 10, 1), "humidity": round(40 + random.random() * 20, 1)}
        client.publish(TOPIC, json.dumps(reading), qos=1)
        print(reading)
        time.sleep(10)
except KeyboardInterrupt:
    client.loop_stop()
    client.disconnect()
