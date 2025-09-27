"""Logger factory for creating configured loggers."""

from functools import lru_cache

import structlog


@lru_cache(maxsize=128)
def get_logger(name: str) -> structlog.BoundLogger:
    """Get or create a logger instance.

    This function returns a cached structlog logger instance for the given name.
    The logger is automatically configured with the processors and settings
    defined during setup_logging().

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured structlog logger bound to the given name

    Example:
        >>> from youtrack_mcp.logging import get_logger
        >>> logger = get_logger(__name__)
        >>> logger.info("processing_started", items=10)
    """
    return structlog.get_logger(name)