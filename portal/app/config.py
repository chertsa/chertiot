from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings from environment / .env (never committed). Secrets have no defaults."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: str = "dev"
    domain: str = "chertiot.com"
    portal_secret_key: str
    portal_database_url: str

    # ThingsBoard (D10: REST only). TB_ADMIN_URL overrides for scripts/tests outside compose.
    tb_admin_url: str = "http://tb:8080"
    tb_sysadmin_email: str = "sysadmin@thingsboard.org"
    tb_sysadmin_password: str = ""

    # D4 quota overrides applied on top of templates-tb/tenant-profile-student.json
    tb_quota_max_devices: int | None = None
    tb_quota_device_msg_rate: str | None = None  # e.g. "10:1,300:60"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # required fields are read from the environment
