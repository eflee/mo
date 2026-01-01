"""Custom exception classes for mo."""


class MoError(Exception):
    """Base exception for all mo errors."""

    pass


class ConfigError(MoError):
    """Configuration-related errors."""

    pass


class ValidationError(MoError):
    """Input validation errors."""

    pass


class ProviderError(MoError):
    """Metadata provider API errors."""

    pass


class FileSystemError(MoError):
    """File system operation errors."""

    pass
