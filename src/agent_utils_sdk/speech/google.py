"""Google Cloud speech-to-text and text-to-speech."""

from __future__ import annotations

import io
import logging
from collections.abc import Sequence
from typing import Any

import resampy
import soundfile
from google.cloud import speech_v1, texttospeech_v1

from ..errors import IntegrationError
from .settings import GoogleSpeechSettings
from .ssml import build_ssml

__all__ = ["GoogleSpeech"]


class GoogleSpeech:
    """Speech-to-text and text-to-speech using Google Cloud.

    Clients are created lazily on first use and never modify the process environment.

    Args:
        settings: Language, voice and credential settings (defaults are neutral).
        stt_client: Pre-built async speech client.
        tts_client: Pre-built async text-to-speech client.
        logger: Logger to use (default module logger).
    """

    def __init__(
        self,
        settings: GoogleSpeechSettings | None = None,
        *,
        stt_client: Any = None,
        tts_client: Any = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.settings = settings or GoogleSpeechSettings()
        self.logger = logger or logging.getLogger(__name__)
        self._stt = stt_client
        self._tts = tts_client

    @property
    def stt_client(self) -> Any:
        """Speech client, created on first access."""
        if self._stt is None:
            path = self.settings.credentials_file
            if path:
                self._stt = speech_v1.SpeechAsyncClient.from_service_account_file(path)
            else:
                self._stt = speech_v1.SpeechAsyncClient()
        return self._stt

    @property
    def tts_client(self) -> Any:
        """Text-to-speech client, created on first access."""
        if self._tts is None:
            path = self.settings.credentials_file
            if path:
                self._tts = texttospeech_v1.TextToSpeechAsyncClient.from_service_account_file(path)
            else:
                self._tts = texttospeech_v1.TextToSpeechAsyncClient()
        return self._tts

    def _prepare_audio(self, audio: bytes) -> bytes:
        """Decode, downmix, resample and re-encode ``audio`` as 16-bit WAV."""
        try:
            data, rate = soundfile.read(io.BytesIO(audio), dtype="float32")
        except Exception as exc:
            raise ValueError(f"Could not decode audio: {exc}") from exc
        if data.ndim > 1:
            data = data.mean(axis=1)
        duration = len(data) / rate
        if duration > self.settings.max_sync_duration_seconds:
            raise ValueError(
                f"Audio is {duration:.1f}s long; the synchronous limit is "
                f"{self.settings.max_sync_duration_seconds}s"
            )
        target = self.settings.sample_rate_hertz
        if rate != target:
            data = resampy.resample(data, rate, target)
        buffer = io.BytesIO()
        soundfile.write(buffer, data, target, format="WAV", subtype="PCM_16")
        return buffer.getvalue()

    async def speech_to_text(self, audio: bytes, phrases: Sequence[str] = ()) -> str:
        """Transcribe ``audio`` (any format libsndfile can read, up to the sync limit).

        Raises:
            ValueError: If the audio cannot be decoded or is too long.
            IntegrationError: If the Google API call fails.
        """
        wav_bytes = self._prepare_audio(audio)
        contexts = [speech_v1.SpeechContext(phrases=list(phrases))] if phrases else []
        config = speech_v1.RecognitionConfig(
            encoding=speech_v1.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=self.settings.sample_rate_hertz,
            language_code=self.settings.language_code,
            enable_automatic_punctuation=self.settings.enable_automatic_punctuation,
            speech_contexts=contexts,
        )
        try:
            response = await self.stt_client.recognize(
                config=config, audio=speech_v1.RecognitionAudio(content=wav_bytes)
            )
        except Exception as exc:
            raise IntegrationError(f"Speech recognition failed: {exc}") from exc
        parts = [r.alternatives[0].transcript.strip() for r in response.results if r.alternatives]
        self.logger.info("Transcribed audio (%d bytes) into %d segments", len(audio), len(parts))
        return " ".join(parts)

    async def text_to_speech(self, text: str, *, ssml: bool = True) -> bytes:
        """Synthesize ``text`` into MP3 bytes.

        Raises:
            IntegrationError: If the API call fails or returns no audio.
        """
        if ssml:
            synthesis_input = texttospeech_v1.SynthesisInput(ssml=build_ssml(text))
        else:
            synthesis_input = texttospeech_v1.SynthesisInput(text=text)
        voice = texttospeech_v1.VoiceSelectionParams(
            language_code=self.settings.language_code, name=self.settings.voice_name or ""
        )
        audio_config = texttospeech_v1.AudioConfig(audio_encoding=texttospeech_v1.AudioEncoding.MP3)
        try:
            response = await self.tts_client.synthesize_speech(
                input=synthesis_input, voice=voice, audio_config=audio_config
            )
        except Exception as exc:
            raise IntegrationError(f"Speech synthesis failed: {exc}") from exc
        if not response.audio_content:
            raise IntegrationError("Speech synthesis returned no audio")
        return bytes(response.audio_content)
