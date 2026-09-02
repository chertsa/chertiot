from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings from environment / .env (never committed). Secrets have no defaults."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: str = "dev"
    domain: str = "chertiot.com"
    portal_secret_key: str
    portal_database_url: str
    portal_public_url: str = "http://localhost"

    # Keycloak (D3): public issuer for browser redirects + token validation; internal URL for the
    # admin API. In dev the portal container resolves *.localhost to the host, so both work.
    kc_hostname: str = "http://auth.localhost"
    kc_internal_url: str = "http://keycloak:8080"
    kc_realm: str = "chertiot"
    kc_secret_portal: str = ""

    # ThingsBoard (D10: REST only). TB_ADMIN_URL overrides for scripts/tests outside compose.
    tb_admin_url: str = "http://tb:8080"
    tb_public_url: str = "http://app.localhost"
    tb_sysadmin_email: str = "sysadmin@thingsboard.org"
    tb_sysadmin_password: str = ""

    # Device connectivity as shown to students (snippets, device pages).
    mqtt_host: str | None = None  # default: DOMAIN
    mqtt_port: int = 8883  # 1883 for local dev (no TLS)
    firmware_dir: str | None = (
        None  # default: <repo>/firmware-examples (or /firmware-examples in the image)
    )

    # M3.2: shared secret for the in-network lab-token endpoint (JupyterHub → portal)
    lab_internal_secret: str = ""

    # D4 quota overrides applied on top of templates-tb/tenant-profile-student.json
    tb_quota_max_devices: int | None = None
    tb_quota_device_msg_rate: str | None = None  # e.g. "10:1,300:60"

    @property
    def device_mqtt_host(self) -> str:
        return self.mqtt_host or self.domain

    @property
    def kc_issuer(self) -> str:
        return f"{self.kc_hostname.rstrip('/')}/realms/{self.kc_realm}"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # required fields are read from the environment
