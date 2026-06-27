"""Valores cerrados del feature de búsqueda de personas."""

from enum import StrEnum


class ReportType(StrEnum):
    """Catálogo del hub con datos de personas (proyección pública `CheckinPublic`)."""

    MISSING_PERSON = "missing_person"
    CHECKIN = "checkin"


class PersonStatus(StrEnum):
    """Estado de la persona; los valores coinciden con los del hub (`status`)."""

    SAFE = "SAFE"
    NEEDS_HELP = "NEEDS_HELP"
    LOOKING_FOR_SOMEONE = "LOOKING_FOR_SOMEONE"
    UNKNOWN = "unknown"


class PersonStep(StrEnum):
    """Pasos del mini-flujo de búsqueda de personas."""

    AWAITING_QUERY = "awaiting_query"
