import pytest

from app.modules.webhook.conversation import messages
from app.modules.webhook.conversation.schemas import ConversationState
from app.modules.webhook.conversation.service import ConversationService
from app.modules.webhook.conversation.store import InMemoryConversationStore
from app.modules.webhook.features.personas import messages as personas_messages
from app.modules.webhook.features.personas.feature import PersonasFeature

KEY = "conv:phone:user"


@pytest.fixture
def service():
    feature = PersonasFeature()
    return ConversationService(InMemoryConversationStore(), {feature.key: feature})


def test_first_message_shows_menu(service):
    reply = service.handle_text(KEY, "hola")
    assert "Búsqueda de personas" in reply
    assert messages.MENU_FOOTER in reply


def test_choose_option_enters_feature_and_persists(service):
    reply = service.handle_text(KEY, "1")
    assert reply == personas_messages.PROMPT_QUERY
    state = service._store.load(KEY)
    assert state.feature == "personas"
    assert state.step == "awaiting_query"


def test_answer_query_returns_results_and_clears(service):
    service.handle_text(KEY, "1")
    reply = service.handle_text(KEY, "Maria")
    assert "Maria Perez" in reply
    assert messages.RETURN_HINT in reply
    assert service._store.load(KEY).feature == ""


def test_no_results_message(service):
    service.handle_text(KEY, "1")
    reply = service.handle_text(KEY, "zzzz-no-existe")
    assert personas_messages.NO_RESULTS in reply


@pytest.mark.parametrize("command", ["menu", "menú", "0", "salir", "SALIR"])
def test_global_command_returns_to_menu(service, command):
    service.handle_text(KEY, "1")
    reply = service.handle_text(KEY, command)
    assert "Búsqueda de personas" in reply
    assert service._store.load(KEY).feature == ""


def test_invalid_numeric_option(service):
    reply = service.handle_text(KEY, "99")
    assert messages.INVALID_OPTION in reply
    assert "Búsqueda de personas" in reply


def test_free_text_at_menu_shows_menu_without_scolding(service):
    reply = service.handle_text(KEY, "hola")
    assert messages.INVALID_OPTION not in reply
    assert "Búsqueda de personas" in reply


def test_unknown_active_feature_resets_to_menu(service):
    service._store.save(KEY, ConversationState(feature="borrado", step="x"))
    reply = service.handle_text(KEY, "cualquier cosa")
    assert "Búsqueda de personas" in reply
    assert service._store.load(KEY).feature == ""
