"""Infra de seguridad: firma del forward y descifrado de credenciales."""

import base64
import hashlib
import hmac
import json
import time

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.core.config import get_settings

SHARED_SALT = b"salt_fijo_para_apis_2024_compartido"


def _password_to_key(password: str) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=SHARED_SALT,
        iterations=100000,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))


def is_valid_signature(payload: bytes, signature: str | None) -> bool:
    """Valida la firma `X-Hub-Signature-256` del forward de ws-backend.

    Args:
        payload: Cuerpo crudo de la petición.
        signature: Header `sha256=<hmac>` recibido (o None).

    Returns:
        True si la firma HMAC-SHA256 coincide con el `app_secret` compartido.
    """
    if not signature:
        return False
    expected = hmac.new(
        get_settings().whatsapp_app_secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)


def decrypt_credentials(token: str) -> dict[str, object]:
    """Descifra las credenciales del tenant cifradas por ws-backend.

    Args:
        token: Header `Authorization` cifrado (Fernet, base64).

    Returns:
        Diccionario con las credenciales descifradas (sin `_exp`).

    Raises:
        ValueError: Si el token expiró.
    """
    cipher = Fernet(_password_to_key(get_settings().encryption_secret_key))
    encrypted_bytes = base64.b64decode(token.encode("utf-8"))
    data: dict[str, object] = json.loads(cipher.decrypt(encrypted_bytes).decode("utf-8"))

    expiration = data.pop("_exp", None)
    if isinstance(expiration, (int, float)) and time.time() > expiration:
        raise ValueError("Credenciales expiradas")

    return data
