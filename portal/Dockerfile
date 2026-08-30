FROM python:3.12-slim-bookworm
RUN pip install --no-cache-dir uv==0.12.7
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON=/usr/local/bin/python3.12 UV_PYTHON_DOWNLOADS=never
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --no-install-project
COPY app ./app
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --retries=5 CMD ["/app/.venv/bin/python","-c","import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/healthz')"]
CMD ["/app/.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
