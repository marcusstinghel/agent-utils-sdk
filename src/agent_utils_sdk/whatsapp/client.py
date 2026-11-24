"""Async WhatsApp Cloud API client."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from ..errors import IntegrationError
from .models import MediaInfo, SendMessageResponse
from .settings import WhatsAppSettings

__all__ = ["WhatsAppClient"]


class WhatsAppClient:
    """Send messages and manage media through the WhatsApp Cloud API.

    Args:
        settings: Credentials and endpoint settings.
        http_client: Async HTTP client used for every request (created when omitted).
        logger: Logger to use (default module logger).
    """

    def __init__(
        self,
        settings: WhatsAppSettings,
        *,
        http_client: httpx.AsyncClient | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.settings = settings
        self.logger = logger or logging.getLogger(__name__)
        self._http = http_client or httpx.AsyncClient(timeout=30.0)

    @property
    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.settings.access_token.get_secret_value()}"}

    async def _request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        try:
            response = await self._http.request(method, url, headers=self._headers, **kwargs)
        except httpx.HTTPError as exc:
            raise IntegrationError(f"WhatsApp request failed: {exc}") from exc
        if response.status_code >= 400:
            raise IntegrationError(f"WhatsApp API returned HTTP {response.status_code} ({method})")
        return response

    @property
    def _messages_url(self) -> str:
        return f"{self.settings.api_url}/{self.settings.phone_number_id}/messages"

    async def _send(self, body: dict[str, Any]) -> SendMessageResponse:
        response = await self._request("POST", self._messages_url, json=body)
        return SendMessageResponse.model_validate(response.json())

    async def send_text(self, to: str | int, body: str) -> SendMessageResponse:
        """Send a text message to ``to``."""
        payload = {
            "messaging_product": "whatsapp",
            "to": str(to),
            "type": "text",
            "text": {"body": body},
        }
        result = await self._send(payload)
        self.logger.info("Sent WhatsApp text message (%d chars)", len(body))
        return result

    async def upload_media(self, data: bytes, mime_type: str, filename: str) -> str:
        """Upload media and return its id."""
        url = f"{self.settings.api_url}/{self.settings.phone_number_id}/media"
        response = await self._request(
            "POST",
            url,
            files={"file": (filename, data, mime_type)},
            data={"messaging_product": "whatsapp"},
        )
        media_id = response.json()["id"]
        self.logger.info("Uploaded media %s (%d bytes)", media_id, len(data))
        return str(media_id)

    async def send_audio(
        self,
        to: str | int,
        audio: bytes,
        *,
        mime_type: str = "audio/mpeg",
        filename: str = "audio.mp3",
        delete_after_send: bool = True,
    ) -> SendMessageResponse:
        """Upload ``audio``, send it to ``to`` and optionally delete the upload."""
        media_id = await self.upload_media(audio, mime_type, filename)
        payload = {
            "messaging_product": "whatsapp",
            "to": str(to),
            "type": "audio",
            "audio": {"id": media_id},
        }
        result = await self._send(payload)
        if delete_after_send:
            await self.delete_media(media_id)
        return result

    async def delete_media(self, media_id: str) -> bool:
        """Delete an uploaded media object."""
        response = await self._request("DELETE", f"{self.settings.api_url}/{media_id}")
        if response.json().get("success") is not True:
            raise IntegrationError(f"WhatsApp did not confirm deletion of media {media_id}")
        return True

    async def get_media_url(self, media_id: str) -> str:
        """Return the download URL of a media object."""
        response = await self._request("GET", f"{self.settings.api_url}/{media_id}")
        return MediaInfo.model_validate(response.json()).url

    async def download_media(self, media_id: str) -> bytes:
        """Download the content of a media object."""
        url = await self.get_media_url(media_id)
        response = await self._request("GET", url)
        return response.content

    async def aclose(self) -> None:
        """Close the underlying HTTP client."""
        await self._http.aclose()
