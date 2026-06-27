"""Traducción de registros crudos heterogéneos al DTO de dominio."""

from app.modules.webhook.features.personas.enums import PersonStatus
from app.modules.webhook.features.personas.schemas import PersonDTO

_STATUS_BY_RAW = {
    "safe": PersonStatus.SAFE,
    "missing": PersonStatus.MISSING,
}


def to_person_dto(raw: dict[str, str], source: str) -> PersonDTO:
    """Normaliza un registro crudo de una fuente al `PersonDTO` común."""
    return PersonDTO(
        full_name=raw["name"],
        national_id=raw.get("id") or None,
        status=_STATUS_BY_RAW.get(raw.get("state", ""), PersonStatus.UNKNOWN),
        location=raw.get("place") or None,
        source=source,
    )
