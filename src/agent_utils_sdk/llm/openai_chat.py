"""OpenAI chat settings and client."""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from typing import Any

import openai
from pydantic import BaseModel, SecretStr

from ..config import EnvReader
from ..errors import IntegrationError
from .messages import ChatMessage

__all__ = ["OpenAIChat", "OpenAISettings"]


class OpenAISettings(BaseModel):
    """Settings for the OpenAI (or compatible) chat API."""

    api_key: SecretStr
    model: str = "gpt-4o-mini"
    base_url: str | None = None

    @classmethod
    def from_env(cls, prefix: str = "OPENAI_", environ: Mapping[str, str] | None = None) -> OpenAISettings:
        """Build settings from ``<prefix>API_KEY`` and optional MODEL / BASE_URL."""
        env = EnvReader(prefix, environ)
        return cls(
            api_key=env.get("API_KEY"),
            model=env.get("MODEL", default="gpt-4o-mini"),
            base_url=env.get("BASE_URL", default=None),
        )


class OpenAIChat:
    """Streaming chat completions helper.

    Args:
        settings: Settings (default: read from the environment).
        client: Pre-built async client; created from settings when omitted.
        logger: Logger to use (default module logger).
    """

    def __init__(
        self,
        settings: OpenAISettings | None = None,
        *,
        client: Any = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.settings = settings or OpenAISettings.from_env()
        self.logger = logger or logging.getLogger(__name__)
        self.client = client or openai.AsyncOpenAI(
            api_key=self.settings.api_key.get_secret_value(),
            base_url=self.settings.base_url,
        )

    async def _complete(self, messages: list[dict[str, str]], model: str | None) -> str:
        chosen = model or self.settings.model
        self.logger.debug("Requesting chat completion: model=%s messages=%d", chosen, len(messages))
        try:
            stream = await self.client.chat.completions.create(model=chosen, messages=messages, stream=True)
            parts: list[str] = []
            async for chunk in stream:
                if not chunk.choices:
                    continue
                content = chunk.choices[0].delta.content
                if content is not None:
                    parts.append(content)
        except openai.AuthenticationError as exc:
            raise IntegrationError("OpenAI authentication failed; check the API key") from exc
        except Exception as exc:
            raise IntegrationError(f"Chat completion failed: {exc}") from exc
        return "".join(parts)

    async def respond(self, prompt: str, *, system: str | None = None, model: str | None = None) -> str:
        """Return the model answer for a single prompt."""
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return await self._complete(messages, model)

    async def respond_with_history(
        self, messages: Sequence[ChatMessage | Mapping[str, Any]], *, model: str | None = None
    ) -> str:
        """Return the model answer for a full conversation."""
        normalized = [ChatMessage.model_validate(m).model_dump() for m in messages]
        return await self._complete(normalized, model)
