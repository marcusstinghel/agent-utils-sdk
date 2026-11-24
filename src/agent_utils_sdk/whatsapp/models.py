"""Response models of the WhatsApp Cloud API."""

from pydantic import BaseModel

__all__ = ["SentContact", "SentMessage", "SendMessageResponse", "MediaInfo"]


class SentContact(BaseModel):
    """Recipient echoed back by the API."""

    input: str
    wa_id: str


class SentMessage(BaseModel):
    """Identifier of a sent message."""

    id: str


class SendMessageResponse(BaseModel):
    """Response of the messages endpoint."""

    messaging_product: str = "whatsapp"
    contacts: list[SentContact]
    messages: list[SentMessage]


class MediaInfo(BaseModel):
    """Metadata of an uploaded or received media object."""

    url: str
    mime_type: str
    sha256: str
    file_size: int
    id: str
    messaging_product: str
