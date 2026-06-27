"""Comandos globales y nombres de cola del menú conversacional."""

from enum import StrEnum


class GlobalCommand(StrEnum):
    """Texto que el usuario envía para volver al menú principal."""

    MENU = "menu"
    MENU_ACCENT = "menú"
    ZERO = "0"
    EXIT = "salir"


class Queue(StrEnum):
    """Colas de Celery según el peso del feature (I/O rápido vs CPU pesado)."""

    FAST = "fast"
    HEAVY = "heavy"
