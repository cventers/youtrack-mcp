"""
Timestamp middleware for adding ISO8601 formatted timestamps to tool responses.

This middleware automatically applies format_json_response() to all tool outputs,
ensuring that YouTrack's millisecond epoch timestamps are augmented with
human-readable ISO8601 formatted timestamps.
"""

import json
import logging
from typing import Any, Callable, Dict, Union
from functools import wraps

from youtrack_mcp.utils import add_iso8601_timestamps
from youtrack_mcp.config import config

logger = logging.getLogger(__name__)


class TimestampMiddleware:
    """
    Middleware that adds ISO8601 timestamps to all tool responses.

    This restores the timestamp conversion functionality that was present
    in the upstream version but got removed during refactoring.
    """

    def __init__(self, enable: bool = True):
        """
        Initialize the timestamp middleware.

        Args:
            enable: Whether to enable timestamp conversion (default: True)
        """
        self.enabled = enable
        # Get compatibility setting from config
        self.include_numeric = config.compat.include_numeric_date
    
    def wrap_tool(self, tool_func: Callable) -> Callable:
        """
        Wrap a tool function to add ISO8601 timestamps to its output.
        
        Args:
            tool_func: The tool function to wrap
            
        Returns:
            Wrapped function that adds timestamps to the output
        """
        @wraps(tool_func)
        async def wrapper(*args, **kwargs):
            # Execute the original tool
            result = await tool_func(*args, **kwargs)
            
            # If middleware is disabled, return original result
            if not self.enabled:
                return result
            
            # Apply timestamp conversion with compatibility mode
            try:
                enhanced_result = add_iso8601_timestamps(result, self.include_numeric)

                # Log if we actually added any timestamps
                if self._has_timestamp_changes(result, enhanced_result):
                    mode = "legacy" if self.include_numeric else "modern"
                    logger.debug(f"Applied {mode} timestamp format to {tool_func.__name__} output")

                return enhanced_result
                
            except Exception as e:
                # If timestamp conversion fails, log and return original
                logger.warning(f"Failed to add timestamps to {tool_func.__name__} output: {e}")
                return result
        
        return wrapper
    
    def _has_timestamp_changes(self, original: Any, enhanced: Any) -> bool:
        """
        Check if timestamp conversion actually added or modified any fields.

        Args:
            original: Original data
            enhanced: Enhanced data with potential timestamps

        Returns:
            True if timestamps were added or modified
        """
        try:
            # Quick check for dict types
            if isinstance(original, dict) and isinstance(enhanced, dict):
                if self.include_numeric:
                    # In legacy mode, check if any _iso8601 fields were added
                    for key in enhanced:
                        if key.endswith('_iso8601') and key not in original:
                            return True
                else:
                    # In modern mode, check if numeric timestamps were replaced
                    for key in ['created', 'updated']:
                        if key in original and key in enhanced:
                            # Check if value changed from int to string
                            if isinstance(original[key], int) and isinstance(enhanced[key], str):
                                return True

            # For complex nested structures, serialize and compare
            original_json = json.dumps(original, sort_keys=True, default=str)
            enhanced_json = json.dumps(enhanced, sort_keys=True, default=str)

            return original_json != enhanced_json

        except Exception:
            # If comparison fails, assume changes were made
            return True
    
    def apply_to_mcp_server(self, mcp_server):
        """
        Apply timestamp middleware to all tools in a FastMCP server.

        Args:
            mcp_server: The FastMCP server instance
        """
        if not self.enabled:
            logger.info("TimestampMiddleware is disabled, skipping tool wrapping")
            return

        # FastMCP stores tools in _tool_manager._tools
        if hasattr(mcp_server, '_tool_manager') and hasattr(mcp_server._tool_manager, '_tools'):
            wrapped_count = 0
            tools_dict = mcp_server._tool_manager._tools

            for tool_name in list(tools_dict.keys()):
                tool_info = tools_dict[tool_name]

                # Wrap the handler function
                if 'handler' in tool_info:
                    original_handler = tool_info['handler']
                    tool_info['handler'] = self.wrap_tool(original_handler)
                    wrapped_count += 1

            logger.info(f"Applied TimestampMiddleware to {wrapped_count} tools")
        else:
            raise AttributeError("MCP server doesn't have _tool_manager._tools attribute, cannot apply middleware")


# Global instance for convenience
timestamp_middleware = TimestampMiddleware()


def apply_timestamp_middleware(mcp_server, enable: bool = True):
    """
    Convenience function to apply timestamp middleware to an MCP server.
    
    Args:
        mcp_server: The FastMCP server instance
        enable: Whether to enable the middleware
    """
    middleware = TimestampMiddleware(enable=enable)
    middleware.apply_to_mcp_server(mcp_server)
    return middleware