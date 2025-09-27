"""Log processors for formatting and enriching log output."""

import json
import os
from collections import OrderedDict
from typing import Any, Dict, List, Optional

import structlog
from structlog.dev import ConsoleRenderer, _ColorfulStyles
from structlog.processors import JSONRenderer, KeyValueRenderer


class CustomConsoleRenderer(ConsoleRenderer):
    """Custom console renderer that displays logger name before event."""

    def __call__(self, logger, name, event_dict):
        """Render with logger name before event."""
        # Extract the fields we want to control
        logger_name = event_dict.pop("logger", None)
        event = event_dict.pop("event", "")

        # Temporarily modify event_dict to control ordering
        if logger_name:
            # Find the logger column formatter to get its color style
            logger_style = ""
            reset_style = ""

            for column in self._columns:
                if column.key == "logger":
                    # Extract color codes from the formatter
                    if hasattr(column.formatter, 'value_style'):
                        logger_style = column.formatter.value_style
                        reset_style = column.formatter.reset_style
                    break

            # Create a modified event string that includes styled logger name
            if logger_style:
                colored_logger = f"[{reset_style}{logger_style}{logger_name}{reset_style}]"
            else:
                colored_logger = f"[{logger_name}]"

            modified_event = f"{colored_logger} {event}"
            event_dict["event"] = modified_event

        # Call parent renderer
        result = super().__call__(logger, name, event_dict)

        # Restore original values
        if logger_name:
            event_dict["logger"] = logger_name
        event_dict["event"] = event

        return result


class OrderedJSONRenderer:
    """JSON renderer that preserves field order."""

    def __init__(self, key_order: List[str], indent: Optional[int] = None):
        """Initialize ordered JSON renderer.

        Args:
            key_order: List of keys in desired order (others will follow)
            indent: JSON indentation (None for compact output)
        """
        self.key_order = key_order
        self.indent = indent

    def __call__(self, logger, name, event_dict: Dict[str, Any]) -> str:
        """Render event dict as JSON with ordered fields.

        Args:
            logger: The logger instance
            name: The method name
            event_dict: The event dictionary

        Returns:
            JSON string with ordered fields
        """
        # Create ordered dict with specified key order
        ordered = OrderedDict()

        # First add keys in specified order if they exist
        for key in self.key_order:
            if key in event_dict:
                ordered[key] = event_dict[key]

        # Then add any remaining keys
        for key, value in event_dict.items():
            if key not in ordered:
                ordered[key] = value

        # Convert to JSON
        return json.dumps(ordered, indent=self.indent, default=str)


def get_console_processor(format: str):
    """Get appropriate console output processor.

    Args:
        format: Output format ('color', 'plain', or 'json')

    Returns:
        Configured processor for console output
    """
    if format == "color":
        return CustomConsoleRenderer(
            colors=True,
            pad_event=50,  # Increased to accommodate [logger] prefix
            force_colors=False,
            repr_native_str=False,
        )
    elif format == "json":
        # Use OrderedRenderer for console JSON too
        return OrderedJSONRenderer(
            key_order=["timestamp", "pid", "level", "logger", "event"],
            indent=None
        )
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
        # Use OrderedRenderer to ensure timestamp appears first
        return OrderedJSONRenderer(
            key_order=["timestamp", "pid", "level", "logger", "event"],
            indent=None
        )
    else:  # text
        return KeyValueRenderer(
            key_order=["timestamp", "pid", "level", "logger", "event"],
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


class PIDAdder:
    """Add process ID to log records."""

    def __init__(self):
        """Initialize with current process ID."""
        self.pid = os.getpid()

    def __call__(self, logger, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Add PID to event dict.

        Args:
            logger: The logger instance
            method_name: The logging method called
            event_dict: The event dictionary

        Returns:
            Event dictionary with added PID
        """
        event_dict['pid'] = self.pid
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