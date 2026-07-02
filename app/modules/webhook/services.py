"""Lógica de dominio del webhook (no sabe de HTTP)."""

from app.core.security import decrypt_credentials, is_valid_signature
from app.modules.webhook.conversation import inbox
from app.modules.webhook.forward import forward_to_edge_marketing
from app.modules.webhook.conversation.enums import Queue
from app.modules.webhook.conversation.registry import discover_features
from app.modules.webhook.conversation.schemas import conversation_key
from app.modules.webhook.conversation.store import get_conversation_store
from app.modules.webhook.exceptions import (
    InvalidCredentialsError,
    InvalidSignatureError,
    MissingCredentialsError,
)
from app.modules.webhook.schemas import Tenant
from app.modules.webhook.tasks import process_conversation, process_event


class WebhookService:
    """Lógica de dominio del webhook: firma, tenant y procesamiento del update."""

    def verify_signature(self, body: bytes, signature: str | None) -> None:
        """Valida la firma del forward o levanta `InvalidSignatureError`."""
        if not is_valid_signature(body, signature):
            raise InvalidSignatureError

    def resolve_tenant(self, authorization: str | None) -> Tenant:
        """Descifra el header `Authorization` y construye el `Tenant`.

        Args:
            authorization: Header cifrado con las credenciales del tenant.

        Returns:
            El tenant resuelto.

        Raises:
            MissingCredentialsError: Si no llegó el header.
            InvalidCredentialsError: Si no se puede descifrar o falta un campo.
        """
        if not authorization:
            raise MissingCredentialsError
        try:
            credentials = decrypt_credentials(authorization)
            return Tenant(
                phone_id=str(credentials["phone_id"]),
                token=str(credentials["token"]),
            )
        except Exception as exc:
            raise InvalidCredentialsError from exc

    def enqueue(
        self, body: bytes, signature: str | None, authorization: str | None
    ) -> None:
        """Verifica firma y tenant (síncrono) y encola el procesamiento en Celery.

        Lo rápido (firma + descifrado) ocurre en el request para devolver 401/403
        reales; lo pesado (pywa + reply + bound) corre en el worker. El body es JSON
        utf-8 y se pasa como str porque el serializador JSON de Celery no admite bytes.

        Un mensaje de usuario se **encola en la bandeja FIFO** de su conversación (en
        orden de llegada) y dispara el drenado serializado; un evento sin mensaje
        (status/delivery) se procesa directo, sin lock ni orden.
        """
        self.verify_signature(body, signature)
        tenant = self.resolve_tenant(authorization)
        payload = body.decode("utf-8")
        wa_id = inbox.extract_sender_wa_id(body)
        if wa_id is None:
            process_event.apply_async(
                args=[payload, tenant.phone_id, tenant.token], queue=Queue.FAST
            )
            forward_to_edge_marketing(body, tenant)
            return
        conv_key = conversation_key(tenant.phone_id, wa_id)
        inbox.push_message(conv_key, payload)
        process_conversation.apply_async(
            args=[conv_key, tenant.phone_id, tenant.token],
            queue=self._queue_for(conv_key),
        )
        forward_to_edge_marketing(body, tenant)

    def _queue_for(self, conv_key: str) -> str:
        """Elige la cola según el peso del feature activo en la conversación.

        Lee el estado (Redis GET, ~1ms): si el usuario está dentro de un feature que
        declara `queue = Queue.HEAVY`, su procesamiento va a la cola pesada; si está
        en el menú o el feature no declara cola, va a la rápida.
        """
        state = get_conversation_store().load(conv_key)
        if not state.feature:
            return Queue.FAST
        feature = discover_features().get(state.feature)
        return str(getattr(feature, "queue", Queue.FAST)) if feature else Queue.FAST
