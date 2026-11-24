"""NATS connection settings."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, SecretStr

from ..config import EnvReader

__all__ = ["NatsSettings"]


class NatsSettings(BaseModel):
    """Connection settings for a NATS server or cluster."""

    servers: list[str]
    user: str | None = None
    password: SecretStr | None = None
    token: SecretStr | None = None
    max_reconnect_attempts: int = 60
    reconnect_time_wait: float = 2.0
    stream: str | None = None

    @classmethod
    def from_env(cls, prefix: str = "NATS_", environ: Mapping[str, str] | None = None) -> NatsSettings:
        """Build settings from ``<prefix>URL`` and optional variables."""
        env = EnvReader(prefix, environ)
        return cls(
            servers=env.get_list("URL"),
            user=env.get("USER", default=None),
            password=env.get("PASSWORD", default=None),
            token=env.get("TOKEN", default=None),
            max_reconnect_attempts=env.get_int("MAX_RECONNECT", default=60),
            reconnect_time_wait=env.get_float("RECONNECT_TIME_WAIT", default=2.0),
            stream=env.get("STREAM", default=None),
        )

    def to_connect_options(self) -> dict[str, Any]:
        """Return keyword arguments for ``nats.connect``."""
        options: dict[str, Any] = {
            "servers": list(self.servers),
            "max_reconnect_attempts": self.max_reconnect_attempts,
            "reconnect_time_wait": self.reconnect_time_wait,
        }
        if self.user is not None:
            options["user"] = self.user
        if self.password is not None:
            options["password"] = self.password.get_secret_value()
        if self.token is not None:
            options["token"] = self.token.get_secret_value()
        return options
