"""Unit tests for EnvReader."""

import pytest

from agent_utils_sdk.config import MISSING, EnvReader
from agent_utils_sdk.errors import ConfigurationError


def test_prefix_and_key():
    env = EnvReader(prefix="APP_", environ={"APP_NAME": "demo"})
    assert env.prefix == "APP_"
    assert env.key("NAME") == "APP_NAME"
    assert env.get("NAME") == "demo"


def test_missing_variable_names_full_key():
    with pytest.raises(ConfigurationError, match="APP_NAME"):
        EnvReader(prefix="APP_", environ={}).get("NAME")


def test_defaults_are_returned_for_missing_and_empty():
    env = EnvReader(environ={"EMPTY": ""})
    assert env.get("EMPTY", default="x") == "x"
    assert env.get("ABSENT", default=None) is None
    assert env.get_float("ABSENT", default=1.5) == 1.5
    assert env.get_bool("ABSENT", default=False) is False
    assert env.get_list("ABSENT", default=[]) == []


def test_typed_getters():
    env = EnvReader(environ={"N": "7", "F": "0.25", "B": "On", "L": "a; b;;c"})
    assert env.get_int("N") == 7
    assert env.get_float("F") == 0.25
    assert env.get_bool("B") is True
    assert env.get_list("L", sep=";") == ["a", "b", "c"]


@pytest.mark.parametrize("method", ["get_int", "get_float", "get_bool"])
def test_invalid_values_raise_configuration_error(method):
    env = EnvReader(prefix="P_", environ={"P_V": "not-a-value"})
    with pytest.raises(ConfigurationError, match="P_V"):
        getattr(env, method)("V")


def test_reads_process_environment_at_call_time(monkeypatch):
    env = EnvReader(prefix="UNIT_LAZY_")
    monkeypatch.setenv("UNIT_LAZY_X", "1")
    assert env.get_int("X") == 1


def test_missing_sentinel_repr():
    assert repr(MISSING) == "<MISSING>"
