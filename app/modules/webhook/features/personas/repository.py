"""Repositorios de personas: contrato común más implementación stub en memoria."""

from typing import Protocol

from app.modules.webhook.features.personas.mapper import to_person_dto
from app.modules.webhook.features.personas.schemas import PersonDTO

_STUB_SOURCE = "stub"
_STUB_RECORDS: tuple[dict[str, str], ...] = (
    {"name": "Maria Perez", "id": "V12345678", "state": "safe", "place": "Refugio Norte"},
    {"name": "Jose Gonzalez", "id": "V87654321", "state": "missing", "place": ""},
    {"name": "Ana Rodriguez", "id": "V11223344", "state": "safe", "place": "Albergue Sur"},
)


class PersonRepository(Protocol):
    """Fuente de personas que devuelve DTOs ya normalizados."""

    source: str

    def search(self, query: str) -> list[PersonDTO]:
        """Busca por nombre o cédula y devuelve coincidencias normalizadas."""
        ...


class StubPersonRepository:
    """Repositorio fake en memoria mientras no exista la API real."""

    source = _STUB_SOURCE

    def search(self, query: str) -> list[PersonDTO]:
        """Filtra los registros de prueba por nombre (substring) o cédula exacta."""
        needle = query.strip().lower()
        if not needle:
            return []
        hits = [
            record
            for record in _STUB_RECORDS
            if needle in record["name"].lower() or needle == record["id"].lower()
        ]
        return [to_person_dto(record, self.source) for record in hits]
