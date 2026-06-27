"""Render de los DTOs de persona a texto de WhatsApp."""

from app.modules.webhook.features.personas import messages
from app.modules.webhook.features.personas.enums import PersonStatus
from app.modules.webhook.features.personas.schemas import PersonDTO

_STATUS_LABEL = {
    PersonStatus.SAFE: messages.STATUS_SAFE,
    PersonStatus.MISSING: messages.STATUS_MISSING,
    PersonStatus.UNKNOWN: messages.STATUS_UNKNOWN,
}


def render_people(people: list[PersonDTO]) -> str:
    """Devuelve el texto a enviar con los resultados de la búsqueda."""
    if not people:
        return messages.NO_RESULTS
    blocks = []
    for person in people:
        line = f"*{person.full_name}* — {_STATUS_LABEL[person.status]}"
        if person.location:
            line += f"\n  📍 {person.location}"
        blocks.append(line)
    return f"{messages.RESULTS_HEADER}\n\n" + "\n\n".join(blocks)
