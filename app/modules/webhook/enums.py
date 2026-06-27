"""Valores cerrados de la API de WhatsApp usados en las salidas."""

from enum import StrEnum


class MessagingProduct(StrEnum):
    """Producto de mensajería de Meta."""

    WHATSAPP = "whatsapp"


class RecipientType(StrEnum):
    """Tipo de destinatario."""

    INDIVIDUAL = "individual"


class MessageType(StrEnum):
    """Tipo de mensaje."""

    TEXT = "text"
