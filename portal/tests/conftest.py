import os

# Test-only values; production reads real secrets from .env (never committed).
os.environ.setdefault("PORTAL_SECRET_KEY", "test-secret")
os.environ.setdefault("PORTAL_DATABASE_URL", "postgresql+psycopg://test:test@localhost:5432/test")
