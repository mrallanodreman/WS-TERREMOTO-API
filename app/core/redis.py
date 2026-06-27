"""Cliente Redis compartido (infra; sin tipos de dominio)."""

from functools import lru_cache

import redis

from app.core.config import get_settings


@lru_cache
def get_redis() -> redis.Redis:
    """Devuelve el cliente Redis cacheado del proceso (decodifica a str)."""
    return redis.Redis.from_url(get_settings().redis_url, decode_responses=True)
