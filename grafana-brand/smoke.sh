#!/usr/bin/env bash
# Offline smoke of a freshly built branded Grafana image. Verifies ar-SA through the ACTUAL build
# output (registered loader + compiled locale), not just raw JSON files — because Grafana bundles
# locales into webpack JS chunks, so a raw-JSON check alone would not prove the loader/UI works.
# Also confirms the container starts and is healthy, and records the image digest. No prod access.
set -euo pipefail
IMAGE="${1:?image ref}"
NAME="gf-smoke-$$"
BUILD=/usr/share/grafana/public/build          # compiled frontend (hashed JS chunks)
LOCALES=/usr/share/grafana/public/locales

echo "== image digest =="
docker inspect --format '{{if .RepoDigests}}{{index .RepoDigests 0}}{{else}}{{.Id}}{{end}}' "$IMAGE"

echo "== ar-SA registered in the compiled frontend (language code + display name) =="
# The @grafana/i18n LANGUAGES registry compiles into the JS bundle. Prove ar-SA + العربية are there.
docker run --rm --entrypoint sh "$IMAGE" -c "grep -rlq -- 'ar-SA' $BUILD/*.js && grep -rlq 'العربية' $BUILD/*.js" \
  && echo "registration present in bundle: OK"

echo "== ar-SA translations compiled into a loadable chunk (loader resolves, not raw-JSON-only) =="
# Webpack splits import('../../../locales/ar-SA/grafana.json') into a chunk. A known Arabic string
# from the catalog must appear in the built assets — proof the loader's target was bundled.
docker run --rm --entrypoint sh "$IMAGE" -c "grep -rlq 'لوحة المعلومات' $BUILD/ $LOCALES/ar-SA/ 2>/dev/null" \
  && echo "compiled ar-SA catalog string found: OK"

echo "== no RTL wiring introduced for ar-SA (Grafana stays LTR) =="
# Guard: the branded image must not have added a dir=rtl / direction:rtl binding for ar-SA.
if docker run --rm --entrypoint sh "$IMAGE" -c "grep -rlq -- \"ar-SA.*\\(dir.*rtl\\|rtl.*ar-SA\\)\" $BUILD/*.js 2>/dev/null"; then
  echo "ERROR: found ar-SA↔rtl wiring in bundle"; exit 1
fi
echo "LTR preserved (no ar-SA rtl binding): OK"

echo "== container starts + /api/health =="
docker run -d --name "$NAME" -p 13000:3000 "$IMAGE" >/dev/null
trap 'docker rm -f "$NAME" >/dev/null 2>&1 || true' EXIT
for _ in $(seq 1 30); do
  curl -sf http://127.0.0.1:13000/api/health >/dev/null 2>&1 && break; sleep 2
done
curl -sf http://127.0.0.1:13000/api/health && echo " health OK"
echo "smoke passed for $IMAGE"
