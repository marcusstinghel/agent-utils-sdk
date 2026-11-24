"""Unit tests for logging helpers."""

import logging

import agent_utils_sdk
from agent_utils_sdk import logs


def test_get_logger_default_and_custom_name():
    assert logs.get_logger().name == "agent_utils_sdk"
    assert logs.get_logger("worker").name == "worker"


def test_package_has_null_handler():
    handlers = logging.getLogger("agent_utils_sdk").handlers
    assert any(isinstance(h, logging.NullHandler) for h in handlers)
    assert agent_utils_sdk.__version__ == "0.1.0"


def test_configure_logging_applies_level_and_format():
    root = logging.getLogger()
    saved_handlers, saved_level = root.handlers[:], root.level
    try:
        logs.configure_logging(level=logging.WARNING, fmt="%(message)s", force=True)
        assert root.level == logging.WARNING
        assert root.handlers[0].formatter._fmt == "%(message)s"
    finally:
        root.handlers[:] = saved_handlers
        root.setLevel(saved_level)
