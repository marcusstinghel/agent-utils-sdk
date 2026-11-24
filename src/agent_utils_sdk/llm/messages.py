"""Chat message model."""

from typing import Literal

from pydantic import BaseModel

__all__ = ["ChatMessage"]


class ChatMessage(BaseModel):
    """A single chat message."""

    role: Literal["system", "user", "assistant"]
    content: str
