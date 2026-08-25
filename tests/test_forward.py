import json

from app.modules.webhook import forward


def test_attach_media_resolves_graph_url_before_download(monkeypatch):
    body = json.dumps(
        {
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "messages": [
                                    {"type": "image", "image": {"id": "media-123"}}
                                ]
                            }
                        }
                    ]
                }
            ]
        }
    ).encode()
    monkeypatch.setattr(
        forward,
        "_resolve_media",
        lambda media_id, token: (
            "https://lookaside.fbsbx.com/media",
            "image/jpeg",
        ),
    )
    monkeypatch.setattr(
        forward,
        "_download_media",
        lambda url, token: (b"jpeg-bytes", "image/jpeg"),
    )

    attachments = forward._attach_media(body, "tenant-token")

    assert len(attachments) == 1
    assert attachments[0]["media_id"] == "media-123"
    assert attachments[0]["mime_type"] == "image/jpeg"
    assert attachments[0]["size"] == len(b"jpeg-bytes")


def test_attach_media_skips_message_without_media_id(monkeypatch):
    body = json.dumps(
        {
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "messages": [
                                    {
                                        "type": "image",
                                        "image": {"link": "https://attacker.example/file"},
                                    }
                                ]
                            }
                        }
                    ]
                }
            ]
        }
    ).encode()
    monkeypatch.setattr(
        forward,
        "_download_media",
        lambda *_: (_ for _ in ()).throw(AssertionError("must not download")),
    )

    assert forward._attach_media(body, "tenant-token") == []
