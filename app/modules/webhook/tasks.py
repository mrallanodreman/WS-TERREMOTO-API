"""Tasks de Celery: procesan el webhook fuera del request, en orden por conversación."""

import logging

from app.core.celery_app import celery_app
from app.modules.webhook import outgoing  # noqa: F401  activa el patch de salida (bound)
from app.modules.webhook.client import build_client
from app.modules.webhook.conversation import inbox
from app.modules.webhook.schemas import Tenant

logger = logging.getLogger(__name__)


def _run_pywa(body: str, phone_id: str, token: str) -> None:
    """Construye el cliente del tenant y procesa un update con pywa."""
    client = build_client(Tenant(phone_id=phone_id, token=token))
    client.webhook_update_handler(body.encode("utf-8"))


@celery_app.task(  # type: ignore[untyped-decorator]  # celery: decorador sin tipos
    name="app.modules.webhook.tasks.process_conversation"
)
def process_conversation(conv_key: str, phone_id: str, token: str) -> None:
    """Drena en orden FIFO la bandeja de la conversación, serializando con un lock.

    Si el lock está tomado, otro worker ya está drenando esta conversación y el
    mensaje quedó encolado en la bandeja: este task termina sin hacer nada. Tras
    soltar el lock se re-chequea la bandeja para cerrar la ventana entre el último
    `pop` y el `release` (un mensaje que llegó justo ahí se re-procesa).
    """
    lock = inbox.conversation_lock(conv_key)
    if not lock.acquire(blocking=False):
        return
    try:
        while (body := inbox.pop_message(conv_key)) is not None:
            _run_pywa(body, phone_id, token)
    finally:
        lock.release()
    if inbox.has_pending(conv_key):
        process_conversation.delay(conv_key, phone_id, token)


@celery_app.task(  # type: ignore[untyped-decorator]  # celery: decorador sin tipos
    name="app.modules.webhook.tasks.process_event"
)
def process_event(body: str, phone_id: str, token: str) -> None:
    """Procesa un evento sin estado (status/delivery): sin lock ni orden."""
    _run_pywa(body, phone_id, token)
