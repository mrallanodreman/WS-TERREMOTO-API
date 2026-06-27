"""Repositorios de personas: contrato común, hub real (httpx) y stub en memoria.

La lectura del hub de Venezuela Ayuda (`GET /api/v1/reports`) es **abierta**: no
requiere API key. El hub **no** filtra por nombre ni expone cédula; los únicos
filtros server-side son `type` y `city`, así que la coincidencia por nombre se
hace en el cliente paginando por cursor (`since`/`next_cursor`).
"""

import logging
from typing import Protocol

import httpx

from app.core.config import get_settings
from app.modules.webhook.features.personas.enums import PersonStatus, ReportType
from app.modules.webhook.features.personas.mapper import to_person_dto
from app.modules.webhook.features.personas.schemas import PersonDTO

logger = logging.getLogger(__name__)

_REPORTS_PATH = "/api/v1/reports"
_PERSON_TYPES: tuple[ReportType, ...] = (ReportType.MISSING_PERSON, ReportType.CHECKIN)
_STUB_SOURCE = "stub"
_STUB_RECORDS: tuple[dict[str, str], ...] = (
    {"id": "1", "name": "Maria Perez", "status": PersonStatus.SAFE, "city": "Caracas",
     "place_name": "Refugio Norte", "source": _STUB_SOURCE},
    {"id": "2", "name": "Jose Gonzalez", "status": PersonStatus.LOOKING_FOR_SOMEONE,
     "city": "La Guaira", "source": _STUB_SOURCE},
    {"id": "3", "name": "Ana Rodriguez", "status": PersonStatus.NEEDS_HELP,
     "place_name": "Albergue Sur", "source": _STUB_SOURCE},
)


class PersonSearchUnavailable(Exception):
    """La fuente de personas no respondió (timeout, red o error del hub)."""


class PersonRepository(Protocol):
    """Fuente de personas que devuelve DTOs ya normalizados."""

    source: str

    def search(self, query: str) -> list[PersonDTO]:
        """Busca por nombre y devuelve coincidencias normalizadas."""
        ...


class ReportsPersonRepository:
    """Lee del hub de Venezuela Ayuda y filtra por nombre en el cliente."""

    source = "terremoto.hazlohoy.org"

    def __init__(
        self,
        client: httpx.Client | None = None,
        types: tuple[ReportType, ...] = _PERSON_TYPES,
        page_limit: int | None = None,
        max_pages: int | None = None,
    ) -> None:
        """Configura el acceso al hub.

        Args:
            client: Cliente httpx (inyectable en tests); si falta se construye
                uno con la `base_url`/timeout de la config.
            types: Catálogos del hub a recorrer (por defecto desaparecidos +
                checkins, que comparten la proyección pública de persona).
            page_limit: Filas por página; cae a `reports_api_page_limit`.
            max_pages: Tope de páginas por tipo; cae a `reports_api_max_pages`.
        """
        settings = get_settings()
        self._client = client or httpx.Client(
            base_url=settings.reports_api_base_url,
            timeout=settings.reports_api_timeout_seconds,
        )
        self._types = types
        self._page_limit = page_limit or settings.reports_api_page_limit
        self._max_pages = max_pages or settings.reports_api_max_pages

    def search(self, query: str) -> list[PersonDTO]:
        """Recorre cada catálogo de personas y filtra por nombre (substring)."""
        needle = query.strip().lower()
        if not needle:
            return []
        try:
            return [
                dto
                for report_type in self._types
                for dto in self._search_type(report_type, needle)
            ]
        except httpx.HTTPError as exc:
            raise PersonSearchUnavailable(str(exc)) from exc

    def _search_type(self, report_type: ReportType, needle: str) -> list[PersonDTO]:
        """Pagina un catálogo por cursor y se queda con los nombres que coinciden."""
        hits: list[PersonDTO] = []
        cursor: str | None = None
        for _ in range(self._max_pages):
            rows, cursor = self._fetch_page(report_type, cursor)
            for row in rows:
                dto = to_person_dto(row)
                if needle in dto.full_name.lower():
                    hits.append(dto)
            if not cursor:
                break
        else:
            logger.warning(
                "[PERSONAS] búsqueda truncada en %s páginas para type=%s",
                self._max_pages,
                report_type.value,
            )
        return hits

    def _fetch_page(
        self, report_type: ReportType, cursor: str | None
    ) -> tuple[list[dict[str, object]], str | None]:
        """Trae una página del hub y devuelve sus filas y el siguiente cursor."""
        params: dict[str, str | int] = {"type": report_type.value, "limit": self._page_limit}
        if cursor:
            params["since"] = cursor
        response = self._client.get(_REPORTS_PATH, params=params)
        response.raise_for_status()
        body = response.json()
        return body.get("reports", []), body.get("next_cursor")


class StubPersonRepository:
    """Repositorio fake en memoria para tests/offline (misma forma que el hub)."""

    source = _STUB_SOURCE

    def search(self, query: str) -> list[PersonDTO]:
        """Filtra los registros de prueba por nombre (substring)."""
        needle = query.strip().lower()
        if not needle:
            return []
        return [
            to_person_dto(dict(record))
            for record in _STUB_RECORDS
            if needle in record["name"].lower()
        ]
