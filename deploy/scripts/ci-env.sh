#!/usr/bin/env bash
# Generate a throwaway .env for CI from .env.example (random secrets, dev mail catcher).
set -euo pipefail
cd "$(dirname "$0")/../.."
rand() { openssl rand -hex 16; }
sed -e "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$(rand)|" \
    -e "s|^KEYCLOAK_ADMIN_PASSWORD=.*|KEYCLOAK_ADMIN_PASSWORD=$(rand)|" \
    -e "s|^PORTAL_SECRET_KEY=.*|PORTAL_SECRET_KEY=$(rand)|" \
    -e "s|^GRAFANA_ADMIN_PASSWORD=.*|GRAFANA_ADMIN_PASSWORD=$(rand)|" \
    -e "s|^KC_SECRET_\([A-Z]*\)=.*|KC_SECRET_\1=$(rand)|" \
    -e "s|^DEV_TEST_USER_PASSWORD=.*|DEV_TEST_USER_PASSWORD=$(rand)|" \
    -e "s|^SMTP_HOST=.*|SMTP_HOST=mailpit|" -e "s|^SMTP_PORT=.*|SMTP_PORT=1025|" -e "s|^SMTP_STARTTLS=.*|SMTP_STARTTLS=false|" \
    -e "s|^MQTT_HOST=.*|MQTT_HOST=localhost|" -e "s|^MQTT_PORT=.*|MQTT_PORT=1883|" \
    .env.example > .env
PW=$(grep ^POSTGRES_PASSWORD= .env | cut -d= -f2)
sed -i.bak "s|chertiot:change-me@postgres|chertiot:${PW}@postgres|" .env && rm -f .env.bak
echo ".env generated for CI"
