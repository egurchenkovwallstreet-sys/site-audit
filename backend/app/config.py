from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
_env_file = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_env_file if _env_file.is_file() else None,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    database_url: str = (
        "postgresql+asyncpg://site_audit:change_me@localhost:5432/site_audit"
    )
    cors_origins: str = "http://localhost:3000"

    playwright_enabled: bool = True
    playwright_max_fetches: int = 14

    # Бюджет одного скана (сек): обход + compliance + passive + Nuclei
    scan_time_budget_sec: int = 600
    scan_max_pages: int = 30

    nuclei_enabled: bool = True
    nuclei_timeout_sec: int = 180
    passive_probe_max: int = 12

    scan_queue_max_concurrent: int = 2
    scan_queue_avg_sec: int = 240
    scan_queue_message_min_waiting: int = 5

    scan_rate_limit_per_hour: int = 5
    scan_rate_limit_per_day: int = 20
    scan_rate_limit_burst_10min: int = 2

    admin_email: str = ""
    admin_password: str = ""
    admin_session_secret: str = ""
    admin_session_ttl_sec: int = 604_800

    public_site_url: str = "http://localhost:3000"

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_use_ssl: bool = False
    smtp_starttls: bool = True
    smtp_allow_unauthenticated: bool = False

    # Веб-интерфейс Mailpit на проде (тест без реального SMTP)
    mailpit_public_url: str = ""

    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def database_url_sync(self) -> str:
        """URL для Alembic (синхронный драйвер psycopg)."""
        url = self.database_url
        if url.startswith("postgresql+asyncpg://"):
            return "postgresql+psycopg://" + url.removeprefix("postgresql+asyncpg://")
        if url.startswith("postgresql://"):
            return "postgresql+psycopg://" + url.removeprefix("postgresql://")
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()