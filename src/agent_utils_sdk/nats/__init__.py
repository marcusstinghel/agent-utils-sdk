"""NATS client and settings (requires the ``nats`` extra)."""

from .client import NatsClient
from .settings import NatsSettings

__all__ = ["NatsClient", "NatsSettings"]
