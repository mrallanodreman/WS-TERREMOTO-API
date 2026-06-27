"""Handlers de pywa: echo del mensaje entrante."""

import logging

from pywa import WhatsApp, types

logger = logging.getLogger(__name__)


def setup_echo(wa: WhatsApp) -> None:
    """Registra el handler de echo: responde el mismo texto recibido."""

    @wa.on_message()  # type: ignore[untyped-decorator]  # pywa: decorador sin tipos
    def echo(client: WhatsApp, msg: types.Message) -> None:
        logger.info(
            "[WEBHOOK:IN] [%s] phone=%s type=%s",
            msg.id,
            msg.from_user.wa_id,
            msg.type.value,
        )
        if not msg.text:
            return
        msg.reply_text(msg.text)
