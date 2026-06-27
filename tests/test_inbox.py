import json

from app.modules.webhook.conversation import inbox


def test_extract_sender_wa_id_from_message(text_webhook_body):
    assert inbox.extract_sender_wa_id(text_webhook_body) == "584140000000"


def test_extract_sender_wa_id_none_for_status():
    payload = json.dumps(
        {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "changes": [
                        {
                            "field": "messages",
                            "value": {"statuses": [{"id": "wamid.X", "status": "delivered"}]},
                        }
                    ]
                }
            ],
        }
    ).encode()
    assert inbox.extract_sender_wa_id(payload) is None


def test_extract_sender_wa_id_none_for_garbage():
    assert inbox.extract_sender_wa_id(b"not json") is None


def test_push_pop_preserve_fifo_order(fake_redis):
    inbox.push_message("c1", "uno")
    inbox.push_message("c1", "dos")

    assert inbox.has_pending("c1") is True
    assert inbox.pop_message("c1") == "uno"
    assert inbox.pop_message("c1") == "dos"
    assert inbox.pop_message("c1") is None
    assert inbox.has_pending("c1") is False
    assert fake_redis.expires["inbox:conv:c1"] == 600


def test_conversation_lock_builds_namespaced_key(fake_redis):
    inbox.conversation_lock("conv:123:456")

    assert fake_redis.locks_created == [("lock:conv:conv:123:456", 600)]
