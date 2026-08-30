import os

# Test-only values; production reads real secrets from .env (never committed).
os.environ.setdefault("PORTAL_SECRET_KEY", "test-secret")
import tempfile

_tmpdb = os.path.join(tempfile.mkdtemp(prefix="chertiot-test-"), "portal.db")
# Tests never touch the real portal DB, whatever .env says.
os.environ["PORTAL_DATABASE_URL"] = f"sqlite:///{_tmpdb}"

# e2e tests read the project .env (populated by `make dev`); unit tests don't need it.
_env = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
if os.path.exists(_env):
    for _line in open(_env):
        _line = _line.split("#", 1)[0].strip()
        if "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())
