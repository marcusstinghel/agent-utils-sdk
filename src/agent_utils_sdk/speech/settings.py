"""Google speech settings."""

from __future__ import annotations

from collections.abc import Mapping

from pydantic import BaseModel

from ..config import EnvReader

__all__ = ["GoogleSpeechSettings"]


class GoogleSpeechSettings(BaseModel):
    """Language, voice and credential settings for Google speech services."""

    language_code: str = "en-US"
    voice_name: str | None = None
    sample_rate_hertz: int = 16000
    credentials_file: str | None = None
    enable_automatic_punctuation: bool = True
    max_sync_duration_seconds: float = 60

    @classmethod
    def from_env(
        cls, prefix: str = "GOOGLE_SPEECH_", environ: Mapping[str, str] | None = None
    ) -> GoogleSpeechSettings:
        """Build settings from optional LANGUAGE_CODE, VOICE_NAME, SAMPLE_RATE_HERTZ, CREDENTIALS_FILE."""
        env = EnvReader(prefix, environ)
        return cls(
            language_code=env.get("LANGUAGE_CODE", default="en-US"),
            voice_name=env.get("VOICE_NAME", default=None),
            sample_rate_hertz=env.get_int("SAMPLE_RATE_HERTZ", default=16000),
            credentials_file=env.get("CREDENTIALS_FILE", default=None),
        )
