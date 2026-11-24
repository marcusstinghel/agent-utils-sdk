"""Google speech-to-text and text-to-speech (requires the ``google`` extra)."""

from .google import GoogleSpeech
from .settings import GoogleSpeechSettings
from .ssml import build_ssml

__all__ = ["GoogleSpeech", "GoogleSpeechSettings", "build_ssml"]
