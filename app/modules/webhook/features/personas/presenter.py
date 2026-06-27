"""Render de los DTOs de persona a texto de WhatsApp."""

from app.modules.webhook.features.personas import messages
from app.modules.webhook.features.personas.enums import PersonStatus
from app.modules.webhook.features.personas.schemas import PersonDTO

_STATUS_LABEL = {
    PersonStatus.SAFE: messages.STATUS_SAFE,
    PersonStatus.NEEDS_HELP: messages.STATUS_NEEDS_HELP,
    PersonStatus.LOOKING_FOR_SOMEONE: messages.STATUS_LOOKING_FOR_SOMEONE,
    PersonStatus.UNKNOWN: messages.STATUS_UNKNOWN,
}


def _render_person(person: PersonDTO) -> str:
    """Arma el bloque de texto de una persona."""
    line = f"*{person.full_name}* — {_STATUS_LABEL[person.status]}"
    if person.location:
        line += f"\n  📍 {person.location}"
    if person.message:
        line += f"\n  📝 {person.message}"
    if person.source:
        attribution = f"\n  🔗 {messages.SOURCE_PREFIX}: {person.source}"
        if person.source_url:
            attribution += f" ({person.source_url})"
        line += attribution
    return line


def render_people(people: list[PersonDTO]) -> str:
    """Devuelve el texto a enviar con los resultados de la búsqueda."""
    if not people:
        return messages.NO_RESULTS
    blocks = [_render_person(person) for person in people]
    return f"{messages.RESULTS_HEADER}\n\n" + "\n\n".join(blocks)
