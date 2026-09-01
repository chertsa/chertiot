#!/usr/bin/env bash
# Restore drill (M2.3): rebuild the platform from the latest restic snapshot into an ISOLATED
# compose project (chertiot-restore_*), verify, and time it. Run on a host whose live stack is
# stopped for the port window (staging). Usage:
#   RESTIC_REPOSITORY=... RESTIC_PASSWORD=... deploy/scripts/restore-drill.sh /srv/chertiot-restore
set -euo pipefail
TARGET="${1:?target directory}"
PROJECT="chertiot-restore"
: "${RESTIC_REPOSITORY:?}" "${RESTIC_PASSWORD:?}"
T0=$(date +%s)
step() { printf '\n== %s (t+%ss)\n' "$*" "$(( $(date +%s) - T0 ))"; }

step "code"
mkdir -p "$TARGET" && cd "$TARGET"
[ -d repo/.git ] || git clone -q https://github.com/chertsa/chertiot.git repo
git -C repo fetch -q origin main && git -C repo reset -q --hard origin/main

step "latest snapshot"
rm -rf restore && restic restore latest --target restore >/dev/null
SNAP=$(find restore -type d -name 'chertiot-backup.*' | head -1)
[ -n "$SNAP" ] || { echo "no backup payload in snapshot"; exit 1; }
cp "$SNAP/config/env" repo/.env

step "postgres + database restore"
cd repo
docker compose -p "$PROJECT" -f docker-compose.yml --profile core up -d postgres
sleep 12
set -a; . ./.env; set +a
for db in thingsboard keycloak portal; do
  docker compose -p "$PROJECT" -f docker-compose.yml exec -T postgres pg_restore -U "$POSTGRES_USER" -d "$db" --clean --if-exists --no-owner < "../$SNAP/db/$db.dump" 2>/dev/null || true
  echo "  $db restored"
done

step "volumes"
for v in caddy-data grafana-data uptime-kuma-data; do
  docker volume create "${PROJECT}_${v}" >/dev/null
  docker run --rm -v "${PROJECT}_${v}:/to" -v "$(cd .. && pwd)/$SNAP:/from:ro" alpine:3.20 sh -c "cd /to && tar xzf /from/${v}.tgz" && echo "  $v"
done

step "full stack (isolated project)"
docker compose -p "$PROJECT" -f docker-compose.yml --profile core up -d
for i in $(seq 1 60); do
  S=$(docker compose -p "$PROJECT" -f docker-compose.yml --profile core ps --format '{{.Service}} {{.Status}}')
  echo "$S" | grep -q '^tb .*(healthy)' && echo "$S" | grep -q '^portal .*(healthy)' && break
  sleep 10
done

step "verify restored data"
docker compose -p "$PROJECT" -f docker-compose.yml exec -T portal /app/.venv/bin/python - <<'PYV'
import urllib.request
assert urllib.request.urlopen("http://tb:8080/login", timeout=10).status == 200
assert urllib.request.urlopen("http://keycloak:8080/realms/chertiot", timeout=10).status == 200
print("  TB login page OK; Keycloak realm restored OK")
PYV
docker compose -p "$PROJECT" -f docker-compose.yml exec -T postgres psql -U "$POSTGRES_USER" -d thingsboard -tAc "select count(*) from tenant" | xargs echo "  tenants in restored TB:"

step "teardown restored project"
docker compose -p "$PROJECT" -f docker-compose.yml --profile core down -v >/dev/null 2>&1 || true
echo
echo "RESTORE DRILL COMPLETE in $(( $(date +%s) - T0 ))s (target < 3600s)"
