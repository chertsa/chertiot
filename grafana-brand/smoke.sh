#!/usr/bin/env bash
# Offline smoke of a freshly built branded Grafana image: it starts, is healthy, ships the ar-SA
# locale, and records the image digest. No production access.
set -euo pipefail
IMAGE="${1:?image ref}"
NAME="gf-smoke-$$"
echo "digest: $(docker inspect --format '{{index .RepoDigests 0}}{{.Id}}' "$IMAGE" 2>/dev/null | head -c 80)"
echo "== ar-SA locale present in image =="
docker run --rm --entrypoint sh "$IMAGE" -c 'test -s /usr/share/grafana/public/locales/ar-SA/grafana.json && echo "grafana.json OK" && test -s /usr/share/grafana/public/locales/ar-SA/grafana-alerting.json && echo "grafana-alerting.json OK"'
echo "== container starts + /api/health =="
docker run -d --name "$NAME" -p 13000:3000 "$IMAGE" >/dev/null
for i in $(seq 1 30); do
  curl -sf http://127.0.0.1:13000/api/health >/dev/null 2>&1 && break; sleep 2
done
curl -sf http://127.0.0.1:13000/api/health && echo " health OK"
docker rm -f "$NAME" >/dev/null
echo "smoke passed for $IMAGE"
