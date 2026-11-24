"""Unit tests for NatsSettings."""

import pytest

from agent_utils_sdk.errors import ConfigurationError
from agent_utils_sdk.nats import NatsSettings


def test_from_env_reads_all_fields():
    settings = NatsSettings.from_env(
        prefix="BUS_",
        environ={
            "BUS_URL": "nats://localhost:4222,nats://localhost:4223",
            "BUS_TOKEN": "hidden-value",
            "BUS_STREAM": "events",
            "BUS_MAX_RECONNECT": "3",
            "BUS_RECONNECT_TIME_WAIT": "0.5",
        },
    )
    assert settings.servers == ["nats://localhost:4222", "nats://localhost:4223"]
    assert settings.stream == "events"
    options = settings.to_connect_options()
    assert options["token"] == "hidden-value"
    assert options["max_reconnect_attempts"] == 3
    assert options["reconnect_time_wait"] == 0.5
    assert "hidden-value" not in repr(settings)


def test_missing_url_is_a_configuration_error():
    with pytest.raises(ConfigurationError, match="NATS_URL"):
        NatsSettings.from_env(environ={})


def test_invalid_number_is_a_configuration_error():
    with pytest.raises(ConfigurationError, match="NATS_MAX_RECONNECT"):
        NatsSettings.from_env(environ={"NATS_URL": "nats://localhost:4222", "NATS_MAX_RECONNECT": "many"})
