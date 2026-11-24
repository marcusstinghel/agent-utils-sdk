"""Unit tests for the WhatsApp client using httpx.MockTransport."""

import httpx
import pytest

from agent_utils_sdk.errors import ConfigurationError, IntegrationError
from agent_utils_sdk.whatsapp import WhatsAppClient, WhatsAppSettings

PHONE_ID = "100000000000001"
SENT = {
    "messaging_product": "whatsapp",
    "contacts": [{"input": "15551234567", "wa_id": "15551234567"}],
    "messages": [{"id": "wamid.UNIT1"}],
}


def _client(handler):
    settings = WhatsAppSettings(access_token="tok", phone_number_id=PHONE_ID)
    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return WhatsAppClient(settings, http_client=http)


def test_settings_from_env_and_api_url():
    settings = WhatsAppSettings.from_env(
        environ={"WHATSAPP_ACCESS_TOKEN": "tok", "WHATSAPP_PHONE_NUMBER_ID": PHONE_ID, "WHATSAPP_BASE_URL": "http://x/"}
    )
    assert settings.api_url == "http://x/v22.0"
    with pytest.raises(ConfigurationError, match="WHATSAPP_PHONE_NUMBER_ID"):
        WhatsAppSettings.from_env(environ={"WHATSAPP_ACCESS_TOKEN": "tok"})


def test_default_http_client_is_created():
    client = WhatsAppClient(WhatsAppSettings(access_token="tok", phone_number_id=PHONE_ID))
    assert isinstance(client._http, httpx.AsyncClient)


async def test_send_text_returns_parsed_response():
    client = _client(lambda request: httpx.Response(200, json=SENT))
    response = await client.send_text("15551234567", "hello")
    assert response.messages[0].id == "wamid.UNIT1"
    await client.aclose()


async def test_transport_errors_are_wrapped():
    def handler(request):
        raise httpx.ConnectError("unreachable")

    with pytest.raises(IntegrationError):
        await _client(handler).send_text("15551234567", "x")


async def test_http_status_errors_are_wrapped():
    client = _client(lambda request: httpx.Response(500, json={}))
    with pytest.raises(IntegrationError, match="500"):
        await client.get_media_url("m1")


async def test_delete_media_requires_confirmation():
    client = _client(lambda request: httpx.Response(200, json={"success": "true"}))
    with pytest.raises(IntegrationError):
        await client.delete_media("m1")


async def test_download_media_uses_injected_client_for_cdn():
    seen = []

    def handler(request):
        seen.append(request.url.host)
        if request.url.host == "cdn.test":
            return httpx.Response(200, content=b"bytes")
        return httpx.Response(
            200,
            json={
                "url": "https://cdn.test/f",
                "mime_type": "audio/ogg",
                "sha256": "s",
                "file_size": 5,
                "id": "m1",
                "messaging_product": "whatsapp",
            },
        )

    assert await _client(handler).download_media("m1") == b"bytes"
    assert seen == ["graph.facebook.com", "cdn.test"]
