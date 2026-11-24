"""SSML helper."""

from xml.sax.saxutils import escape

__all__ = ["build_ssml"]


def build_ssml(text: str) -> str:
    """Wrap ``text`` in a ``<speak>`` element, escaping XML special characters."""
    return "<speak>" + escape(text) + "</speak>"
