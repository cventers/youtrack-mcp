"""Logging setup and configuration."""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import List, Optional

import structlog

from .config import LoggingConfig
from .processors import (
    ContextEnricher,
    ErrorDetailsAdder,
    PIDAdder,
    get_console_processor,
    get_file_processor,
)

# Global context enricher instance
_context_enricher: Optional[ContextEnricher] = None


def setup_logging(config: Optional[LoggingConfig] = None) -> ContextEnricher:
    """Set up the unified logging system.

    This function configures structlog with the appropriate processors
    and output handlers based on the provided configuration.

    Args:
        config: Logging configuration. If None, uses default settings.

    Returns:
        The context enricher instance for adding global context
    """
    global _context_enricher

    if config is None:
        config = LoggingConfig()

    # Create context enricher
    _context_enricher = ContextEnricher()

    # Build shared processors
    shared_processors: List = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.TimeStamper(fmt="iso"),
        PIDAdder(),
        ErrorDetailsAdder(),
        _context_enricher,
    ]

    # Configure structlog
    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure Python's logging
    handlers = []

    # Console handler
    if config.console_enabled:
        console_handler = logging.StreamHandler(sys.stderr)
        console_level = config.console_level or config.level
        console_handler.setLevel(getattr(logging, console_level))

        # Create formatter with appropriate processor
        console_formatter = structlog.stdlib.ProcessorFormatter(
            processor=get_console_processor(config.console_format),
            foreign_pre_chain=shared_processors,
        )
        console_handler.setFormatter(console_formatter)
        handlers.append(console_handler)

    # File handler
    if config.file:
        # Ensure directory exists
        file_path = Path(config.file)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Create handler with rotation if configured
        if config.file_rotation:
            file_handler = logging.handlers.RotatingFileHandler(
                filename=str(file_path),
                maxBytes=config.file_max_bytes,
                backupCount=config.file_backup_count,
            )
        else:
            file_handler = logging.FileHandler(str(file_path))

        file_level = config.file_level or config.level
        file_handler.setLevel(getattr(logging, file_level))

        # Create formatter with appropriate processor
        file_formatter = structlog.stdlib.ProcessorFormatter(
            processor=get_file_processor(config.file_format),
            foreign_pre_chain=shared_processors,
        )
        file_handler.setFormatter(file_formatter)
        handlers.append(file_handler)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.handlers = handlers
    root_logger.setLevel(getattr(logging, config.level))

    # Apply module-specific levels
    for module_name, level_str in config.module_levels.items():
        module_logger = logging.getLogger(module_name)
        module_logger.setLevel(getattr(logging, level_str))

    return _context_enricher


def get_context_enricher() -> Optional[ContextEnricher]:
    """Get the global context enricher instance.

    Returns:
        The context enricher if logging has been set up, None otherwise
    """
    return _context_enricher


def add_global_context(**kwargs):
    """Add context that applies to all subsequent log events.

    Args:
        **kwargs: Key-value pairs to add to all log events

    Example:
        >>> add_global_context(server_id="mcp-youtrack", version="1.0.0")
    """
    if _context_enricher:
        _context_enricher.add_global_context(**kwargs)