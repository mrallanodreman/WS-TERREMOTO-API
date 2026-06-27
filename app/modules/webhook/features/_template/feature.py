"""Esqueleto de feature de menú. TODO: renombra la clase y completa la lógica."""

from app.modules.webhook.conversation.contracts import FeatureReply, FeatureTurn
from app.modules.webhook.features._template import messages
from app.modules.webhook.features._template.enums import ItemStep
from app.modules.webhook.features._template.presenter import render_items
from app.modules.webhook.features._template.repository import (
    ItemRepository,
    StubItemRepository,
)


class TemplateFeature:
    """Mini-flujo de ejemplo: pide un término y devuelve resultados.

    Completa los tres atributos de clase: `key` (identificador único y estable
    en snake_case; no lo cambies luego), `label` (texto del menú) y `order`
    (posición en el menú; el desempate es por `key`).
    """

    key = "cambiame"
    label = "TODO: nombre en el menú"
    order = 99

    def __init__(
        self, repositories: tuple[ItemRepository, ...] | None = None
    ) -> None:
        """Inyecta los repositorios; por defecto usa solo el stub."""
        self._repositories = repositories or (StubItemRepository(),)

    def start(self) -> FeatureReply:
        """Primer mensaje al entrar al feature."""
        return FeatureReply(text=messages.PROMPT_QUERY, step=ItemStep.AWAITING_QUERY)

    def handle(self, turn: FeatureTurn) -> FeatureReply:
        """Procesa la respuesta del usuario y devuelve el resultado.

        Para flujos de varios pasos: mira `turn.step`, acumula en `turn.data` y
        devuelve `FeatureReply(step=..., data=...)`. Cuando termines, `done=True`.
        """
        results = [
            dto for repo in self._repositories for dto in repo.search(turn.text)
        ]
        return FeatureReply(text=render_items(results), done=True)
