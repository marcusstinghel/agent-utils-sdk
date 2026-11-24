"""Models for WhatsApp Cloud API webhook payloads."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "WebhookPayload",
    "Entry",
    "Change",
    "Value",
    "Metadata",
    "Contact",
    "Profile",
    "InboundMessage",
    "Text",
    "Audio",
]


class Text(BaseModel):
    """Text message body."""

    body: str


class Audio(BaseModel):
    """Audio message reference."""

    mime_type: str
    sha256: str
    id: str
    voice: bool = False


class Profile(BaseModel):
    """Sender profile."""

    name: str


class Contact(BaseModel):
    """Sender contact."""

    wa_id: str
    profile: Profile


class Metadata(BaseModel):
    """Business phone number the event belongs to."""

    display_phone_number: str
    phone_number_id: str


class InboundMessage(BaseModel):
    """A message received from a user."""

    model_config = ConfigDict(populate_by_name=True)

    from_number: str = Field(alias="from")
    id: str
    timestamp: str
    type: str
    text: Text | None = None
    audio: Audio | None = None


class Value(BaseModel):
    """Payload of a change notification."""

    messaging_product: str
    metadata: Metadata | None = None
    contacts: list[Contact] | None = None
    messages: list[InboundMessage] | None = None
    statuses: list[dict[str, Any]] | None = None


class Change(BaseModel):
    """A single change inside an entry."""

    field: str
    value: Value


class Entry(BaseModel):
    """A webhook entry (one per business account)."""

    id: str
    changes: list[Change]


class WebhookPayload(BaseModel):
    """Top-level webhook body."""

    object: str
    entry: list[Entry]

    def iter_messages(self) -> Iterator[InboundMessage]:
        """Yield every inbound message contained in the payload."""
        for entry in self.entry:
            for change in entry.changes:
                yield from change.value.messages or []
