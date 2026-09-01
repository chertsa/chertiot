#!/usr/bin/env bash
# Materialize runtime secret files from .env (never committed). Called by `make dev`, CI and deploy.sh.
set -euo pipefail
cd "$(dirname "$0")/../.."
set -a; . ./.env; set +a
# Dir 700 blocks host path traversal; file 644 so containers running as non-root (e.g. the
# prom images' "nobody") can read their bind-mounted secret. Bind mounts bypass dir traversal.
mkdir -p secrets
chmod 700 secrets
umask 022
printf '%s' "${SMTP_PASSWORD:-}" > secrets/alertmanager_smtp_password
chmod 644 secrets/alertmanager_smtp_password
echo "runtime secrets written"
