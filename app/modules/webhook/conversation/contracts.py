"""Contrato que implementa cada feature del menú conversacional."""

from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field


class FeatureTurn(BaseModel):
    """Entrada de un turno: texto del usuario más el estado local del feature."""

    text: str
    step: str = ""
    data: dict[str, str] = Field(default_factory=dict)


class FeatureReply(BaseModel):
    """Salida de un turno: texto a enviar y el próximo paso/datos o fin del flujo."""

    text: str
    step: str = ""
    data: dict[str, str] = Field(default_factory=dict)
    done: bool = False


@runtime_checkable
class Feature(Protocol):
    """Un mini-flujo conversacional conectable al menú principal."""

    key: str
    label: str
    order: int

    def start(self) -> FeatureReply:
        """Devuelve el primer mensaje al entrar al feature."""
        ...

    def handle(self, turn: FeatureTurn) -> FeatureReply:
        """Procesa la respuesta del usuario y devuelve el siguiente mensaje."""
        ...
