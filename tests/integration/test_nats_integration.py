"""Integration test against a real NATS server (run with ``pytest -m integration``)."""

import os

import pytest

from agent_utils_sdk.nats import NatsClient, NatsSettings

pytestmark = pytest.mark.integration


async def test_publish_and_read_back_from_stream():
    if not os.environ.get("NATS_URL"):
        pytest.skip("NATS_URL is not set")
    settings = NatsSettings.from_env()
    async with NatsClient(settings) as client:
        js = client._nc.jetstream()
        await js.add_stream(name="acceptance_tmp", subjects=["demo.>"])
        try:
            await client.publish("demo.hello", {"text": "hi"})
            messages = await client.get_messages("demo.hello", stream="acceptance_tmp")
            assert messages == [{"subject": "demo.hello", "data": {"text": "hi"}}]
        finally:
            await js.delete_stream("acceptance_tmp")
