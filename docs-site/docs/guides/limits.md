# Limits and what you can't do (yet)

Every student tenant has the same fair limits so that one runaway device cannot slow anyone else down:

| Limit | Value |
|---|---|
| Devices | 10 |
| Messages per device | 10 per second, 300 per minute |
| Messages per tenant | 50 per second, 1,500 per minute |
| Data points per device | 100 per second |
| Telemetry retention | 90 days |
| Dashboards | 10 · rule chains 5 · users 3 |

Exceeding a rate limit drops the extra messages (and briefly disconnects a device that keeps flooding). Send a reading every few seconds, not every loop iteration.

**Not available yet:** LoRaWAN devices, Node-RED flows and Jupyter notebooks are planned; email/webhook alerts from the portal and CSV export are planned. See the status page for maintenance windows.
