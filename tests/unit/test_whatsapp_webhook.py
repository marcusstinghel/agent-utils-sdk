"""Unit tests for the WhatsApp webhook models (fictional data only)."""

from agent_utils_sdk.whatsapp.webhook import WebhookPayload

PHONE_ID = "100000000000001"


def _payload(value):
    return {
        "object": "whatsapp_business_account",
        "entry": [{"id": "100000000000009", "changes": [{"field": "messages", "value": value}]}],
    }


def test_text_message():
    value = {
        "messaging_product": "whatsapp",
        "metadata": {"display_phone_number": "15550000000", "phone_number_id": PHONE_ID},
        "contacts": [{"profile": {"name": "Jane Doe"}, "wa_id": "15551234567"}],
        "messages": [
            {"from": "15551234567", "id": "wamid.X1", "timestamp": "1700000000", "type": "text",
             "text": {"body": "hello"}}
        ],
    }
    payload = WebhookPayload.model_validate(_payload(value))
    (message,) = payload.iter_messages()
    assert message.from_number == "15551234567"
    assert message.text.body == "hello"
    assert payload.entry[0].changes[0].value.contacts[0].profile.name == "Jane Doe"


def test_audio_message_defaults_voice_to_false():
    value = {
        "messaging_product": "whatsapp",
        "messages": [
            {"from": "15551234567", "id": "wamid.X2", "timestamp": "1", "type": "audio",
             "audio": {"mime_type": "audio/ogg", "sha256": "abc", "id": "media-1"}}
        ],
    }
    (message,) = WebhookPayload.model_validate(_payload(value)).iter_messages()
    assert message.audio.voice is False
    assert message.text is None


def test_status_update_yields_no_messages():
    value = {"messaging_product": "whatsapp", "statuses": [{"id": "wamid.X3", "status": "read"}]}
    assert list(WebhookPayload.model_validate(_payload(value)).iter_messages()) == []
