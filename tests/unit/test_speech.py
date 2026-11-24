"""Unit tests for GoogleSpeech with fake clients (no network, no credentials)."""

import io
import struct
import wave
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from google.cloud import speech_v1, texttospeech_v1

from agent_utils_sdk.errors import IntegrationError
from agent_utils_sdk.speech import GoogleSpeech, GoogleSpeechSettings, build_ssml


def _wav(seconds, rate=8000, channels=1):
    frames = int(seconds * rate)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(2)
        w.setframerate(rate)
        sample = struct.pack("<h", 1000)
        w.writeframes(sample * channels * frames)
    return buf.getvalue()


def _result(text):
    return SimpleNamespace(results=[SimpleNamespace(alternatives=[SimpleNamespace(transcript=text)])])


def test_build_ssml_escapes_markup():
    assert build_ssml("<b> & </b>") == "<speak>&lt;b&gt; &amp; &lt;/b&gt;</speak>"


def test_settings_from_env_uses_prefix_and_defaults():
    settings = GoogleSpeechSettings.from_env(environ={"GOOGLE_SPEECH_SAMPLE_RATE_HERTZ": "8000"})
    assert settings.sample_rate_hertz == 8000
    assert settings.language_code == "en-US"


async def test_speech_to_text_handles_stereo_and_same_rate():
    fake = SimpleNamespace(recognize=AsyncMock(return_value=_result(" hi ")))
    speech = GoogleSpeech(GoogleSpeechSettings(sample_rate_hertz=8000), stt_client=fake)
    assert await speech.speech_to_text(_wav(0.2, rate=8000, channels=2)) == "hi"
    assert fake.recognize.await_args.kwargs["audio"].content[:4] == b"RIFF"


async def test_speech_to_text_rejects_undecodable_audio():
    speech = GoogleSpeech(stt_client=SimpleNamespace(recognize=AsyncMock()))
    with pytest.raises(ValueError, match="decode"):
        await speech.speech_to_text(b"not audio")


async def test_speech_to_text_wraps_api_errors():
    fake = SimpleNamespace(recognize=AsyncMock(side_effect=RuntimeError("quota")))
    with pytest.raises(IntegrationError):
        await GoogleSpeech(stt_client=fake).speech_to_text(_wav(0.2))


async def test_text_to_speech_wraps_api_errors():
    fake = SimpleNamespace(synthesize_speech=AsyncMock(side_effect=RuntimeError("quota")))
    with pytest.raises(IntegrationError):
        await GoogleSpeech(tts_client=fake).text_to_speech("hello")


def test_clients_are_created_lazily_without_credentials(monkeypatch):
    created = []

    class FakeStt:
        def __init__(self):
            created.append("stt")

    class FakeTts:
        def __init__(self):
            created.append("tts")

    monkeypatch.setattr(speech_v1, "SpeechAsyncClient", FakeStt)
    monkeypatch.setattr(texttospeech_v1, "TextToSpeechAsyncClient", FakeTts)
    speech = GoogleSpeech()
    assert created == []
    assert isinstance(speech.stt_client, FakeStt)
    assert isinstance(speech.tts_client, FakeTts)
    assert speech.stt_client is speech.stt_client
    assert created == ["stt", "tts"]


def test_clients_use_credentials_file_when_configured(monkeypatch):
    calls = []

    class FakeStt:
        @classmethod
        def from_service_account_file(cls, path):
            calls.append(("stt", path))
            return cls()

    class FakeTts:
        @classmethod
        def from_service_account_file(cls, path):
            calls.append(("tts", path))
            return cls()

    monkeypatch.setattr(speech_v1, "SpeechAsyncClient", FakeStt)
    monkeypatch.setattr(texttospeech_v1, "TextToSpeechAsyncClient", FakeTts)
    speech = GoogleSpeech(GoogleSpeechSettings(credentials_file="creds.json"))
    speech.stt_client
    speech.tts_client
    assert calls == [("stt", "creds.json"), ("tts", "creds.json")]
