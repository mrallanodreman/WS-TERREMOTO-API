import base64
import hashlib
import hmac
import json
import os
from collections import defaultdict

import pytest
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.modules.webhook import handlers, services
from app.modules.webhook.conversation import inbox
from app.modules.webhook.conversation.store import InMemoryConversationStore

os.environ.setdefault("WHATSAPP_APP_SECRET", "secret_test_123")
os.environ.setdefault("ENCRYPTION_SECRET_KEY", "clave_compartida_test")
os.environ.setdefault("WEBHOOK_ADD_MESSAGE_ENDPOINT", "https://ws-backend/api/messages/add")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

from app.core.celery_app import celery_app  # noqa: E402  tras setear el entorno

celery_app.conf.task_always_eager = True
celery_app.conf.task_eager_propagates = True

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
    monkeypatch.setattr(services, "get_conversation_store", lambda: store)
    return store


class _FakeLock:
    def __init__(self, redis: "_FakeRedis", name: str) -> None:
        self._redis = redis
        self._name = name

    def acquire(self, blocking: bool = True) -> bool:
        if self._redis.held.get(self._name):
            return False
        self._redis.held[self._name] = True
        return True

    def release(self) -> None:
        self._redis.held[self._name] = False


class _FakeRedis:
    """Redis en memoria: solo las operaciones que usa `inbox` (FIFO + lock)."""

    def __init__(self) -> None:
        self.lists: dict = defaultdict(list)
        self.expires: dict = {}
        self.held: dict = {}
        self.locks_created: list = []

    def rpush(self, name: str, value: str) -> None:
        self.lists[name].append(value)

    def expire(self, name: str, ttl: int) -> None:
        self.expires[name] = ttl

    def lpop(self, name: str) -> str | None:
        items = self.lists.get(name, [])
        return items.pop(0) if items else None

    def llen(self, name: str) -> int:
        return len(self.lists.get(name, []))

    def lock(self, name: str, timeout: int | None = None) -> _FakeLock:
        self.locks_created.append((name, timeout))
        return _FakeLock(self, name)


@pytest.fixture(autouse=True)
def fake_redis(monkeypatch):
    fake = _FakeRedis()
    monkeypatch.setattr(inbox, "get_redis", lambda: fake)
    return fake


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
