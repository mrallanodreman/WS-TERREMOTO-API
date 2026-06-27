import json

import pytest

from app.modules.webhook import outgoing
from app.modules.webhook.conversation import inbox
from app.modules.webhook.conversation.schemas import conversation_key
from app.modules.webhook.tasks import process_conversation, process_event

TENANT = {"phone_id": "123456789012345", "token": "EAAG_tenant"}
WA_ID = "584140000000"
CONV_KEY = conversation_key(TENANT["phone_id"], WA_ID)


def _text_body(text: str) -> str:
    payload = {
        "object": "whatsapp_business_account",
        "entry": [{"id": "WABA", "changes": [{"field": "messages", "value": {
            "messaging_product": "whatsapp",
            "metadata": {"display_phone_number": "1555", "phone_number_id": TENANT["phone_id"]},
            "contacts": [{"profile": {"name": "Jose"}, "wa_id": WA_ID, "user_id": WA_ID}],
            "messages": [{"from": WA_ID, "id": "wamid.IN", "timestamp": "1700000000",
                          "type": "text", "text": {"body": text}}],
        }}]}],
    }
    return json.dumps(payload)


@pytest.fixture
def capture_send(monkeypatch):
    captured: dict = {"sent": []}

    def fake_original(self, sender, to, recipient, recipient_type, typ, msg, *a, **k):  # noqa: PLR0913
        captured["sent"].append({"to": to or recipient, "typ": typ, "msg": msg})
        return {
            "messaging_product": "whatsapp",
            "contacts": [{"input": to or recipient, "wa_id": to or recipient}],
            "messages": [{"id": "wamid.OUT"}],
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


def test_process_conversation_drains_and_bounds(capture_send):
    inbox.push_message(CONV_KEY, _text_body("hola"))

    process_conversation.delay(CONV_KEY, TENANT["phone_id"], TENANT["token"])

    assert capture_send["sent"][0]["to"] == WA_ID
    assert "Búsqueda de personas" in capture_send["sent"][0]["msg"]["body"]
    assert capture_send["bound"]["data"]["wamid"] == "wamid.OUT"
    assert inbox.has_pending(CONV_KEY) is False  # bandeja drenada


def test_process_conversation_skips_when_lock_held(capture_send):
    inbox.conversation_lock(CONV_KEY).acquire()  # otro worker la tiene
    inbox.push_message(CONV_KEY, _text_body("hola"))

    process_conversation.delay(CONV_KEY, TENANT["phone_id"], TENANT["token"])

    assert capture_send["sent"] == []  # no procesa; el mensaje queda en la bandeja
    assert inbox.has_pending(CONV_KEY) is True


def test_process_conversation_keeps_fifo_order(capture_send):
    inbox.push_message(CONV_KEY, _text_body("menu"))
    inbox.push_message(CONV_KEY, _text_body("1"))

    process_conversation.delay(CONV_KEY, TENANT["phone_id"], TENANT["token"])

    bodies = [s["msg"]["body"] for s in capture_send["sent"]]
    assert len(bodies) == 2  # ambos procesados por el mismo worker, en orden
    assert "Búsqueda de personas" in bodies[0]  # 1º: respuesta a "menu" (el menú)
    assert bodies[1] != bodies[0]  # 2º: respuesta a "1" (entra al feature)


def test_process_event_runs_without_lock(capture_send):
    process_event.delay(_text_body("hola"), TENANT["phone_id"], TENANT["token"])

    assert capture_send["sent"][0]["to"] == WA_ID
