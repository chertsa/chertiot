#!/usr/bin/env bash
# Offline smoke of a freshly built branded Grafana image. Proves the ar-SA locale is actually
# shipped and compiled into the frontend the image serves (not merely inferred from raw JSON), and
# that the container starts healthy. Records the image digest. No prod access.
#
# LTR is asserted AUTHORITATIVELY by the jest test registration.ar-SA.test.tsx ("is LTR: the
# definition carries no direction/rtl field"), which runs in build.sh, and is guaranteed by
# construction: Grafana has NO language->direction mechanism (no i18next.dir()/documentElement.dir
# wiring; the only `direction:'rtl'` in the tree is an unrelated NumberInput style). Registering
# ar-SA therefore does not switch the UI to RTL. A grep for "rtl" in the minified single-line bundle
# is unsound (every RTL locale's data coexists on the same line) and is deliberately NOT used here.
set -euo pipefail
IMAGE="${1:?image ref}"
NAME="gf-smoke-$$"
BUILD=/usr/share/grafana/public/build          # compiled frontend (hashed JS chunks)
LOCALES=/usr/share/grafana/public/locales      # raw catalog JSON (webpack leaves it in place)

echo "== image digest =="
docker inspect --format '{{if .RepoDigests}}{{index .RepoDigests 0}}{{else}}{{.Id}}{{end}}' "$IMAGE"

echo "== ar-SA registered in the COMPILED frontend =="
# 'ar-SA' is an ASCII code string emitted literally into the bundle: the @grafana/i18n LANGUAGES
# registry and the import(`../../../locales/${locale}/grafana.json`) context module both carry it.
# Recursive over build/ (chunks live in subdirs), so this proves the loader/registration compiled in
# — not just that a raw JSON file happens to sit in the image.
docker run --rm --entrypoint sh "$IMAGE" -c "grep -rlq -- 'ar-SA' $BUILD" \
  || { echo 'ERROR: ar-SA not found in the compiled frontend bundle'; exit 1; }
echo "ar-SA present in compiled bundle: OK"

echo "== ar-SA catalog shipped in the image =="
# The catalog must be in the image. Prefer the compiled chunk (import() target). Terser may emit the
# Arabic as \u escapes, so fall back to the raw JSON that webpack leaves under public/locales — either
# proves the catalog ships; report which. Both absent is a real failure.
if docker run --rm --entrypoint sh "$IMAGE" -c "grep -rlq 'لوحة المعلومات' $BUILD 2>/dev/null"; then
  echo "compiled ar-SA catalog string found in build/: OK"
elif docker run --rm --entrypoint sh "$IMAGE" -c "test -s $LOCALES/ar-SA/grafana.json && grep -q 'لوحة المعلومات' $LOCALES/ar-SA/grafana.json"; then
  echo "ar-SA catalog present as raw JSON at locales/ar-SA/grafana.json: OK (the import() loader compiles it into a chunk)"
else
  echo "ERROR: ar-SA catalog not found in build/ or locales/ar-SA/"; exit 1
fi

echo "== container starts + /api/health =="
docker run -d --name "$NAME" -p 13000:3000 "$IMAGE" >/dev/null
trap 'docker rm -f "$NAME" >/dev/null 2>&1 || true' EXIT
for _ in $(seq 1 30); do
  curl -sf http://127.0.0.1:13000/api/health >/dev/null 2>&1 && break; sleep 2
done
curl -sf http://127.0.0.1:13000/api/health && echo " health OK"

echo "LTR preserved by construction (asserted in the jest registration test; no per-locale dir in Grafana)"
echo "smoke passed for $IMAGE"
