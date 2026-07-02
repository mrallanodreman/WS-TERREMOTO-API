"""Forward Venezuela WhatsApp updates to Edge Marketing unified backend."""

import base64
import json
import logging

import httpx
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.core.config import get_settings
from app.modules.webhook.conversation import inbox
from app.modules.webhook.schemas import Tenant

logger = logging.getLogger(__name__)

_SHARED_SALT = b"salt_fijo_para_apis_2024_compartido"


def _derive_key(password: str) -> bytes:
    """Derive a Fernet key from a password using the shared repo PBKDF2 scheme."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=_SHARED_SALT,
        iterations=100000,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))


def _encrypt_payload(payload: dict, secret: str) -> str:
    """Encrypt a payload using PBKDF2-derived Fernet and return base64 token."""
    token = Fernet(_derive_key(secret)).encrypt(json.dumps(payload).encode("utf-8"))
    return base64.b64encode(token).decode("utf-8")


def forward_to_edge_marketing(body: bytes, tenant: Tenant) -> None:
    """Forward an incoming WhatsApp webhook to Edge Marketing's ingest endpoint.

    The destination URL is controlled by the ``EDGE_MARKETING_INGEST_URL`` env
    var. The payload is encrypted with ``ENCRYPTION_SECRET_KEY`` using the same
    PBKDF2/Fernet scheme used for tenant credentials, so the Edge Marketing
    Superserver can decrypt it.
    """
    settings = get_settings()
    endpoint = settings.edge_marketing_ingest_url
    secret = settings.encryption_secret_key
    if not endpoint or not secret:
        return

    wa_id = inbox.extract_sender_wa_id(body)
    payload = {
        "phone": wa_id,
        "source": "whatsapp",
        "reports": [
            {
                "type": "whatsapp_message",
                "tenant_phone_id": tenant.phone_id,
                "payload": body.decode("utf-8"),
            }
        ],
    }

    try:
        encrypted = _encrypt_payload(payload, secret)
        resp = httpx.post(endpoint, json={"encrypted": encrypted}, timeout=15)
        resp.raise_for_status()
        logger.debug("Forwarded WhatsApp update to Edge Marketing: %s", resp.status_code)
    except Exception:
        logger.exception("Error forwarding WhatsApp update to Edge Marketing")
