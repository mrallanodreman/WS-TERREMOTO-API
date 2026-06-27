"""Motor conversacional: enruta cada turno entre el menú y los features."""

from app.modules.webhook.conversation import messages
from app.modules.webhook.conversation.contracts import Feature, FeatureTurn
from app.modules.webhook.conversation.enums import GlobalCommand
from app.modules.webhook.conversation.schemas import ConversationState
from app.modules.webhook.conversation.store import ConversationStore

_GLOBAL_COMMANDS = frozenset(c.value for c in GlobalCommand)
_MENU_START = 1


class ConversationService:
    """Carga estado, decide menú vs. feature, despacha y persiste el resultado."""

    def __init__(self, store: ConversationStore, features: dict[str, Feature]) -> None:
        """Inyecta el store de estado y el catálogo de features descubiertos."""
        self._store = store
        self._features = features

    def handle_text(self, key: str, raw_text: str) -> str:
        """Procesa un mensaje de texto y devuelve la respuesta para el usuario."""
        text = raw_text.strip()
        if text.lower() in _GLOBAL_COMMANDS:
            self._store.clear(key)
            return self._menu_text()
        state = self._store.load(key)
        if not state.feature:
            return self._enter_feature(key, text)
        return self._advance_feature(key, state, text)

    def _ordered(self) -> list[Feature]:
        return sorted(self._features.values(), key=lambda f: (f.order, f.key))

    def _menu_text(self) -> str:
        lines = [messages.MENU_HEADER, ""]
        lines += [f"{i}) {f.label}" for i, f in enumerate(self._ordered(), _MENU_START)]
        lines += ["", messages.MENU_FOOTER]
        return "\n".join(lines)

    def _feature_by_choice(self, text: str) -> Feature | None:
        if not text.isdigit():
            return None
        ordered = self._ordered()
        index = int(text) - _MENU_START
        return ordered[index] if 0 <= index < len(ordered) else None

    def _enter_feature(self, key: str, text: str) -> str:
        feature = self._feature_by_choice(text)
        if feature is None:
            if text.isdigit():
                return f"{messages.INVALID_OPTION}\n\n{self._menu_text()}"
            return self._menu_text()
        reply = feature.start()
        self._store.save(
            key,
            ConversationState(feature=feature.key, step=reply.step, data=reply.data),
        )
        return reply.text

    def _advance_feature(self, key: str, state: ConversationState, text: str) -> str:
        feature = self._features.get(state.feature)
        if feature is None:
            self._store.clear(key)
            return self._menu_text()
        reply = feature.handle(FeatureTurn(text=text, step=state.step, data=state.data))
        if reply.done:
            self._store.clear(key)
            return f"{reply.text}\n\n{messages.RETURN_HINT}"
        self._store.save(
            key,
            ConversationState(feature=state.feature, step=reply.step, data=reply.data),
        )
        return reply.text
