#!/usr/bin/env bash
# Nightly backup (M2.3, D9): pg_dump of every database (thingsboard, keycloak, portal) + WAL-level
# pgBackRest is configured separately (deploy/pgbackrest/); this script produces the restic push:
#   dumps + .env + Caddy TLS storage + named volumes (Grafana/Uptime Kuma) → encrypted restic repo.
# Writes a textfile-collector metric for the BackupTooOld alert. Cron: 0 3 * * * (see runbooks/backup.md).
set -euo pipefail
cd "$(dirname "$0")/../.."
set -a; . ./.env; set +a
: "${RESTIC_REPOSITORY:?set in .env}" "${RESTIC_PASSWORD:?set in .env}"
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
WORK=$(mktemp -d /var/tmp/chertiot-backup.XXXXXX); trap 'rm -rf "$WORK"' EXIT
METRIC_DIR=${NODE_TEXTFILE_DIR:-/var/lib/node_exporter/textfile}
mkdir -p "$WORK/db" "$WORK/config" "$METRIC_DIR" 2>/dev/null || true

for db in thingsboard keycloak portal; do
  docker compose -f docker-compose.yml exec -T postgres pg_dump -U "$POSTGRES_USER" -Fc "$db" > "$WORK/db/$db.dump"
done
cp .env "$WORK/config/env"
docker run --rm -v chertiot_caddy-data:/from:ro -v "$WORK":/to alpine:3.20 sh -c 'cd /from && tar czf /to/caddy-data.tgz .'
docker run --rm -v chertiot_grafana-data:/from:ro -v "$WORK":/to alpine:3.20 sh -c 'cd /from && tar czf /to/grafana-data.tgz .'
docker run --rm -v chertiot_uptime-kuma-data:/from:ro -v "$WORK":/to alpine:3.20 sh -c 'cd /from && tar czf /to/uptime-kuma-data.tgz .'

restic backup --tag chertiot --tag "$STAMP" "$WORK"
restic forget --tag chertiot --keep-daily 7 --keep-weekly 4 --keep-monthly 6 --prune
echo "chertiot_backup_last_success_timestamp_seconds $(date +%s)" > "$METRIC_DIR/chertiot_backup.prom.$$" && mv "$METRIC_DIR/chertiot_backup.prom.$$" "$METRIC_DIR/chertiot_backup.prom"
echo "backup $STAMP ok"
