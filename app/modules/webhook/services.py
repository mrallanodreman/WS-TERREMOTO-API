"""Lógica de dominio del webhook (no sabe de HTTP)."""

from typing import cast

from app.core.security import decrypt_credentials, is_valid_signature
from app.modules.webhook.client import build_client
from app.modules.webhook.exceptions import (
    InvalidCredentialsError,
    InvalidSignatureError,
    MissingCredentialsError,
)
from app.modules.webhook.schemas import Tenant


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

    def process(
        self, body: bytes, signature: str | None, authorization: str | None
    ) -> tuple[str, int]:
        """Verifica, resuelve el tenant y procesa el update con pywa.

        Returns:
            (cuerpo de respuesta, status) que devuelve `webhook_update_handler`.
        """
        self.verify_signature(body, signature)
        tenant = self.resolve_tenant(authorization)
        client = build_client(tenant)
        return cast("tuple[str, int]", client.webhook_update_handler(body))
