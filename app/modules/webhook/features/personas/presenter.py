"""Render de los DTOs de persona a texto de WhatsApp.

WhatsApp rechaza (`code=100`) cualquier `text.body` de más de 4096 caracteres,
así que el resultado se acota: tope de coincidencias, preview corto del mensaje
y un presupuesto de caracteres con aviso de "…y N más".
"""

from app.modules.webhook.features.personas import messages
from app.modules.webhook.features.personas.enums import PersonStatus
from app.modules.webhook.features.personas.schemas import PersonDTO

_STATUS_LABEL = {
    PersonStatus.SAFE: messages.STATUS_SAFE,
    PersonStatus.NEEDS_HELP: messages.STATUS_NEEDS_HELP,
    PersonStatus.LOOKING_FOR_SOMEONE: messages.STATUS_LOOKING_FOR_SOMEONE,
    PersonStatus.UNKNOWN: messages.STATUS_UNKNOWN,
}

_MAX_RESULTS = 10
_MESSAGE_PREVIEW = 140
_BLOCK_SEPARATOR = "\n\n"
# Margen bajo el límite duro de WhatsApp (4096) para header y aviso de "…y N más".
_TEXT_BUDGET = 3800


def _render_person(person: PersonDTO) -> str:
    """Arma el bloque de texto de una persona (con el mensaje recortado)."""
    line = f"*{person.full_name}* — {_STATUS_LABEL[person.status]}"
    if person.location:
        line += f"\n  📍 {person.location}"
    if person.message:
        preview = person.message
        if len(preview) > _MESSAGE_PREVIEW:
            preview = preview[:_MESSAGE_PREVIEW].rstrip() + "…"
        line += f"\n  📝 {preview}"
    if person.source:
        attribution = f"\n  🔗 {messages.SOURCE_PREFIX}: {person.source}"
        if person.source_url:
            attribution += f" ({person.source_url})"
        line += attribution
    return line


def render_people(people: list[PersonDTO]) -> str:
    """Devuelve el texto a enviar, acotado al límite de WhatsApp.

    Muestra hasta `_MAX_RESULTS` personas sin pasar el presupuesto de caracteres;
    si quedan más fuera, agrega un aviso para que el usuario afine la búsqueda.
    """
    if not people:
        return messages.NO_RESULTS
    blocks: list[str] = []
    used = len(messages.RESULTS_HEADER)
    for person in people[:_MAX_RESULTS]:
        block = _render_person(person)
        if used + len(block) + len(_BLOCK_SEPARATOR) > _TEXT_BUDGET:
            break
        blocks.append(block)
        used += len(block) + len(_BLOCK_SEPARATOR)
    text = messages.RESULTS_HEADER + _BLOCK_SEPARATOR + _BLOCK_SEPARATOR.join(blocks)
    omitted = len(people) - len(blocks)
    if omitted > 0:
        text += _BLOCK_SEPARATOR + messages.MORE_RESULTS.format(count=omitted)
    return text
