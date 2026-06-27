"""Traduce el registro crudo de tu fuente al DTO de dominio.

TODO: cada fuente (API/DB) tiene su propio formato; aquí lo normalizas al DTO.
"""

from app.modules.webhook.features._template.schemas import ItemDTO


def to_item_dto(raw: dict[str, str], source: str) -> ItemDTO:
    """Normaliza un registro crudo de una fuente al `ItemDTO` común."""
    return ItemDTO(
        title=raw["title"],
        detail=raw.get("detail") or None,
        source=source,
    )
