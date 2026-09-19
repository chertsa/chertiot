#!/usr/bin/env bash
# CHERT IoT — branded Grafana with Arabic (ar-SA, LTR) localization.
#
# Reproducible, source-built image pinned to an IMMUTABLE tag AND commit. Fails closed on any
# mismatch (never trusts a mutable branch). Mirrors thingsboard-brand/build.sh conventions:
# clone pinned upstream -> apply CHERT changes -> validate -> docker build -> chertiot/grafana:<ver>-b<N>.
# TB/Grafana are FROZEN: this builds the branded image once; there is no upgrade path here.
# Needs a large runner (Go 1.26 + Node 24 + webpack). Run in CI (images.yml), not on a laptop.
set -euo pipefail
cd "$(dirname "$0")"

GRAFANA_VERSION="${GRAFANA_VERSION:-$(grep ^GRAFANA_VERSION= ../.env.example | cut -d= -f2)}"
PIN_COMMIT="afdab62868c728d60df3f87657e68c8ed6dbb926"   # v13.1.4 (verified 2026-09; fail closed)
BRAND_BUILD="${BRAND_BUILD:-$(cat BUILD_NUMBER 2>/dev/null || echo 1)}"
IMAGE="chertiot/grafana:${GRAFANA_VERSION}-b${BRAND_BUILD}"
SRC="upstream"

step() { printf '\n\033[1m== %s\033[0m\n' "$*"; }

if [[ "${1:-}" != "--skip-clone" ]]; then
  step "clone grafana v${GRAFANA_VERSION} (immutable tag)"
  rm -rf "$SRC"
  git clone --depth 1 --branch "v${GRAFANA_VERSION}" https://github.com/grafana/grafana.git "$SRC"
fi

step "verify pinned commit (FAIL CLOSED)"
HEAD="$(git -C "$SRC" rev-parse HEAD)"
if [[ "$HEAD" != "$PIN_COMMIT" ]]; then
  echo "ABORT: upstream HEAD $HEAD != pinned $PIN_COMMIT (tag moved or wrong source)"; exit 1
fi
echo "commit verified: $HEAD"

step "register ar-SA (constants + languages + tests)"
python3 apply-registration.py "$SRC"

step "regenerate ar-SA catalog from committed per-namespace source of truth"
python3 tools/assemble-ar.py "$SRC/public/locales/en-US/grafana.json"

step "install CHERT-maintained locale files into the source tree"
install -D -m 0644 locales/ar-SA/grafana.json \
  "$SRC/public/locales/ar-SA/grafana.json"
install -D -m 0644 locales/ar-SA/grafana-alerting.json \
  "$SRC/packages/grafana-alerting/src/locales/ar-SA/grafana-alerting.json"

step "install CHERT registration test into the source tree"
install -D -m 0644 tests/registration.ar-SA.test.tsx \
  "$SRC/public/app/core/internationalization/registration.ar-SA.test.tsx"

step "validate locales (schema-aware; FAIL CLOSED)"
python3 validate.py "$SRC" --require-complete

# Runtime fallback + Arabic-plural proof (Node only; no Grafana toolchain needed).
step "run i18next fallback test (ar-SA present/fallback/plurals)"
( cd tests && npm install --silent --no-audit --no-fund && node i18n-fallback.test.mjs )

# The heavy repo-level tests run in CI where the Grafana toolchain is installed:
#   yarn install --immutable
#   yarn test --testPathPattern 'internationalization/(languages|registration.ar-SA)'
# (upstream languages.test.ts is amended by apply-registration.py to include ar-SA and fails closed).
if [[ "${RUN_GRAFANA_JEST:-0}" == "1" ]]; then
  step "run Grafana jest registration tests (CI)"
  ( cd "$SRC" && yarn install --immutable && \
    yarn jest public/app/core/internationalization/registration.ar-SA.test.tsx \
              packages/grafana-i18n/src/languages.test.ts )
fi

step "docker build (Grafana root Dockerfile; OSS build tags)"
docker build -t "$IMAGE" "$SRC"
echo "$IMAGE" > LAST_IMAGE
step "built $IMAGE"
