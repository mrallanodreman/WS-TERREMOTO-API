from app.modules.webhook.conversation.registry import discover_features
from app.modules.webhook.conversation.schemas import ConversationState, conversation_key
from app.modules.webhook.conversation.store import RedisConversationStore


class FakeRedis:
    def __init__(self) -> None:
        self.data: dict[str, str] = {}
        self.last_ex: int | None = None

    def get(self, key: str) -> object:
        return self.data.get(key)

    def set(self, key: str, value: str, ex: int | None = None) -> object:
        self.data[key] = value
        self.last_ex = ex
        return True

    def delete(self, key: str) -> object:
        self.data.pop(key, None)
        return 1


def test_conversation_key_format():
    assert conversation_key("123", "584140000000") == "conv:123:584140000000"


def test_load_missing_returns_empty():
    store = RedisConversationStore(FakeRedis())
    assert store.load("conv:a:b") == ConversationState()


def test_save_load_roundtrip_with_ttl():
    fake = FakeRedis()
    store = RedisConversationStore(fake, ttl_seconds=120)
    store.save("conv:a:b", ConversationState(feature="personas", step="awaiting_query"))
    assert fake.last_ex == 120
    loaded = store.load("conv:a:b")
    assert loaded.feature == "personas"
    assert loaded.step == "awaiting_query"


def test_clear():
    fake = FakeRedis()
    store = RedisConversationStore(fake)
    store.save("conv:a:b", ConversationState(feature="personas"))
    store.clear("conv:a:b")
    assert store.load("conv:a:b") == ConversationState()


def test_discover_features_includes_personas_and_skips_template():
    features = discover_features()
    assert "personas" in features
    assert "cambiame" not in features
