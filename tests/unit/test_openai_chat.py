"""Unit tests for OpenAISettings and OpenAIChat with a fake client."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import openai
import pytest

from agent_utils_sdk.errors import ConfigurationError, IntegrationError
from agent_utils_sdk.llm import ChatMessage, OpenAIChat, OpenAISettings


def _chunk(content):
    return SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=content))])


class _Stream:
    def __init__(self, parts):
        self._items = [_chunk(p) for p in parts] + [SimpleNamespace(choices=[])]

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self._items:
            raise StopAsyncIteration
        return self._items.pop(0)


def _client(parts=("ok",), error=None):
    create = AsyncMock(return_value=_Stream(parts), side_effect=error)
    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))), create


def test_settings_from_env_requires_key():
    with pytest.raises(ConfigurationError, match="OPENAI_API_KEY"):
        OpenAISettings.from_env(environ={})
    settings = OpenAISettings.from_env(environ={"OPENAI_API_KEY": "test-key", "OPENAI_MODEL": "m"})
    assert settings.model == "m"
    assert "test-key" not in repr(settings)


def test_default_settings_are_read_from_environment(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    chat = OpenAIChat(client=object())
    assert chat.settings.api_key.get_secret_value() == "test-key"


async def test_respond_concatenates_chunks():
    client, create = _client(("a", None, "b"))
    chat = OpenAIChat(OpenAISettings(api_key="k"), client=client)
    assert await chat.respond("hi", system="s") == "ab"
    assert create.await_args.kwargs["messages"][0] == {"role": "system", "content": "s"}


async def test_history_accepts_models_and_mappings():
    client, create = _client()
    chat = OpenAIChat(OpenAISettings(api_key="k"), client=client)
    await chat.respond_with_history([ChatMessage(role="user", content="a"), {"role": "assistant", "content": "b"}])
    assert [m["role"] for m in create.await_args.kwargs["messages"]] == ["user", "assistant"]


async def test_authentication_error_has_clear_message():
    response = SimpleNamespace(status_code=401, headers={}, request=None)
    error = openai.AuthenticationError("bad key", response=response, body=None)
    client, _ = _client(error=error)
    chat = OpenAIChat(OpenAISettings(api_key="k"), client=client)
    with pytest.raises(IntegrationError, match="authentication"):
        await chat.respond("hi")


async def test_other_errors_are_wrapped():
    client, _ = _client(error=RuntimeError("down"))
    chat = OpenAIChat(OpenAISettings(api_key="k"), client=client)
    with pytest.raises(IntegrationError, match="down"):
        await chat.respond("hi")
