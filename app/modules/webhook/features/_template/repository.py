"""Repositorios de tu feature: contrato común más un stub en memoria.

TODO: reemplaza el stub por tu conexión real (API REST, base de datos, etc.).
Cada repositorio recibe la consulta cruda del usuario y devuelve DTOs ya
normalizados (usando su propio `mapper`). El feature solo concatena DTOs.
"""

from typing import Protocol

from app.modules.webhook.features._template.mapper import to_item_dto
from app.modules.webhook.features._template.schemas import ItemDTO

_STUB_SOURCE = "stub"
_STUB_RECORDS: tuple[dict[str, str], ...] = (
    {"title": "Ejemplo 1", "detail": "Reemplázame"},
    {"title": "Ejemplo 2", "detail": ""},
)


class ItemRepository(Protocol):
    """Fuente de datos que devuelve DTOs ya normalizados."""

    source: str

    def search(self, query: str) -> list[ItemDTO]:
        """Busca según la consulta del usuario y devuelve coincidencias."""
        ...


class StubItemRepository:
    """Repositorio fake en memoria. TODO: bórralo cuando conectes la fuente real."""

    source = _STUB_SOURCE

    def search(self, query: str) -> list[ItemDTO]:
        """Devuelve registros de ejemplo que contengan la consulta en el título."""
        needle = query.strip().lower()
        if not needle:
            return []
        hits = [r for r in _STUB_RECORDS if needle in r["title"].lower()]
        return [to_item_dto(record, self.source) for record in hits]
