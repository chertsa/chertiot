# ESP32 with MicroPython

**You need:** an ESP32 flashed with a recent MicroPython firmware (`esptool` + the official `.bin`), and Thonny or `mpremote`.

1. Download `main.py` from your device page in the portal.
2. Set `WIFI_SSID` and `WIFI_PASSWORD`.
3. Copy the file to the board (`mpremote cp main.py :main.py`) and reset it. The REPL prints `WiFi ok`, `MQTT ok` and one reading every 10 seconds.
4. Open **My dashboard**.

`umqtt.simple` ships with the official firmware. The starter connects with `ssl=True` on port 8883; if your firmware is very old and lacks TLS, ask your instructor — plain MQTT is not exposed on the public platform.
