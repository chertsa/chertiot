# CHERT branding overlay on the (already source-built, ghcr-hosted) chertiot-grafana image.
# Swaps the top-left logo, favicons and the "Grafana" app title for CHERT IoT — no external base.
# Rebuilding Grafana from source is frozen; this thin layer keeps branding durable across deploys.
ARG GRAFANA_BASE=ghcr.io/chertsa/chertiot-grafana:13.1.4-b1
FROM ${GRAFANA_BASE}
USER root
COPY grafana_icon.svg /usr/share/grafana/public/img/grafana_icon.svg
COPY fav32.png apple-touch-icon.png /usr/share/grafana/public/img/
RUN set -eux; GD=/usr/share/grafana/public; \
    for f in "$GD"/build/static/img/grafana_icon.*.svg; do cp "$GD/img/grafana_icon.svg" "$f"; done; \
    cp "$GD/img/fav32.png"           "$GD/build/img/fav32.png"; \
    cp "$GD/img/apple-touch-icon.png" "$GD/build/img/apple-touch-icon.png"; \
    JS="$(grep -rl 'this.AppTitle="Grafana"' "$GD"/build/*.js | head -1)"; \
    sed -i 's/this.AppTitle="Grafana"/this.AppTitle="CHERT IoT"/; s/this.LoginTitle="Welcome to Grafana"/this.LoginTitle="Welcome to CHERT IoT"/' "$JS"
USER 472
