"""Async NATS / JetStream client."""

from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

import nats
import nats.errors
from nats.js.api import AckPolicy, ConsumerConfig, DeliverPolicy
from nats.js.errors import BucketNotFoundError
from pydantic import BaseModel

from ..errors import ConfigurationError, IntegrationError
from .settings import NatsSettings

__all__ = ["NatsClient"]


class NatsClient:
    """Thin wrapper around nats-py with logging and error mapping.

    Args:
        settings: Connection settings.
        logger: Logger to use (default module logger).
    """

    def __init__(self, settings: NatsSettings, logger: logging.Logger | None = None) -> None:
        self.settings = settings
        self.logger = logger or logging.getLogger(__name__)
        self._nc: Any = None

    async def _error_cb(self, exc: Exception) -> None:
        self.logger.error("NATS error: %s", exc)

    async def _reconnected_cb(self) -> None:
        self.logger.info("NATS reconnected")

    async def _disconnected_cb(self) -> None:
        self.logger.warning("NATS disconnected")

    async def _closed_cb(self) -> None:
        self.logger.info("NATS connection closed")

    async def connect(self) -> Any:
        """Connect to the server and return the underlying connection."""
        options = self.settings.to_connect_options()
        options.update(
            error_cb=self._error_cb,
            reconnected_cb=self._reconnected_cb,
            disconnected_cb=self._disconnected_cb,
            closed_cb=self._closed_cb,
        )
        try:
            self._nc = await nats.connect(**options)
        except Exception as exc:
            raise IntegrationError(f"Could not connect to NATS: {exc}") from exc
        self.logger.info("Connected to NATS")
        return self._nc

    async def close(self) -> bool:
        """Drain and close the connection. Returns False when not connected."""
        if self._nc is None:
            return False
        nc, self._nc = self._nc, None
        await nc.drain()
        await nc.close()
        return True

    async def __aenter__(self) -> NatsClient:
        await self.connect()
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.close()

    def _require_connection(self) -> Any:
        if self._nc is None:
            raise ConnectionError("Not connected to NATS; call connect() first")
        return self._nc

    async def subscribe(self, subject: str, cb: Callable[[Any], Awaitable[None]] | None = None) -> Any:
        """Subscribe to ``subject`` and return the subscription."""
        nc = self._require_connection()
        try:
            return await nc.subscribe(subject, cb=cb)
        except Exception as exc:
            raise IntegrationError(f"Could not subscribe to {subject}: {exc}") from exc

    async def publish(self, subject: str, payload: Mapping[str, Any] | BaseModel) -> bool:
        """Publish ``payload`` as a JSON object on ``subject``."""
        nc = self._require_connection()
        obj = payload.model_dump(mode="json") if isinstance(payload, BaseModel) else payload
        try:
            await nc.publish(subject, json.dumps(obj).encode())
        except Exception as exc:
            raise IntegrationError(f"Could not publish to {subject}: {exc}") from exc
        self.logger.debug("Published to %s", subject)
        return True

    def _resolve_stream(self, stream: str | None) -> str:
        resolved = stream or self.settings.stream
        if not resolved:
            raise ConfigurationError("No JetStream stream configured; pass stream= or set NatsSettings.stream")
        return resolved

    async def _fetch(
        self, subject: str, stream: str | None, policy: DeliverPolicy, batch: int, timeout: float
    ) -> list[dict[str, Any]]:
        nc = self._require_connection()
        resolved = self._resolve_stream(stream)
        collected: list[dict[str, Any]] = []
        try:
            js = nc.jetstream()
            consumer = await js.pull_subscribe(
                subject=subject,
                stream=resolved,
                config=ConsumerConfig(deliver_policy=policy, ack_policy=AckPolicy.EXPLICIT),
            )
            msgs = await consumer.fetch(batch=batch, timeout=timeout)
            for msg in msgs:
                collected.append({"subject": msg.subject, "data": json.loads(msg.data.decode())})
                await msg.ack()
        except (nats.errors.TimeoutError, TimeoutError):
            return collected
        except Exception as exc:
            raise IntegrationError(f"Could not fetch messages from {subject}: {exc}") from exc
        return collected

    async def get_messages(
        self, subject: str, max_num_messages: int = 10, stream: str | None = None, timeout: float = 1.0
    ) -> list[dict[str, Any]]:
        """Fetch up to ``max_num_messages`` messages and acknowledge them."""
        return await self._fetch(subject, stream, DeliverPolicy.ALL, max_num_messages, timeout)

    async def get_last_message(
        self, subject: str, stream: str | None = None, timeout: float = 1.0
    ) -> dict[str, Any] | None:
        """Return the last message on ``subject`` or None."""
        msgs = await self._fetch(subject, stream, DeliverPolicy.LAST, 1, timeout)
        return msgs[0] if msgs else None

    async def create_bucket(self, bucket: str) -> bool:
        """Create a key-value bucket."""
        nc = self._require_connection()
        try:
            await nc.jetstream().create_key_value(bucket=bucket)
        except Exception as exc:
            raise IntegrationError(f"Could not create bucket {bucket}: {exc}") from exc
        return True

    async def put_bucket_data(self, bucket: str, key: str, data: bytes, create_missing: bool = True) -> bool:
        """Store ``data`` under ``key``, creating the bucket when missing."""
        nc = self._require_connection()
        try:
            js = nc.jetstream()
            try:
                kv = await js.key_value(bucket=bucket)
            except BucketNotFoundError:
                if not create_missing:
                    raise
                await self.create_bucket(bucket)
                kv = await js.key_value(bucket=bucket)
            await kv.put(key, data)
        except IntegrationError:
            raise
        except Exception as exc:
            raise IntegrationError(f"Could not store {key} in {bucket}: {exc}") from exc
        return True

    async def get_bucket_data(self, bucket: str, key: str) -> bytes:
        """Return the value stored under ``key``."""
        nc = self._require_connection()
        try:
            kv = await nc.jetstream().key_value(bucket=bucket)
            entry = await kv.get(key)
        except Exception as exc:
            raise IntegrationError(f"Could not read {key} from {bucket}: {exc}") from exc
        return entry.value
