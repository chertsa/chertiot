import os

# Test-only values; production reads real secrets from .env (never committed).
os.environ.setdefault("PORTAL_SECRET_KEY", "test-secret")
os.environ.setdefault("PORTAL_DATABASE_URL", "postgresql+psycopg://test:test@localhost:5432/test")

# e2e tests read the project .env (populated by `make dev`); unit tests don't need it.
_env = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
if os.path.exists(_env):
    for _line in open(_env):
        _line = _line.split("#", 1)[0].strip()
        if "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())
