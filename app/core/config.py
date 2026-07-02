"""Config global de la app (único lector de variables de entorno)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Config global cargada del entorno / `.env`. Único lector de variables."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    env: str = "local"
    whatsapp_app_secret: str = ""
    encryption_secret_key: str = ""
    webhook_add_message_endpoint: str = ""
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"
    reports_api_base_url: str = "https://terremoto.hazlohoy.org"
    reports_api_timeout_seconds: float = 10.0
    reports_api_page_limit: int = 200
    reports_api_max_pages: int = 5
    edge_marketing_ingest_url: str = ""

    @property
    def celery_broker(self) -> str:
        """URL del broker de Celery (cae a `redis_url` si no se define)."""
        return self.celery_broker_url or self.redis_url

    @property
    def celery_backend(self) -> str:
        """URL del backend de resultados de Celery (cae a `redis_url`)."""
        return self.celery_result_backend or self.redis_url


@lru_cache
def get_settings() -> Settings:
    """Devuelve la config cacheada del proceso (singleton)."""
    return Settings()
