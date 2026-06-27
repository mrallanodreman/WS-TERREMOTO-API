"""Patch de pywa: reenvía (bound) cada mensaje de salida a ws-backend."""

import logging
from typing import Any, cast

import httpx
from pywa.api import GraphAPI

from app.core.config import get_settings
from app.modules.webhook.enums import MessagingProduct, RecipientType

logger = logging.getLogger(__name__)

_original_send_message = GraphAPI.send_message


def _bound_to_ws_backend(
    sender: str, to: str | None, typ: str, msg: dict[str, Any], response: dict[str, Any]
) -> None:
    endpoint = get_settings().webhook_add_message_endpoint
    if not endpoint:
        return

    wamid = response.get("messages", [{}])[0].get("id")
    data = {
        "messaging_product": MessagingProduct.WHATSAPP.value,
        "recipient_type": RecipientType.INDIVIDUAL.value,
        "to": to,
        "type": typ,
        typ: msg,
        "sender": sender,
        "wamid": wamid,
    }

    try:
        webhook_response = httpx.post(endpoint, json=data, timeout=15)
        webhook_response.raise_for_status()
    except httpx.HTTPStatusError as e:
        logger.error(
            "Error bound ws-backend: status=%s response=%s",
            e.response.status_code,
            e.response.text,
        )
    except Exception as e:
        logger.error("Error bound ws-backend: %s", str(e))


def _patched_send_message(  # noqa: PLR0913  firma impuesta por pywa GraphAPI.send_message
    self: GraphAPI,
    sender: str,
    to: str | None,
    recipient: str | None,
    recipient_type: str,
    typ: str,
    msg: dict[str, Any],
    *args: Any,
    **kwargs: Any,
) -> dict[str, Any]:
    response = cast(
        "dict[str, Any]",
        _original_send_message(
            self, sender, to, recipient, recipient_type, typ, msg, *args, **kwargs
        ),
    )
    _bound_to_ws_backend(sender, to or recipient, typ, msg, response)
    return response


GraphAPI.send_message = _patched_send_message
