"""Handlers de pywa: delega cada turno en el motor conversacional."""

import logging

from pywa import WhatsApp, types

from app.modules.webhook.conversation.registry import discover_features
from app.modules.webhook.conversation.schemas import conversation_key
from app.modules.webhook.conversation.service import ConversationService
from app.modules.webhook.conversation.store import get_conversation_store
from app.modules.webhook.schemas import Tenant

logger = logging.getLogger(__name__)


def setup_handlers(wa: WhatsApp, tenant: Tenant) -> None:
    """Registra el handler de texto que enruta por el menú o el feature activo."""
    service = ConversationService(get_conversation_store(), discover_features())

    @wa.on_message()  # type: ignore[untyped-decorator]  # pywa: decorador sin tipos
    def on_message(client: WhatsApp, msg: types.Message) -> None:
        logger.info(
            "[WEBHOOK:IN] [%s] phone=%s type=%s",
            msg.id,
            msg.from_user.wa_id,
            msg.type.value,
        )
        if not msg.text:
            return
        key = conversation_key(tenant.phone_id, msg.from_user.wa_id)
        msg.reply_text(service.handle_text(key, msg.text))
