# CHERT IoT

Open-source systems inventory for the CHERT IoT platform (chertiot.com), covering all deployed engines/services defined in the project architecture and Docker Compose profiles.

## Inventory Scope

- Source of truth: docker-compose profiles (`core`, `flows`, `lab`, `lora`) and architecture documentation.
- Includes production and staging deployed systems; dev-only systems are marked.
- Focus: open-source platforms/engines and operational services that run as part of the stack.

## Open-Source Systems Inventory

| System | Version (Pinned) | License | Sector | Category | Deployment Profile | Role in Project | Notes |
|---|---|---|---|---|---|---|---|
| ThingsBoard CE | 4.3.1.4 | Apache-2.0 | IoT Platform | IoT Application Enablement Platform (AEP) | `core` | Multi-tenant IoT core: device connectivity, telemetry, dashboards, rule chains, alarms, REST API | Branded build from pinned upstream tag and patch series |
| Keycloak | 26.7.2 | Apache-2.0 | Identity & Access | IAM / OIDC Identity Provider | `core` | Central authentication, SSO, realm and client management for platform apps | TB acts as OAuth2 client to Keycloak |
| PostgreSQL | 16.15 | PostgreSQL License | Data | Relational Database | `core`, `lora` | Primary datastore for ThingsBoard, Keycloak, portal, and ChirpStack | Shared DB engine across services |
| Caddy (+ layer4 plugin build) | 2.11.4 | Apache-2.0 | Networking & Edge | Reverse Proxy / TLS Termination / L4 Gateway | `core` | HTTPS ingress, vhost routing, and MQTTS termination on 8883 | Uses custom pinned layer4-enabled image in non-dev envs |
| Prometheus | v3.14.0 | Apache-2.0 | Observability | Metrics Collection & Alert Source | `core` | Scrapes platform/exporter metrics and evaluates alert rules | Retention and alert rules defined in monitoring config |
| Alertmanager | v0.34.0 | Apache-2.0 | Observability | Alert Routing | `core` | Routes Prometheus alerts to notification channels (email) | SMTP credentials mounted as runtime secret |
| Grafana | 13.1.4 | AGPL-3.0 | Observability | Metrics Visualization | `core` | Admin dashboards over Prometheus data | Admin-only access |
| Uptime Kuma | 1.23.17 | MIT | Operations | Uptime Monitoring / Status Page | `core` | Public status page and endpoint health monitoring | 1.x line pinned for API compatibility |
| node-exporter | v1.12.1 | Apache-2.0 | Observability | Host Metrics Exporter | `core` | Exposes host metrics to Prometheus | Runs with host filesystem mount |
| cAdvisor | v0.55.1 | Apache-2.0 | Observability | Container Metrics Exporter | `core` | Exposes per-container runtime metrics to Prometheus | Image served via `gcr.io/cadvisor/cadvisor` |
| postgres-exporter | v0.20.1 | Apache-2.0 | Observability | Database Metrics Exporter | `core` | Exposes PostgreSQL metrics to Prometheus | Uses DB credentials via env |
| Node-RED | 5.0.6 | Apache-2.0 | Automation / IoT Flows | Visual Flow Programming Runtime | `flows` | Per-student flow editor/runtime with resource caps | Spawned and isolated per user |
| docker-socket-proxy (Tecnativa) | v0.5.0 | GPL-3.0 | Platform Operations | Docker API Access Control Proxy | `flows`, `lab` | Restricts Docker API surface for controlled container spawning | Least-privilege gateway for spawner workflows |
| JupyterHub | 5.5.1 | BSD-3-Clause | Data Science & Education | Multi-user Notebook Hub | `lab` | Student notebook environment with OIDC login and per-user sessions | Uses DockerSpawner pattern |
| ChirpStack | 4.19.1 | MIT | IoT Connectivity | LoRaWAN Network Server | `lora` | LoRaWAN device/network management and uplink handling | Integrated into TB via bridge workflow |
| ChirpStack Gateway Bridge | 4.1.2 | MIT | IoT Connectivity | Gateway Protocol Bridge | `lora` | Bridges gateway packet-forwarder traffic to ChirpStack over MQTT | UDP Semtech traffic ingress |
| Eclipse Mosquitto | 2.0.22 | EPL-2.0 | Messaging | MQTT Broker | `lora` | Internal broker for ChirpStack/gateway bridge and LoRa event flow | Internal service for LoRa profile |
| Redis | 7.4.11 | BSD-3-Clause | Data Infrastructure | In-memory Data Store | `lora` | Backend store used by ChirpStack | Stateful service with dedicated volume |
| Restic | 0.16 | BSD-2-Clause | Backup & DR | Encrypted Backup Tool | Ops scripts | The backup mechanism in use: nightly `pg_dump` of all four DBs + `.env` + Caddy/Grafana/Kuma volumes → encrypted off-site repo; restore drill proven (260 s) | Driven by `deploy/scripts/backup.sh`, not a long-running compose service (pgBackRest/WAL is a PLAN.md aspiration, not deployed) |
| Mailpit | v1.31.0 | MIT | Development Tooling | Local SMTP Catcher | Dev-only (`docker-compose.override.yml`) | Captures verification emails during local/e2e testing | Not part of production stack |

## Deployment Profiles Summary

- `core`: Main production stack (edge, identity, IoT core, DB, monitoring, status).
- `flows`: Per-student Node-RED workloads and controlled Docker API access.
- `lab`: JupyterHub-based notebook environment.
- `lora`: LoRaWAN stack (ChirpStack, bridge, MQTT, Redis).

## Notes for Operations

- All images/versions are pinned in project configuration and environment variables.
- **Versions are frozen — there is no upgrade plan (owner ruling).** The branded ThingsBoard and layer4 Caddy images still build once from their pinned tags; no engine is upgraded on a schedule.
- Custom application services (`portal`, `docs`, `lora-bridge`) are project-owned components and are excluded from this open-source systems inventory table.
