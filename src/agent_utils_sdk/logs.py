"""Logging helpers."""

from __future__ import annotations

import logging

__all__ = ["get_logger", "configure_logging", "DEFAULT_FORMAT"]

DEFAULT_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"


def get_logger(name: str = "agent_utils_sdk") -> logging.Logger:
    """Return the logger called ``name``."""
    return logging.getLogger(name)


def configure_logging(level: int = logging.INFO, fmt: str = DEFAULT_FORMAT, force: bool = False) -> None:
    """Configure root logging for applications (libraries should not call this)."""
    logging.basicConfig(level=level, format=fmt, force=force)
