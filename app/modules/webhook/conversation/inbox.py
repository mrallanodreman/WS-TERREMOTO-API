"""Serialización por conversación: bandeja FIFO en Redis + lock + parseo del remitente."""

import json
from typing import Any, cast

from redis.lock import Lock

from app.core.redis import get_redis

_LOCK_PREFIX = "lock:conv"
_INBOX_PREFIX = "inbox:conv"
_TTL_SECONDS = 600


def conversation_lock(key: str) -> Lock:
    """Devuelve el lock Redis de la conversación (se adquiere no bloqueante).

    El `timeout` excede el límite de tiempo del task para que el lock no expire
    mientras una feature larga sigue drenando la bandeja.
    """
    lock = get_redis().lock(f"{_LOCK_PREFIX}:{key}", timeout=_TTL_SECONDS)
    return cast("Lock", lock)


def push_message(key: str, body: str) -> None:
    """Encola el mensaje al final de la bandeja FIFO de la conversación."""
    client = get_redis()
    name = f"{_INBOX_PREFIX}:{key}"
    client.rpush(name, body)
    client.expire(name, _TTL_SECONDS)


def pop_message(key: str) -> str | None:
    """Saca el mensaje más antiguo de la bandeja, o None si está vacía."""
    raw = get_redis().lpop(f"{_INBOX_PREFIX}:{key}")
    return cast("str | None", raw)


def has_pending(key: str) -> bool:
    """Indica si quedan mensajes en la bandeja de la conversación."""
    return bool(get_redis().llen(f"{_INBOX_PREFIX}:{key}"))


def extract_sender_wa_id(body: str | bytes) -> str | None:
    """Extrae el `wa_id` del remitente del payload de Meta, o None si no aplica.

    Devuelve None para eventos sin mensaje de usuario (status/delivery), que no
    tocan el estado conversacional y se procesan sin lock ni orden.
    """
    try:
        payload: Any = json.loads(body)
        message = payload["entry"][0]["changes"][0]["value"]["messages"][0]
        wa_id = message["from"]
    except (KeyError, IndexError, TypeError, ValueError):
        return None
    return str(wa_id) if wa_id else None
