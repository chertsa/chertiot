# Build context is the repo root (docker-compose.yml: build.context=.), so the image carries
# templates-tb/ alongside the app and provisioning resolves it as /templates-tb.
FROM python:3.12-slim-bookworm
RUN pip install --no-cache-dir uv==0.12.7
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON=/usr/local/bin/python3.12 UV_PYTHON_DOWNLOADS=never
COPY portal/pyproject.toml portal/uv.lock portal/.python-version ./
RUN uv sync --frozen --no-dev --no-install-project
COPY portal/app ./app
COPY portal/migrations ./migrations
COPY portal/alembic.ini portal/docker-entrypoint.sh ./
COPY templates-tb /templates-tb
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --retries=5 CMD ["/app/.venv/bin/python","-c","import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/healthz')"]
CMD ["/app/docker-entrypoint.sh"]
