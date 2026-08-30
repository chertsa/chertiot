# ESP32 with the Arduino IDE

**You need:** any ESP32 board, a USB cable, the Arduino IDE 2.x with the *esp32* board package, and the **PubSubClient** library (Library Manager → search "PubSubClient").

1. In the portal, open **My devices → your device** and download `chertiot_starter.ino`. Your token and the broker host are already in it.
2. Set `WIFI_SSID` and `WIFI_PASSWORD` at the top of the file.
3. Select your board and port, click **Upload**, then open the Serial Monitor at 115200 baud. You should see `WiFi ok`, `MQTT connecting... ok`, and a JSON line every 10 seconds.
4. Open **My dashboard**: the Temperature and Humidity charts start moving within a few seconds.

## Send real sensor data
The starter publishes random values. Replace the two lines that compute `temperature` and `humidity` with a read from your sensor (DHT22, BME280, …) and keep the JSON keys — the dashboard charts are wired to `temperature` and `humidity`. Any other key you send appears in **Latest telemetry** and can be added to a chart.

## Troubleshooting
| Symptom | Cause | Fix |
|---|---|---|
| `MQTT connecting... failed rc=5` | Wrong token | Copy the token again from the device page; it is the MQTT **username**, password stays empty |
| `rc=-2` | No route to the broker | Check Wi-Fi; the broker is `chertiot.com` port `8883` (TLS) |
| Connects, but the dashboard stays empty | Publishing to the wrong topic | The topic must be exactly `v1/devices/me/telemetry` |
| Data stops after a burst | Rate limit (10 messages/second per device) | Send one reading every few seconds; see [Limits](../guides/limits.md) |
