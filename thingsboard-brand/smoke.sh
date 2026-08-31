#!/usr/bin/env bash
# Smoke test a branded image: start it standalone (no DB needed for static assets) and check strings.
set -euo pipefail
IMAGE="${1:?image}"
CID=$(docker create "$IMAGE")
trap 'docker rm -f "$CID" >/dev/null' EXIT
docker cp "$CID:/usr/share/thingsboard/bin/thingsboard.jar" /tmp/tb-brand-smoke.jar
cd /tmp && rm -rf tb-brand-smoke && mkdir tb-brand-smoke && cd tb-brand-smoke
unzip -q -o ../tb-brand-smoke.jar 'BOOT-INF/lib/ui-ngx-*.jar' 'BOOT-INF/classes/templates/*'
unzip -q -o BOOT-INF/lib/ui-ngx-*.jar 'public/index.html' 'public/assets/logo_title_white.svg' 'public/assets/locale/*' 2>/dev/null || unzip -q -o BOOT-INF/lib/ui-ngx-*.jar
ok=1
grep -q '<title>CHERT IoT</title>' public/index.html || { echo "FAIL: index title"; ok=0; }
grep -q 'CHERT' public/assets/logo_title_white.svg || { echo "FAIL: logo asset"; ok=0; }
grep -q 'powered by ThingsBoard' public/assets/locale/locale.constant-en_US.json || { echo "FAIL: attribution string"; ok=0; }
grep -q 'CHERT IoT' BOOT-INF/classes/templates/activation.ftl || { echo "FAIL: email template"; ok=0; }
[[ $ok == 1 ]] && echo "smoke OK: $IMAGE"
