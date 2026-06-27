"""Valores cerrados de tu feature. TODO: ajústalos a tu dominio."""

from enum import StrEnum


class ItemStep(StrEnum):
    """Pasos del mini-flujo. TODO: declara los pasos que necesites."""

    AWAITING_QUERY = "awaiting_query"
