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


@lru_cache
def get_settings() -> Settings:
    """Devuelve la config cacheada del proceso (singleton)."""
    return Settings()
