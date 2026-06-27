"""Traducción de la proyección pública del hub al DTO de dominio."""

from typing import Any

from app.modules.webhook.features.personas.enums import PersonStatus
from app.modules.webhook.features.personas.schemas import PersonDTO

_STATUS_BY_RAW = {
    PersonStatus.SAFE.value: PersonStatus.SAFE,
    PersonStatus.NEEDS_HELP.value: PersonStatus.NEEDS_HELP,
    PersonStatus.LOOKING_FOR_SOMEONE.value: PersonStatus.LOOKING_FOR_SOMEONE,
}


def to_person_dto(raw: dict[str, Any]) -> PersonDTO:
    """Normaliza una fila `CheckinPublic` del hub al `PersonDTO` común.

    Args:
        raw: Fila pública del hub (sin PII) tal como la devuelve la lectura.

    Returns:
        El `PersonDTO` con la ubicación más específica disponible
        (`place_name`, si no `city`) y el estado mapeado al enum cerrado.
    """
    status_raw = str(raw.get("status") or "")
    return PersonDTO(
        report_id=raw.get("id"),
        full_name=str(raw.get("name") or "").strip(),
        status=_STATUS_BY_RAW.get(status_raw, PersonStatus.UNKNOWN),
        location=(raw.get("place_name") or raw.get("city")) or None,
        message=raw.get("message") or None,
        source=raw.get("source") or None,
        source_url=raw.get("source_url") or None,
    )
