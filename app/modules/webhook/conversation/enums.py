"""Comandos globales para volver al menú desde cualquier feature."""

from enum import StrEnum


class GlobalCommand(StrEnum):
    """Texto que el usuario envía para volver al menú principal."""

    MENU = "menu"
    MENU_ACCENT = "menú"
    ZERO = "0"
    EXIT = "salir"
