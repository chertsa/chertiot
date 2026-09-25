# Static docs: build with mkdocs-material, serve with nginx under /docs/ (Caddy handle_path strips the prefix).
FROM ghcr.io/chertsa/chertiot-base-mkdocs-material:9.7.7 AS build
RUN pip install --no-cache-dir mkdocs-static-i18n==1.3.1
WORKDIR /docs
COPY . .
RUN mkdocs build --strict --site-dir /site
FROM ghcr.io/chertsa/chertiot-base-nginx:1.31.4-alpine
COPY --from=build /site /usr/share/nginx/html
