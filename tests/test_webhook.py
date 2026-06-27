import time

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.modules.webhook import outgoing

TENANT = {"phone_id": "123456789012345", "token": "EAAG_tenant"}


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def capture_send(monkeypatch):
    captured: dict = {}

    def fake_original(self, sender, to, recipient, recipient_type, typ, msg, *a, **k):  # noqa: PLR0913
        captured["sent"] = {"sender": sender, "to": to or recipient, "typ": typ, "msg": msg}
        return {
            "messaging_product": "whatsapp",
            "contacts": [{"input": to or recipient, "wa_id": to or recipient}],
            "messages": [{"id": "wamid.OUT_ECHO"}],
        }

    class _Resp:
        def raise_for_status(self):
            return None

    def fake_post(url, json, timeout):
        captured["bound"] = {"url": url, "data": json}
        return _Resp()

    monkeypatch.setattr(outgoing, "_original_send_message", fake_original)
    monkeypatch.setattr("app.modules.webhook.outgoing.httpx.post", fake_post)
    return captured


def test_health(client):
    assert client.get("/ms/ws/health").json() == {"status": "healthy"}


def test_echo_and_bound(client, capture_send, encrypt_credentials, sign, text_webhook_body):
    creds = {**TENANT, "_exp": time.time() + 1800}
    headers = {
        "X-Hub-Signature-256": sign(text_webhook_body),
        "Authorization": encrypt_credentials(creds),
    }
    r = client.post("/ms/ws/webhook", content=text_webhook_body, headers=headers)

    assert r.status_code == 200
    assert capture_send["sent"]["sender"] == TENANT["phone_id"]
    assert capture_send["sent"]["to"] == "584140000000"
    assert capture_send["sent"]["msg"]["body"] == "hola"
    assert capture_send["bound"]["data"]["wamid"] == "wamid.OUT_ECHO"
    assert capture_send["bound"]["url"].endswith("/api/messages/add")


def test_invalid_signature(client, encrypt_credentials, text_webhook_body):
    headers = {
        "X-Hub-Signature-256": "sha256=deadbeef",
        "Authorization": encrypt_credentials({**TENANT, "_exp": time.time() + 1800}),
    }
    r = client.post("/ms/ws/webhook", content=text_webhook_body, headers=headers)
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "INVALID_SIGNATURE"
    assert r.json()["error"]["request_id"]


def test_missing_credentials(client, sign, text_webhook_body):
    headers = {"X-Hub-Signature-256": sign(text_webhook_body)}
    r = client.post("/ms/ws/webhook", content=text_webhook_body, headers=headers)
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "MISSING_CREDENTIALS"


def test_invalid_credentials(client, sign, text_webhook_body):
    headers = {"X-Hub-Signature-256": sign(text_webhook_body), "Authorization": "no-es-fernet"}
    r = client.post("/ms/ws/webhook", content=text_webhook_body, headers=headers)
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "INVALID_CREDENTIALS"
