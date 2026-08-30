# Backup & restore (M2.3)

- **What:** nightly `deploy/scripts/backup.sh` (cron 03:00 UTC as the deploy user): `pg_dump -Fc` of `thingsboard`, `keycloak`, `portal`; `.env`; Caddy TLS storage; Grafana and Uptime Kuma volumes → restic (encrypted) to `RESTIC_REPOSITORY` (Hetzner Storage Box / S3). Retention 7d/4w/6m.
- **Point-in-time:** pgBackRest with WAL archiving (D9) — config in `deploy/pgbackrest/` once the secondary storage exists; RPO with pg_dump alone is 24 h.
- **Alert:** `BackupTooOld` fires if no success metric in 26 h (`monitoring/prometheus/rules/platform.yml`).
- **Drill:** `deploy/scripts/restore-drill.sh /srv/chertiot-restore` on the staging host; record the time here after each drill. Target < 1 h.

| Date | Snapshot | Duration | Notes |
|---|---|---|---|
| — | — | — | first drill pending (needs staging VPS) |
