"""Unit tests for NatsClient with a mocked nats.connect."""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import nats
import pytest
from nats.js.errors import BucketNotFoundError

from agent_utils_sdk.errors import ConfigurationError, IntegrationError
from agent_utils_sdk.nats import NatsClient, NatsSettings


def _setup(monkeypatch, stream="events", connect_error=None):
    consumer = MagicMock()
    consumer.fetch = AsyncMock(return_value=[])
    kv = MagicMock()
    kv.put = AsyncMock()
    kv.get = AsyncMock(return_value=SimpleNamespace(value=b"v"))
    js = MagicMock()
    js.pull_subscribe = AsyncMock(return_value=consumer)
    js.key_value = AsyncMock(return_value=kv)
    js.create_key_value = AsyncMock()
    nc = MagicMock()
    nc.publish = AsyncMock()
    nc.subscribe = AsyncMock(return_value="sub")
    nc.drain = AsyncMock()
    nc.close = AsyncMock()
    nc.jetstream = MagicMock(return_value=js)
    connect = AsyncMock(return_value=nc, side_effect=connect_error)
    monkeypatch.setattr(nats, "connect", connect)
    client = NatsClient(NatsSettings(servers=["nats://localhost:4222"], stream=stream))
    return SimpleNamespace(client=client, nc=nc, js=js, consumer=consumer, kv=kv)


async def test_connect_failure_is_wrapped(monkeypatch):
    env = _setup(monkeypatch, connect_error=OSError("refused"))
    with pytest.raises(IntegrationError):
        await env.client.connect()


async def test_callbacks_only_log(monkeypatch, caplog):
    env = _setup(monkeypatch)
    await env.client.connect()
    caplog.set_level("DEBUG")
    client = env.client
    await client._error_cb(RuntimeError("x"))
    await client._reconnected_cb()
    await client._disconnected_cb()
    await client._closed_cb()
    assert "NATS reconnected" in caplog.text


async def test_close_without_connection_returns_false(monkeypatch):
    env = _setup(monkeypatch)
    assert await env.client.close() is False
    await env.client.connect()
    assert await env.client.close() is True
    assert await env.client.close() is False


async def test_subscribe_and_publish_errors_are_wrapped(monkeypatch):
    env = _setup(monkeypatch)
    await env.client.connect()
    env.nc.subscribe.side_effect = OSError("x")
    with pytest.raises(IntegrationError):
        await env.client.subscribe("a.b")
    env.nc.publish.side_effect = OSError("x")
    with pytest.raises(IntegrationError):
        await env.client.publish("a.b", {"k": 1})


async def test_get_messages_requires_connection_and_stream(monkeypatch):
    env = _setup(monkeypatch, stream=None)
    with pytest.raises(ConnectionError):
        await env.client.get_messages("a")
    await env.client.connect()
    with pytest.raises(ConfigurationError):
        await env.client.get_messages("a")


async def test_get_messages_backend_error_is_wrapped(monkeypatch):
    env = _setup(monkeypatch)
    await env.client.connect()
    env.consumer.fetch.side_effect = ValueError("broken")
    with pytest.raises(IntegrationError):
        await env.client.get_messages("a")


async def test_get_messages_builtin_timeout_returns_empty(monkeypatch):
    env = _setup(monkeypatch)
    await env.client.connect()
    env.consumer.fetch.side_effect = TimeoutError()
    assert await env.client.get_messages("a") == []


async def test_get_last_message_returns_none_when_empty(monkeypatch):
    env = _setup(monkeypatch)
    await env.client.connect()
    assert await env.client.get_last_message("a") is None


async def test_get_messages_decodes_and_acks(monkeypatch):
    env = _setup(monkeypatch)
    msg = SimpleNamespace(subject="a.b", data=json.dumps({"n": 1}).encode(), ack=AsyncMock())
    env.consumer.fetch.return_value = [msg]
    await env.client.connect()
    assert await env.client.get_messages("a.*") == [{"subject": "a.b", "data": {"n": 1}}]
    msg.ack.assert_awaited_once()


async def test_create_bucket_and_errors(monkeypatch):
    env = _setup(monkeypatch)
    await env.client.connect()
    assert await env.client.create_bucket("b") is True
    env.js.create_key_value.side_effect = OSError("x")
    with pytest.raises(IntegrationError):
        await env.client.create_bucket("b")


async def test_put_without_create_missing_raises(monkeypatch):
    env = _setup(monkeypatch)
    await env.client.connect()
    env.js.key_value.side_effect = BucketNotFoundError()
    with pytest.raises(IntegrationError):
        await env.client.put_bucket_data("b", "k", b"d", create_missing=False)
    env.js.create_key_value.assert_not_awaited()


async def test_put_propagates_create_failure(monkeypatch):
    env = _setup(monkeypatch)
    await env.client.connect()
    env.js.key_value.side_effect = BucketNotFoundError()
    env.js.create_key_value.side_effect = OSError("x")
    with pytest.raises(IntegrationError):
        await env.client.put_bucket_data("b", "k", b"d")


async def test_put_and_get_errors_are_wrapped(monkeypatch):
    env = _setup(monkeypatch)
    await env.client.connect()
    env.kv.put.side_effect = OSError("x")
    with pytest.raises(IntegrationError):
        await env.client.put_bucket_data("b", "k", b"d")
    env.kv.get.side_effect = OSError("x")
    with pytest.raises(IntegrationError):
        await env.client.get_bucket_data("b", "k")
