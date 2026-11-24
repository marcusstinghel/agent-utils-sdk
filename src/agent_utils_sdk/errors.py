"""Exception hierarchy used across the SDK."""

__all__ = ["AgentUtilsError", "ConfigurationError", "IntegrationError"]


class AgentUtilsError(Exception):
    """Base class for every error raised by this SDK."""


class ConfigurationError(AgentUtilsError, ValueError):
    """Raised when configuration is missing or invalid."""


class IntegrationError(AgentUtilsError, RuntimeError):
    """Raised when an external service or backend call fails."""
