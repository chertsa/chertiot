# CHERT IoT starter — ESP32 MicroPython. Sends a reading every 10 s over MQTT/TLS.
# Needs umqtt.simple (built into most ESP32 MicroPython builds). Placeholders {{...}} are filled
# in by the portal when you download this file.
import json
import network
import time
import urandom

from umqtt.simple import MQTTClient

WIFI_SSID = "YOUR_WIFI_SSID"
WIFI_PASSWORD = "YOUR_WIFI_PASSWORD"

MQTT_HOST = "{{MQTT_HOST}}"
MQTT_PORT = {{MQTT_PORT}}  # 8883 = TLS
ACCESS_TOKEN = "{{ACCESS_TOKEN}}"  # device access token = MQTT username
TOPIC = b"v1/devices/me/telemetry"


def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        while not wlan.isconnected():
            time.sleep(0.5)
    print("WiFi ok:", wlan.ifconfig()[0])


def main():
    connect_wifi()
    client = MQTTClient("{{DEVICE_NAME}}", MQTT_HOST, port=MQTT_PORT, user=ACCESS_TOKEN, password="", ssl=True)
    client.connect()
    print("MQTT ok")
    while True:
        # Replace with a real sensor read. Random values keep the demo alive.
        reading = {"temperature": 20 + urandom.getrandbits(7) / 12.7, "humidity": 40 + urandom.getrandbits(7) / 6.35}
        client.publish(TOPIC, json.dumps(reading))
        print(reading)
        time.sleep(10)


main()
