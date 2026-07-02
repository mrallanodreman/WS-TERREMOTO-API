"""Forward Venezuela WhatsApp updates to Edge Marketing unified backend."""

import base64
import json
import logging
import mimetypes
import os
from io import BytesIO

import httpx
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.core.config import get_settings
from app.modules.webhook.conversation import inbox
from app.modules.webhook.schemas import Tenant

logger = logging.getLogger(__name__)

_SHARED_SALT = b"salt_fijo_para_apis_2024_compartido"

MEDIA_TYPES = {"image", "video", "audio", "document", "sticker", "voice"}


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


def _extract_messages(body: bytes) -> list[dict]:
    """Extract WhatsApp messages from webhook body."""
    try:
        data = json.loads(body.decode("utf-8"))
    except Exception:
        return []
    messages = []
    for entry in data.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            messages.extend(value.get("messages", []))
    return messages


def _guess_extension(mime_type: str, media_type: str) -> str:
    """Return a sensible file extension for a MIME type."""
    ext = mimetypes.guess_extension(mime_type or "")
    if ext:
        return ext
    fallback = {
        "image": ".jpg",
        "video": ".mp4",
        "audio": ".mp3",
        "voice": ".ogg",
        "document": ".bin",
        "sticker": ".webp",
    }
    return fallback.get(media_type, ".bin")


def _download_media(url: str, token: str) -> tuple[bytes, str] | None:
    """Download media from WhatsApp lookaside URL using tenant token."""
    try:
        resp = httpx.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
            follow_redirects=True,
        )
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "application/octet-stream")
        return resp.content, content_type
    except Exception:
        logger.exception("Failed to download WhatsApp media from %s", url)
        return None


def _attach_media(body: bytes, token: str) -> list[dict]:
    """Find media in webhook body and return base64 attachments."""
    attachments: list[dict] = []
    for msg in _extract_messages(body):
        msg_type = msg.get("type")
        if msg_type not in MEDIA_TYPES:
            continue
        media_obj = msg.get(msg_type)
        if not isinstance(media_obj, dict):
            continue
        url = media_obj.get("url") or media_obj.get("link")
        media_id = media_obj.get("id")
        mime_type = media_obj.get("mime_type", "application/octet-stream")
        if not url:
            # Try Graph API media endpoint as fallback
            if media_id and token:
                url = f"https://graph.facebook.com/v20.0/{media_id}"
            else:
                continue
        downloaded = _download_media(url, token)
        if not downloaded:
            continue
        data, content_type = downloaded
        ext = _guess_extension(content_type or mime_type, msg_type)
        filename = f"{msg_type}_{media_id or 'unknown'}{ext}"
        attachments.append(
            {
                "type": msg_type,
                "media_id": media_id,
                "filename": filename,
                "mime_type": content_type or mime_type,
                "size": len(data),
                "data": base64.b64encode(data).decode("ascii"),
            }
        )
    return attachments


def forward_to_edge_marketing(body: bytes, tenant: Tenant) -> None:
    """Forward an incoming WhatsApp webhook to Edge Marketing's ingest endpoint.

    The destination URL is controlled by the ``EDGE_MARKETING_INGEST_URL`` env
    var. The payload is encrypted with ``ENCRYPTION_SECRET_KEY`` using the same
    PBKDF2/Fernet scheme used for tenant credentials, so the Edge Marketing
    Superserver can decrypt it.

    Media attachments (image, video, audio, voice, document, sticker) are
    downloaded using the tenant's WhatsApp token and attached as base64 data
    so Edge Marketing can persist them without needing its own token.
    """
    settings = get_settings()
    endpoint = settings.edge_marketing_ingest_url
    secret = settings.encryption_secret_key
    if not endpoint or not secret:
        return

    wa_id = inbox.extract_sender_wa_id(body)
    report = {
        "type": "whatsapp_message",
        "tenant_phone_id": tenant.phone_id,
        "payload": body.decode("utf-8"),
    }
    attachments = _attach_media(body, tenant.token)
    if attachments:
        report["media"] = attachments

    payload = {
        "phone": wa_id,
        "source": "whatsapp",
        "reports": [report],
    }

    try:
        encrypted = _encrypt_payload(payload, secret)
        resp = httpx.post(endpoint, json={"encrypted": encrypted}, timeout=60)
        resp.raise_for_status()
        logger.debug("Forwarded WhatsApp update to Edge Marketing: %s", resp.status_code)
    except Exception:
        logger.exception("Error forwarding WhatsApp update to Edge Marketing")
