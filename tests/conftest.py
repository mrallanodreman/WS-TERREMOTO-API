import base64
import hashlib
import hmac
import json
import os

import pytest
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.modules.webhook import handlers
from app.modules.webhook.conversation.store import InMemoryConversationStore

os.environ.setdefault("WHATSAPP_APP_SECRET", "secret_test_123")
os.environ.setdefault("ENCRYPTION_SECRET_KEY", "clave_compartida_test")
os.environ.setdefault("WEBHOOK_ADD_MESSAGE_ENDPOINT", "https://ws-backend/api/messages/add")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

APP_SECRET = os.environ["WHATSAPP_APP_SECRET"]
ENC_KEY = os.environ["ENCRYPTION_SECRET_KEY"]
SALT = b"salt_fijo_para_apis_2024_compartido"


def _fernet_key(password: str) -> bytes:
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=SALT, iterations=100000)
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))


@pytest.fixture(autouse=True)
def in_memory_store(monkeypatch):
    store = InMemoryConversationStore()
    monkeypatch.setattr(handlers, "get_conversation_store", lambda: store)
    return store


@pytest.fixture
def encrypt_credentials():
    def _encrypt(credentials: dict) -> str:
        token = Fernet(_fernet_key(ENC_KEY)).encrypt(json.dumps(credentials).encode())
        return base64.b64encode(token).decode()

    return _encrypt


@pytest.fixture
def sign():
    def _sign(body: bytes) -> str:
        return "sha256=" + hmac.new(APP_SECRET.encode(), body, hashlib.sha256).hexdigest()

    return _sign


@pytest.fixture
def text_webhook_body():
    payload = {
        "object": "whatsapp_business_account",
        "entry": [{"id": "WABA", "changes": [{"field": "messages", "value": {
            "messaging_product": "whatsapp",
            "metadata": {"display_phone_number": "1555", "phone_number_id": "123456789012345"},
            "contacts": [{
                "profile": {"name": "Jose"},
                "wa_id": "584140000000",
                "user_id": "584140000000",
            }],
            "messages": [{"from": "584140000000", "id": "wamid.IN", "timestamp": "1700000000",
                          "type": "text", "text": {"body": "hola"}}],
        }}]}],
    }
    return json.dumps(payload).encode()
