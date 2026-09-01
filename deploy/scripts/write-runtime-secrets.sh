#!/usr/bin/env bash
# Materialize runtime secret files from .env (never committed). Called by `make dev`, CI and deploy.sh.
set -euo pipefail
cd "$(dirname "$0")/../.."
set -a; . ./.env; set +a
umask 077
mkdir -p secrets
printf '%s' "${SMTP_PASSWORD:-}" > secrets/alertmanager_smtp_password
echo "runtime secrets written"
