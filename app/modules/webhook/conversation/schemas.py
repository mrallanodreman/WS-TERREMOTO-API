"""Estado de conversación persistido por (tenant, usuario)."""

from pydantic import BaseModel, Field

_KEY_PREFIX = "conv"


class ConversationState(BaseModel):
    """Posición del usuario en el árbol: feature activo, paso y datos parciales."""

    feature: str = ""
    step: str = ""
    data: dict[str, str] = Field(default_factory=dict)


def conversation_key(phone_id: str, wa_id: str) -> str:
    """Construye la clave Redis del estado para (tenant phone_id, usuario wa_id)."""
    return f"{_KEY_PREFIX}:{phone_id}:{wa_id}"
