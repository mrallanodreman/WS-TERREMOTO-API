import time

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.modules.webhook import services as svc
from app.modules.webhook.conversation import inbox
from app.modules.webhook.conversation.schemas import ConversationState, conversation_key
from app.modules.webhook.services import WebhookService
from app.modules.webhook.tasks import process_conversation, process_event

TENANT = {"phone_id": "123456789012345", "token": "EAAG_tenant"}
WA_ID = "584140000000"


@pytest.fixture
def client():
    return TestClient(app)


def test_endpoint_pushes_to_inbox_and_enqueues_drain(
    client, monkeypatch, encrypt_credentials, sign, text_webhook_body
):
    captured: dict = {}
    monkeypatch.setattr(
        process_conversation,
        "apply_async",
        lambda args, queue: captured.update(args=args, queue=queue),
    )
    headers = {
        "X-Hub-Signature-256": sign(text_webhook_body),
        "Authorization": encrypt_credentials({**TENANT, "_exp": time.time() + 1800}),
    }
    r = client.post("/ms/ws/webhook", content=text_webhook_body, headers=headers)

    conv_key = conversation_key(TENANT["phone_id"], WA_ID)
    assert r.status_code == 200
    assert r.text == "ok"
    assert captured["args"] == [conv_key, TENANT["phone_id"], TENANT["token"]]
    assert captured["queue"] == "fast"  # sin feature activo → cola rápida
    assert inbox.has_pending(conv_key) is True  # quedó en la bandeja


def test_invalid_signature_does_not_enqueue(
    client, monkeypatch, encrypt_credentials, text_webhook_body
):
    called = []
    monkeypatch.setattr(process_conversation, "apply_async", lambda *a, **k: called.append(a))
    monkeypatch.setattr(process_event, "apply_async", lambda *a, **k: called.append(a))
    headers = {
        "X-Hub-Signature-256": "sha256=deadbeef",
        "Authorization": encrypt_credentials({**TENANT, "_exp": time.time() + 1800}),
    }
    r = client.post("/ms/ws/webhook", content=text_webhook_body, headers=headers)

    assert r.status_code == 403
    assert called == []


def test_missing_credentials_does_not_enqueue(
    client, monkeypatch, sign, text_webhook_body
):
    called = []
    monkeypatch.setattr(process_conversation, "apply_async", lambda *a, **k: called.append(a))
    monkeypatch.setattr(process_event, "apply_async", lambda *a, **k: called.append(a))
    headers = {"X-Hub-Signature-256": sign(text_webhook_body)}
    r = client.post("/ms/ws/webhook", content=text_webhook_body, headers=headers)

    assert r.status_code == 401
    assert called == []


def test_queue_for_menu_is_fast(in_memory_store):
    conv_key = conversation_key(TENANT["phone_id"], WA_ID)
    assert WebhookService()._queue_for(conv_key) == "fast"


def test_queue_for_heavy_feature(monkeypatch, in_memory_store):
    conv_key = conversation_key(TENANT["phone_id"], WA_ID)
    in_memory_store.save(conv_key, ConversationState(feature="bigjob"))

    class _Heavy:
        queue = "heavy"

    monkeypatch.setattr(svc, "discover_features", lambda: {"bigjob": _Heavy()})

    assert WebhookService()._queue_for(conv_key) == "heavy"
