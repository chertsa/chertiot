from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings from environment / .env (never committed). Secrets have no defaults."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: str = "dev"
    domain: str = "chertiot.com"
    portal_secret_key: str
    portal_database_url: str


@lru_cache
def get_settings() -> Settings:
    return Settings()  # required fields are read from the environment
