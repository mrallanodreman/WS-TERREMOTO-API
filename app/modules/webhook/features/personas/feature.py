"""Feature de menú: búsqueda de personas."""

import logging

from app.modules.webhook.conversation.contracts import FeatureReply, FeatureTurn
from app.modules.webhook.features.personas import messages
from app.modules.webhook.features.personas.enums import PersonStep
from app.modules.webhook.features.personas.presenter import render_people
from app.modules.webhook.features.personas.repository import (
    PersonRepository,
    PersonSearchUnavailable,
    ReportsPersonRepository,
)

logger = logging.getLogger(__name__)


class PersonasFeature:
    """Pide un término y agrega resultados de uno o varios repositorios."""

    key = "personas"
    label = "Búsqueda de personas"
    order = 1

    def __init__(
        self, repositories: tuple[PersonRepository, ...] | None = None
    ) -> None:
        """Inyecta los repositorios; por defecto usa el hub real (lectura abierta)."""
        self._repositories = repositories or (ReportsPersonRepository(),)

    def start(self) -> FeatureReply:
        """Solicita el nombre a buscar."""
        return FeatureReply(text=messages.PROMPT_QUERY, step=PersonStep.AWAITING_QUERY)

    def handle(self, turn: FeatureTurn) -> FeatureReply:
        """Busca en todos los repositorios, normaliza y devuelve el resultado."""
        try:
            results = [
                dto for repo in self._repositories for dto in repo.search(turn.text)
            ]
        except PersonSearchUnavailable:
            logger.exception("[PERSONAS] fuente de personas no disponible")
            return FeatureReply(text=messages.SERVICE_UNAVAILABLE, done=True)
        return FeatureReply(text=render_people(results), done=True)
