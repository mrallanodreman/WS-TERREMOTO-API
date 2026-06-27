"""Render de los DTOs a texto de WhatsApp. TODO: dale el formato que quieras."""

from app.modules.webhook.features._template import messages
from app.modules.webhook.features._template.schemas import ItemDTO


def render_items(items: list[ItemDTO]) -> str:
    """Devuelve el texto a enviar con los resultados."""
    if not items:
        return messages.NO_RESULTS
    lines = [f"• *{item.title}*" for item in items]
    return f"{messages.RESULTS_HEADER}\n\n" + "\n".join(lines)
