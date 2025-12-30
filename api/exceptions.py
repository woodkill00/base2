class UpstreamTimeout(Exception):
    """Raised when an upstream service times out."""


class UpstreamBadResponse(Exception):
    """Raised when an upstream service returns an invalid or bad response."""


class ConfigError(Exception):
    """Raised when application configuration is invalid or missing."""
