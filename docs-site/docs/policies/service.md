# Service expectations

CHERT IoT is run on a best-effort basis for learning, on a single server.

- **Status:** [status page](https://status.chertiot.com) shows live availability and incidents.
- **Maintenance window:** Sundays 06:00–08:00 UTC. Upgrades and backups happen then; devices reconnect automatically afterwards.
- **Backups:** nightly; a restore may lose up to 24 hours of telemetry.
- **Data retention:** 90 days of telemetry; older data is deleted automatically.
- **No guarantees** on uptime, latency or data durability — do not depend on it for anything that matters if it stops.
