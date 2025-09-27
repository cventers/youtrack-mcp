"""Log processors for formatting and enriching log output."""

from typing import Any, Dict, Optional

import structlog
from structlog.dev import ConsoleRenderer
from structlog.processors import JSONRenderer, KeyValueRenderer


def get_console_processor(format: str):
    """Get appropriate console output processor.

    Args:
        format: Output format ('color', 'plain', or 'json')

    Returns:
        Configured processor for console output
    """
    if format == "color":
        return ConsoleRenderer(
            colors=True,
            pad_event=30,
            force_colors=False,
            repr_native_str=False,
        )
    elif format == "json":
        return JSONRenderer(indent=None, sort_keys=False)
    else:  # plain
        return ConsoleRenderer(colors=False)


def get_file_processor(format: str):
    """Get appropriate file output processor.

    Args:
        format: Output format ('json' or 'text')

    Returns:
        Configured processor for file output
    """
    if format == "json":
        return JSONRenderer(indent=None, sort_keys=True)
    else:  # text
        return KeyValueRenderer(
            key_order=["timestamp", "level", "logger", "event"],
            drop_missing=True,
        )


class ContextEnricher:
    """Add contextual information to log records.

    This processor enriches log events with global context and
    MCP-specific information when available.
    """

    def __init__(self):
        """Initialize the context enricher."""
        self.global_context: Dict[str, Any] = {}

    def add_global_context(self, **kwargs):
        """Add context that applies to all logs.

        Args:
            **kwargs: Key-value pairs to add to all log events
        """
        self.global_context.update(kwargs)

    def __call__(self, logger, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Processor to add context to events.

        Args:
            logger: The logger instance
            method_name: The logging method called (info, debug, etc.)
            event_dict: The event dictionary to enrich

        Returns:
            Enriched event dictionary
        """
        # Add global context
        event_dict.update(self.global_context)

        # Add MCP-specific context if available
        if hasattr(logger, '_mcp_context'):
            event_dict['mcp'] = logger._mcp_context

        return event_dict


class ErrorDetailsAdder:
    """Add detailed error information to log records."""

    def __call__(self, logger, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Add exception details if present.

        Args:
            logger: The logger instance
            method_name: The logging method called
            event_dict: The event dictionary

        Returns:
            Event dictionary with added error details
        """
        if 'exc_info' in event_dict and event_dict['exc_info']:
            import sys
            import traceback

            exc_info = event_dict.pop('exc_info')
            if exc_info is True:
                exc_info = sys.exc_info()

            if exc_info and exc_info[0]:
                event_dict['error_type'] = exc_info[0].__name__
                event_dict['error_message'] = str(exc_info[1])
                event_dict['error_traceback'] = ''.join(traceback.format_exception(*exc_info))

        return event_dict