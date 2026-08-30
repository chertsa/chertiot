#!/usr/bin/env bash
# Restore drill (M2.3): rebuild the platform from the latest restic snapshot onto a scratch host or
# directory, time it, and verify. Target: < 1 hour. Usage: ./restore-drill.sh /srv/chertiot-restore
set -euo pipefail
TARGET="${1:?target directory on the scratch host}"
: "${RESTIC_REPOSITORY:?}" "${RESTIC_PASSWORD:?}"
T0=$(date +%s)
mkdir -p "$TARGET" && cd "$TARGET"
echo "== 1. code"; [ -d repo ] || git clone --depth 1 https://github.com/<org>/chertiot.git repo
echo "== 2. latest snapshot"; restic restore latest --tag chertiot --target restore
SNAP=$(find restore -maxdepth 3 -type d -name 'chertiot-backup.*' | head -1)
cp "$SNAP/config/env" repo/.env
cd repo
echo "== 3. postgres + restore dumps"
docker compose -f docker-compose.yml --profile core up -d postgres && sleep 10
set -a; . ./.env; set +a
for db in thingsboard keycloak portal; do
  docker compose -f docker-compose.yml exec -T postgres pg_restore -U "$POSTGRES_USER" -d "$db" --clean --if-exists < "../$SNAP/db/$db.dump" || true
done
echo "== 4. volumes"
for v in caddy-data grafana-data uptime-kuma-data; do
  docker run --rm -v "chertiot_${v}:/to" -v "$(cd .. && pwd)/$SNAP:/from:ro" alpine:3.20 sh -c "cd /to && tar xzf /from/${v}.tgz"
done
echo "== 5. full stack"; docker compose -f docker-compose.yml --profile core up -d; make wait-healthy
echo "== 6. verify"; curl -fsS -o /dev/null http://127.0.0.1:8080/login && echo "TB login page OK"
echo "restore drill took $(( $(date +%s) - T0 ))s"
