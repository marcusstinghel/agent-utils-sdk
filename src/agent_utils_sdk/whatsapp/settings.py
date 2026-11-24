"""WhatsApp Cloud API settings."""

from __future__ import annotations

from collections.abc import Mapping

from pydantic import BaseModel, SecretStr

from ..config import EnvReader

__all__ = ["WhatsAppSettings"]


class WhatsAppSettings(BaseModel):
    """Credentials and endpoint of the WhatsApp Cloud API."""

    access_token: SecretStr
    phone_number_id: str
    api_version: str = "v22.0"
    base_url: str = "https://graph.facebook.com"

    @property
    def api_url(self) -> str:
        """Base URL including the API version, without a trailing slash."""
        return f"{self.base_url.rstrip('/')}/{self.api_version}"

    @classmethod
    def from_env(cls, prefix: str = "WHATSAPP_", environ: Mapping[str, str] | None = None) -> WhatsAppSettings:
        """Build settings from ACCESS_TOKEN, PHONE_NUMBER_ID and optional API_VERSION / BASE_URL."""
        env = EnvReader(prefix, environ)
        return cls(
            access_token=env.get("ACCESS_TOKEN"),
            phone_number_id=env.get("PHONE_NUMBER_ID"),
            api_version=env.get("API_VERSION", default="v22.0"),
            base_url=env.get("BASE_URL", default="https://graph.facebook.com"),
        )
