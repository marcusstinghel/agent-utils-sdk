"""Message envelope, NATS subject builder and message handler (no NATS dependency)."""

from __future__ import annotations

import json
import logging
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

__all__ = ["Envelope", "SubjectBuilder", "MessageHandler"]


class Envelope(BaseModel):
    """Minimal message envelope. Extra fields are kept."""

    model_config = ConfigDict(extra="allow")

    user_id: str
    message_id: str
    event_type: str | None = None
    user_name: str | None = None
    timestamp: str | None = None
    text: str | None = None
    audio_data: str | None = None
    role: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SubjectBuilder:
    """Build dotted subjects from envelope fields.

    Args:
        fields: Envelope fields that make up the subject, in order.
        prefix: Optional leading token.
        placeholder: Token used for missing or None values.
        separator: Token separator.
    """

    def __init__(
        self,
        fields: Sequence[str] = ("user_id", "message_id", "event_type"),
        prefix: str | None = None,
        placeholder: str = "_",
        separator: str = ".",
    ) -> None:
        self.fields: tuple[str, ...] = tuple(fields)
        self.prefix = prefix
        self.placeholder = placeholder
        self.separator = separator

    def _check(self, token: str) -> str:
        bad = token == "" or self.separator in token or "*" in token or ">" in token
        if bad or any(ch.isspace() for ch in token):
            raise ValueError(f"Invalid subject token: {token!r}")
        return token

    def build(self, envelope: BaseModel | Mapping[str, Any]) -> str:
        """Return the subject for ``envelope``."""
        tokens = [self.prefix] if self.prefix else []
        for name in self.fields:
            if isinstance(envelope, Mapping):
                value = envelope.get(name)
            else:
                value = getattr(envelope, name, None)
            tokens.append(self.placeholder if value is None else self._check(str(value)))
        return self.separator.join(self._check(t) for t in tokens)

    def pattern(self, **fixed: Any) -> str:
        """Return a subscription pattern; fields not given become ``*``."""
        unknown = set(fixed) - set(self.fields)
        if unknown:
            raise ValueError(f"Unknown subject fields: {sorted(unknown)}")
        tokens = [self.prefix] if self.prefix else []
        for name in self.fields:
            tokens.append("*" if name not in fixed else self._check(str(fixed[name])))
        return self.separator.join(tokens)


class MessageHandler:
    """Parse incoming messages and derive subjects.

    Args:
        subject_builder: Builder used by ``to_subject`` (default ``SubjectBuilder()``).
        logger: Logger to use (default module logger).
    """

    def __init__(
        self,
        subject_builder: SubjectBuilder | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.subject_builder = subject_builder or SubjectBuilder()
        self.logger = logger or logging.getLogger(__name__)

    def to_subject(self, envelope: BaseModel | Mapping[str, Any]) -> str:
        """Return the subject for ``envelope``."""
        return self.subject_builder.build(envelope)

    def parse(self, message: Any, model: type[BaseModel] = Envelope) -> BaseModel:
        """Parse bytes, str, mapping or an object with ``.data`` into ``model``.

        Raises:
            ValueError: If the payload is malformed or fails validation.
        """
        data = getattr(message, "data", message)
        if isinstance(data, Mapping):
            obj: Any = data
        else:
            try:
                obj = json.loads(data)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Message is not valid JSON: {exc}") from exc
        if isinstance(obj, list):
            if len(obj) != 1:
                raise ValueError(f"Expected a list with exactly one item, got {len(obj)}")
            obj = obj[0]
        if not isinstance(obj, Mapping):
            raise ValueError("Message payload must be a JSON object")
        try:
            return model.model_validate(obj)
        except ValidationError as exc:
            fields = ", ".join(sorted({".".join(str(p) for p in e["loc"]) for e in exc.errors()}))
            raise ValueError(f"Invalid message, check fields: {fields}") from exc

    def require_role(self, role: str | None, allowed: Iterable[str]) -> bool:
        """Return True if ``role`` is allowed, otherwise raise PermissionError."""
        if role is not None and role in set(allowed):
            return True
        raise PermissionError(f"Role {role!r} is not allowed")
