"""Valores cerrados del feature de búsqueda de personas."""

from enum import StrEnum


class PersonStatus(StrEnum):
    """Estado de la persona en el contexto del terremoto."""

    SAFE = "safe"
    MISSING = "missing"
    UNKNOWN = "unknown"


class PersonStep(StrEnum):
    """Pasos del mini-flujo de búsqueda de personas."""

    AWAITING_QUERY = "awaiting_query"
