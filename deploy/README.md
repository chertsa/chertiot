# deploy/

VPS provisioning and operations. `scripts/` (bootstrap/backup/restore), `caddy/` (Caddyfile.dev / Caddyfile.prod + layer4 build), `tb/` (ThingsBoard env), `postgres/` (init SQL), `runbooks/`, `staging/`. Staging deploy = M2.2, production = M2.3.

## Services in the `core` profile

| Service | What it does |
|---|---|
| **postgres** | Single PostgreSQL 16 instance holding three databases: `thingsboard`, `keycloak`, `portal`. Created by `postgres/init.sql` on first start. |
| **tb-install** | One-shot ThingsBoard schema installer (`INSTALL_TB=true`). Writes a marker to its volume and exits 0 on later runs. |
| **tb** | ThingsBoard CE monolith (`thingsboard/tb-node`): REST/UI on 8080, MQTT on 1883, HTTP transport. In-memory queue, SQL timeseries. Branded image replaces it in M2.1. |
| **keycloak** | Identity provider (D3) at `auth.<domain>`. Postgres-backed, runs behind Caddy with forwarded headers; health/metrics on port 9000. |
| **portal** | CHERT IoT FastAPI portal (signup, provisioning, student pages). Built from `portal/`. |
| **caddy** | TLS + HTTP routing for every vhost, and layer4 TLS termination for MQTTS 8883 → `tb:1883` (D8). One image everywhere: `chertiot/caddy:<ver>-l4` (make caddy-image / CI images.yml). |
| **prometheus** | Scrapes TB, Keycloak, Caddy, node/cAdvisor/postgres exporters, portal. 30-day retention. Alert rules in `monitoring/prometheus/rules/`. |
| **grafana** | Admin-only dashboards over Prometheus. Datasource auto-provisioned; dashboards from `monitoring/grafana-dashboards/`. |
| **uptime-kuma** | Public status page at `status.<domain>` and up/down alerting. |
| **node-exporter** | Host CPU/RAM/disk metrics for Prometheus. |
| **cadvisor** | Per-container CPU/RAM/IO metrics — the basis for the Phase 3 resource-cap tests. |
| **postgres-exporter** | Database size, connections, and query stats for Prometheus. |

## Local dev

```
cp .env.example .env   # fill in passwords
make dev               # builds caddy+portal, installs TB schema, starts everything
```
Then: http://app.localhost (ThingsBoard), http://auth.localhost (Keycloak), http://localhost (portal), http://grafana.localhost, http://prometheus.localhost, http://status.localhost. MQTT: `localhost:1883`.
