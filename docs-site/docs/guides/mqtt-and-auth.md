# MQTT, topics and your token

| Setting | Value |
|---|---|
| Broker | `chertiot.com` |
| Port | `8883` (TLS). Plain `1883` is **not** exposed publicly |
| Username | your device's **access token** |
| Password | empty |
| Client id | anything unique; the starter code uses the device name |
| Telemetry topic | `v1/devices/me/telemetry` |
| Attributes topic | `v1/devices/me/attributes` (device metadata such as firmware version) |

**Payload** is JSON, either `{"key": value, ...}` (timestamped on arrival) or `{"ts": 1700000000000, "values": {...}}` to supply your own timestamp. Keys are free-form; numbers become charts, strings become labels.

**Tokens are per device.** A token can only write to its own device — it cannot read anything, and cannot reach another device or another student's data. Lost a token, or pasted it somewhere public? Open the device page and click **Issue new token**; the old one stops working immediately.

**TLS:** the certificate is a normal public one (Let's Encrypt). Most Arduino cores and MicroPython builds accept it by default; the ESP32 starter uses `setInsecure()` for simplicity — switch to `setCACert()` with the ISRG Root X1 certificate for anything beyond the lab.
