#!/usr/bin/env bash
# CHERT IoT — deploy/upgrade one environment (M2.2/M2.3). Run FROM this repo on a workstation/CI:
#   deploy/scripts/deploy.sh <host> <domain>            e.g. deploy.sh 2.29.25.134 stage.chertiot.com
# Idempotent. First run: clones the repo on the server, generates .env (random secrets), asks
# nothing; later runs: git pull + compose up + migrations. SMTP creds are read from
# deploy/secrets.<domain>.env on the workstation if present (never committed) and merged once.
set -euo pipefail
HOST="${1:?server ip}"; DOMAIN="${2:?public domain, e.g. stage.chertiot.com}"
KEY="${DEPLOY_KEY:-$HOME/.ssh/chertiot_deploy}"
RUN="ssh -i $KEY -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new chertiot@$HOST"
REPO="https://github.com/chertsa/chertiot.git"
step() { printf '\n\033[1m== %s\033[0m\n' "$*"; }

step "code on $HOST"
$RUN "sudo install -d -o chertiot -g chertiot /srv/chertiot; if [ -d /srv/chertiot/.git ]; then cd /srv/chertiot && git fetch -q origin main && git reset -q --hard origin/main; else git clone -q $REPO /srv/chertiot; fi; cd /srv/chertiot && git log --oneline -1"

step ".env"
$RUN "cd /srv/chertiot && [ -f .env ] || { deploy/scripts/ci-env.sh; \
  sed -i \"s|^ENV=.*|ENV=prod|; s|^DOMAIN=.*|DOMAIN=$DOMAIN|; s|^CADDYFILE=.*|CADDYFILE=deploy/caddy/Caddyfile.prod|; \
    s|^KC_HOSTNAME=.*|KC_HOSTNAME=https://auth.$DOMAIN|; s|^TB_PUBLIC_URL=.*|TB_PUBLIC_URL=https://app.$DOMAIN|; \
    s|^PORTAL_PUBLIC_URL=.*|PORTAL_PUBLIC_URL=https://$DOMAIN|; s|^MQTT_HOST=.*|MQTT_HOST=$DOMAIN|; s|^MQTT_PORT=.*|MQTT_PORT=8883|; \
    s|^SMTP_HOST=.*|SMTP_HOST=|; s|^TB_SYSADMIN_PASSWORD=.*|TB_SYSADMIN_PASSWORD=\$(openssl rand -hex 12)|\" .env; echo '.env generated'; }"
if [ -f "deploy/secrets.$DOMAIN.env" ]; then
  step "merge secrets from deploy/secrets.$DOMAIN.env (server-side, quoting-safe)"
  scp -q -i "$KEY" -o IdentitiesOnly=yes "deploy/secrets.$DOMAIN.env" "chertiot@$HOST:/srv/chertiot/.secrets.merge"
  $RUN "cd /srv/chertiot && python3 - <<'PYMERGE'
lines = open('.env').read().split('\n')
merge = {}
for raw in open('.secrets.merge').read().split('\n'):
    raw = raw.strip()
    if raw and '=' in raw and not raw.startswith('#'):
        k, v = raw.split('=', 1)
        merge[k] = v
seen = set()
for i, line in enumerate(lines):
    k = line.split('=', 1)[0]
    if k in merge:
        lines[i] = k + '=' + merge[k]
        seen.add(k)
lines.extend(k + '=' + v for k, v in merge.items() if k not in seen)
open('.env', 'w').write('\n'.join(lines))
print('merged:', ', '.join(sorted(merge)))
PYMERGE
rm -f /srv/chertiot/.secrets.merge"
fi

step "compose up (production file only, no dev override)"
$RUN "cd /srv/chertiot && docker compose -f docker-compose.yml --profile core pull -q --ignore-buildable && docker compose -f docker-compose.yml --profile core up -d --build && docker compose -f docker-compose.yml --profile core ps --format '{{.Service}} {{.Status}}'"

step "wait for tb + keycloak + portal healthy (up to 10 min)"
$RUN 'cd /srv/chertiot && for i in $(seq 1 60); do S=$(docker compose -f docker-compose.yml --profile core ps --format "{{.Service}} {{.Status}}"); echo "$S" | grep -q "^tb .*(healthy)" && echo "$S" | grep -q "^keycloak .*(healthy)" && echo "$S" | grep -q "^portal .*(healthy)" && exit 0; sleep 10; done; echo "$S"; exit 1'

step "bootstrap: rotate TB sysadmin, keycloak realm, tb oauth2 (idempotent, inside the portal container)"
$RUN "cd /srv/chertiot && set -a && . ./.env && set +a && \
  docker compose -f docker-compose.yml exec -T -e KC_ADMIN_URL=http://keycloak:8080 -e TB_ADMIN_URL=http://tb:8080 -e ENV -e DOMAIN -e KC_HOSTNAME -e KC_INTERNAL_URL -e KC_REALM -e KC_SECRET_THINGSBOARD -e KC_SECRET_PORTAL -e KC_SECRET_JUPYTERHUB -e KC_SECRET_GRAFANA -e KEYCLOAK_ADMIN -e KEYCLOAK_ADMIN_PASSWORD -e TB_PUBLIC_URL -e PORTAL_PUBLIC_URL -e MQTT_HOST -e MQTT_PORT -e SMTP_HOST -e SMTP_PORT -e SMTP_USER -e SMTP_PASSWORD -e SMTP_FROM -e SMTP_STARTTLS -e TB_SYSADMIN_EMAIL -e TB_SYSADMIN_PASSWORD portal /app/.venv/bin/python -m scripts.rotate_tb_sysadmin && \
  docker compose -f docker-compose.yml exec -T -e KC_ADMIN_URL=http://keycloak:8080 -e TB_ADMIN_URL=http://tb:8080 -e ENV -e DOMAIN -e KC_HOSTNAME -e KC_INTERNAL_URL -e KC_REALM -e KC_SECRET_THINGSBOARD -e KC_SECRET_PORTAL -e KC_SECRET_JUPYTERHUB -e KC_SECRET_GRAFANA -e KEYCLOAK_ADMIN -e KEYCLOAK_ADMIN_PASSWORD -e TB_PUBLIC_URL -e PORTAL_PUBLIC_URL -e MQTT_HOST -e MQTT_PORT -e SMTP_HOST -e SMTP_PORT -e SMTP_USER -e SMTP_PASSWORD -e SMTP_FROM -e SMTP_STARTTLS -e TB_SYSADMIN_EMAIL -e TB_SYSADMIN_PASSWORD portal /app/.venv/bin/python -m scripts.setup_keycloak && \
  docker compose -f docker-compose.yml exec -T -e KC_ADMIN_URL=http://keycloak:8080 -e TB_ADMIN_URL=http://tb:8080 -e ENV -e DOMAIN -e KC_HOSTNAME -e KC_INTERNAL_URL -e KC_REALM -e KC_SECRET_THINGSBOARD -e KC_SECRET_PORTAL -e KC_SECRET_JUPYTERHUB -e KC_SECRET_GRAFANA -e KEYCLOAK_ADMIN -e KEYCLOAK_ADMIN_PASSWORD -e TB_PUBLIC_URL -e PORTAL_PUBLIC_URL -e MQTT_HOST -e MQTT_PORT -e SMTP_HOST -e SMTP_PORT -e SMTP_USER -e SMTP_PASSWORD -e SMTP_FROM -e SMTP_STARTTLS -e TB_SYSADMIN_EMAIL -e TB_SYSADMIN_PASSWORD portal /app/.venv/bin/python -m scripts.setup_tb_oauth2"

step "smoke: public endpoints"
for url in "https://$DOMAIN/healthz" "https://app.$DOMAIN/login" "https://auth.$DOMAIN/realms/chertiot"; do
  printf '  %-46s ' "$url"; curl -s -o /dev/null -w '%{http_code}\n' --max-time 20 "$url" || true
done
echo "deploy of $DOMAIN done"
