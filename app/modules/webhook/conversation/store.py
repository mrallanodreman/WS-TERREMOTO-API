"""Persistencia del estado de conversación: contrato + Redis + memoria."""

from functools import lru_cache
from typing import Protocol, cast

from app.core.redis import get_redis
from app.modules.webhook.conversation.schemas import ConversationState

_TTL_SECONDS = 60 * 30


class RedisClient(Protocol):
    """Subconjunto de Redis usado por el store (desacopla del cliente real)."""

    def get(self, key: str) -> object:
        """Devuelve el valor crudo de la clave o None."""
        ...

    def set(self, key: str, value: str, ex: int | None = None) -> object:
        """Guarda el valor con expiración opcional en segundos."""
        ...

    def delete(self, key: str) -> object:
        """Elimina la clave."""
        ...


class ConversationStore(Protocol):
    """Almacena el estado de conversación por clave (tenant, usuario)."""

    def load(self, key: str) -> ConversationState:
        """Devuelve el estado guardado o uno vacío si no existe."""
        ...

    def save(self, key: str, state: ConversationState) -> None:
        """Guarda el estado con TTL."""
        ...

    def clear(self, key: str) -> None:
        """Elimina el estado (vuelta al menú)."""
        ...


class RedisConversationStore:
    """Implementación sobre Redis con TTL deslizante."""

    def __init__(
        self, client: RedisClient, ttl_seconds: int = _TTL_SECONDS
    ) -> None:
        """Inyecta el cliente Redis y el TTL del estado."""
        self._client = client
        self._ttl = ttl_seconds

    def load(self, key: str) -> ConversationState:
        """Carga y deserializa el estado, o devuelve uno vacío."""
        raw = self._client.get(key)
        if raw is None:
            return ConversationState()
        return ConversationState.model_validate_json(cast("str", raw))

    def save(self, key: str, state: ConversationState) -> None:
        """Serializa y persiste el estado renovando el TTL."""
        self._client.set(key, state.model_dump_json(), ex=self._ttl)

    def clear(self, key: str) -> None:
        """Borra el estado de Redis."""
        self._client.delete(key)


class InMemoryConversationStore:
    """Store en memoria para dev local y tests (sin Redis)."""

    def __init__(self) -> None:
        """Inicializa el diccionario interno."""
        self._data: dict[str, ConversationState] = {}

    def load(self, key: str) -> ConversationState:
        """Devuelve el estado en memoria o uno vacío."""
        return self._data.get(key, ConversationState())

    def save(self, key: str, state: ConversationState) -> None:
        """Guarda el estado en memoria."""
        self._data[key] = state

    def clear(self, key: str) -> None:
        """Elimina el estado en memoria."""
        self._data.pop(key, None)


@lru_cache
def get_conversation_store() -> ConversationStore:
    """Provee el store Redis cacheado (monkeypatcheable en tests)."""
    return RedisConversationStore(get_redis())
