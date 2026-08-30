#!/usr/bin/env bash
# CHERT IoT — ThingsBoard CE branded build (D2/D7).
#   clone pinned upstream tag → apply patches/ in order → Maven build inside Docker → image chertiot/tb:<tag>-b<N>
# Usage: ./build.sh [--skip-clone] [--no-docker]     (env: TB_VERSION, BRAND_BUILD=N, JAVA_MEM=6g)
# Needs ~8 GB RAM for the Maven/Angular build. Reproducible: no host Java required (build runs in maven:3.9-eclipse-temurin-17).
set -euo pipefail
cd "$(dirname "$0")"
TB_VERSION="${TB_VERSION:-$(grep ^TB_VERSION= ../.env.example | cut -d= -f2)}"
BRAND_BUILD="${BRAND_BUILD:-$(cat BUILD_NUMBER 2>/dev/null || echo 1)}"
IMAGE="chertiot/tb:${TB_VERSION}-b${BRAND_BUILD}"
JAVA_MEM="${JAVA_MEM:-6g}"
MAVEN_IMAGE="maven:3.9.12-eclipse-temurin-17"
SRC="upstream"

step() { printf '\n\033[1m== %s\033[0m\n' "$*"; }

if [[ "${1:-}" != "--skip-clone" ]]; then
  step "clone thingsboard v${TB_VERSION}"
  rm -rf "$SRC"
  git clone --depth 1 --branch "v${TB_VERSION}" https://github.com/thingsboard/thingsboard.git "$SRC"
fi

step "apply patch series"
( cd "$SRC" && git checkout -- . && for p in ../patches/*.patch; do echo " - $(basename "$p")"; git apply --check "$p"; git apply "$p"; done )
step "copy brand assets"
cp assets/logo_title_white.svg "$SRC/ui-ngx/src/assets/logo_title_white.svg"
cp assets/logo_white.svg       "$SRC/ui-ngx/src/assets/logo_white.svg"
cp assets/favicon.ico          "$SRC/ui-ngx/src/thingsboard.ico"
cp assets/favicon.ico          "$SRC/ui-ngx/src/assets/favicon.ico" 2>/dev/null || true

step "build (Maven, inside Docker) — this takes 20–60 min"
# -DskipTests, license check off (we keep Apache-2.0 headers but our brand assets have none),
# only the modules the tb-node image needs (application + its deps + msa/tb-node), docker image built by the tb-node module.
docker run --rm \
  -v "$PWD/$SRC:/src" -v "${HOME}/.m2:/root/.m2" -v /var/run/docker.sock:/var/run/docker.sock \
  -w /src -e MAVEN_OPTS="-Xmx${JAVA_MEM}" "$MAVEN_IMAGE" \
  mvn -B -q clean install -DskipTests -Dlicense.skip=true -Ddockerfile.skip=false -Dpush.docker.image=false \
      -pl msa/tb-node -am
# The upstream module tags the image thingsboard/tb-node:<version>; retag as ours.
docker tag "thingsboard/tb-node:${TB_VERSION}" "$IMAGE"
step "built $IMAGE"
echo "$IMAGE" > LAST_IMAGE
