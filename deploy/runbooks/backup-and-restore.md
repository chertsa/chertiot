# Backup & restore (M2.3)

- **What:** nightly `deploy/scripts/backup.sh` (cron 03:00 UTC as the deploy user): `pg_dump -Fc` of `thingsboard`, `keycloak`, `portal`; `.env`; Caddy TLS storage; Grafana and Uptime Kuma volumes → restic (encrypted) to `RESTIC_REPOSITORY` (Hetzner Storage Box / S3). Retention 7d/4w/6m.
- **Point-in-time:** pgBackRest with WAL archiving (D9) — config in `deploy/pgbackrest/` once the secondary storage exists; RPO with pg_dump alone is 24 h.
- **Alert:** `BackupTooOld` fires if no success metric in 26 h (`monitoring/prometheus/rules/platform.yml`).
- **Drill:** `deploy/scripts/restore-drill.sh /srv/chertiot-restore` on the staging host; record the time here after each drill. Target < 1 h.

| Date | Snapshot | Duration | Notes |
|---|---|---|---|
| 2026-09-01 | latest (first nightly snapshot, prod→staging sftp) | **260 s** | Full drill on staging: restic restore → pg_restore ×3 → volumes → isolated compose project → TB login + realm + tenant verified → teardown. Fixes folded in: installer marker pre-set, unconditional teardown, caddy force-recreate after the port window. |
