"""Generic, prefix-aware environment variable reader."""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from typing import Any

from .errors import ConfigurationError

__all__ = ["EnvReader"]


class _Missing:
    def __repr__(self) -> str:
        return "<MISSING>"


MISSING: Any = _Missing()

_TRUE = {"true", "1", "yes", "on"}
_FALSE = {"false", "0", "no", "off"}


class EnvReader:
    """Read typed values from environment variables sharing a common prefix.

    Args:
        prefix: String prepended to every variable name (default empty).
        environ: Mapping to read from. When None, ``os.environ`` is read at
            call time, not at construction time.
    """

    def __init__(self, prefix: str = "", environ: Mapping[str, str] | None = None) -> None:
        self._prefix = prefix
        self._environ = environ

    @property
    def prefix(self) -> str:
        """Prefix prepended to every variable name."""
        return self._prefix

    def key(self, name: str) -> str:
        """Return the full variable name for ``name``."""
        return f"{self._prefix}{name}"

    def _raw(self, name: str) -> str | None:
        source = os.environ if self._environ is None else self._environ
        value = source.get(self.key(name))
        if value is None or value == "":
            return None
        return value

    def _read(self, name: str, default: Any, convert: Callable[[str], Any], kind: str) -> Any:
        raw = self._raw(name)
        if raw is None:
            if default is MISSING:
                raise ConfigurationError(f"Missing required environment variable {self.key(name)}")
            return default
        try:
            return convert(raw)
        except ValueError as exc:
            raise ConfigurationError(
                f"Environment variable {self.key(name)} must be {kind}, got {raw!r}"
            ) from exc

    def get(self, name: str, default: Any = MISSING) -> Any:
        """Return the string value, or ``default`` when unset or empty."""
        return self._read(name, default, str, "a string")

    def get_int(self, name: str, default: Any = MISSING) -> Any:
        """Return the value as an int."""
        return self._read(name, default, int, "an integer")

    def get_float(self, name: str, default: Any = MISSING) -> Any:
        """Return the value as a float."""
        return self._read(name, default, float, "a number")

    def get_bool(self, name: str, default: Any = MISSING) -> Any:
        """Return the value as a bool (true/1/yes/on or false/0/no/off)."""

        def convert(raw: str) -> bool:
            lowered = raw.strip().lower()
            if lowered in _TRUE:
                return True
            if lowered in _FALSE:
                return False
            raise ValueError(raw)

        return self._read(name, default, convert, "a boolean")

    def get_list(self, name: str, default: Any = MISSING, sep: str = ",") -> Any:
        """Return the value split on ``sep``, stripped, without empty items."""

        def convert(raw: str) -> list[str]:
            return [item.strip() for item in raw.split(sep) if item.strip()]

        return self._read(name, default, convert, "a list")
