"""
Strict JSON Schema MCP Server for YouTrack.

This module implements a strict JSON schema-based MCP server that replaces
the flexible args/kwargs + repair pattern with canonical tool invocations.
"""

import json
import logging
import inspect
from typing import Dict, List, Any, Optional, Callable

try:
    # Try importing from mcp_sdk (new package name)
    from mcp_sdk.server import ToolServerBase
except ImportError:
    # Fall back to mcp (old package name)
    from mcp.server.fastmcp import FastMCP as ToolServerBase

from youtrack_mcp.config import config
from youtrack_mcp.schemas import (
    TOOL_SCHEMAS,
    get_tool_schema,
    validate_tool_call
)

# Use structlog if available, otherwise fall back to standard logging
try:
    import structlog
    logger = structlog.get_logger(__name__)
except ImportError:
    logger = logging.getLogger(__name__)


class StrictYouTrackMCPServer:
    """
    Strict JSON schema-based MCP server for YouTrack.

    This server enforces canonical tool invocation format:
    {
        "tool_name": "tool.name",
        "arguments": {...}
    }

    No repair logic, no parameter name mapping, strict validation.
    """

    def __init__(self, transport: Optional[str] = None):
        """
        Initialize the strict MCP server.

        Args:
            transport: The transport to use ('http', 'stdio', or None to auto-detect)
        """
        # Auto-detect transport if not specified
        if transport is None:
            import sys
            # Use STDIO when running in a pipe (for Claude integration)
            if not sys.stdin.isatty() or not sys.stdout.isatty():
                transport = "stdio"
            else:
                transport = "http"

        logger.info(f"Initializing strict MCP server with {transport} transport")

        # Store the transport mode
        self.transport_mode = transport

        # Initialize server with ToolServerBase
        self.server = ToolServerBase(
            name=config.MCP_SERVER_NAME,
            instructions=config.MCP_SERVER_DESCRIPTION,
        )

        # Set MCP timeout from environment if specified
        if hasattr(config, 'MCP_TIMEOUT') and config.MCP_TIMEOUT:
            self._mcp_timeout = config.MCP_TIMEOUT / 1000.0
            logger.info(f"MCP timeout set to {self._mcp_timeout}s")
        else:
            self._mcp_timeout = 15.0

        # Initialize tool registry
        self._tools: Dict[str, Callable] = {}
        self._registered_tools = set()

        # Register MCP Resources
        self._register_resources()

    def _register_resources(self) -> None:
        """Register MCP Resources with the server."""
        try:
            from youtrack_mcp.mcp_resources import (
                handle_query_syntax_resource,
                handle_project_fields_resource,
                handle_projects_list_resource,
                handle_users_directory_resource
            )

            @self.server.resource("youtrack://query-syntax",
                                name="YouTrack Query Syntax Guide",
                                description="Complete reference for YouTrack Query Language (YQL) syntax")
            async def query_syntax_handler():
                return await handle_query_syntax_resource()

            @self.server.resource("youtrack://projects",
                                name="YouTrack Projects List",
                                description="List of all available projects with metadata")
            async def projects_list_handler():
                return await handle_projects_list_resource()

            @self.server.resource("youtrack://users",
                                name="YouTrack Users Directory",
                                description="Directory of all users with login names and metadata")
            async def users_directory_handler():
                return await handle_users_directory_resource()

            @self.server.resource("youtrack://project/{project_id}/fields",
                                name="Project Custom Fields",
                                description="Available custom fields for a specific project")
            async def project_fields_handler(project_id: str):
                return await handle_project_fields_resource(project_id)

            logger.info("Registered 4 MCP Resources with strict server")

        except Exception as e:
            logger.warning(f"Failed to register MCP Resources: {e}")

    def register_strict_tool(
        self,
        name: str,
        func: Callable,
        description: str,
    ) -> None:
        """
        Register a tool with strict JSON schema validation.

        Args:
            name: The tool name (e.g., "issues.get")
            func: The tool function
            description: Description of what the tool does
        """
        if name in self._registered_tools:
            logger.debug(f"Tool {name} already registered, skipping")
            return

        self._registered_tools.add(name)

        # Get the schema for this tool
        try:
            schema = get_tool_schema(name)
        except ValueError as e:
            logger.error(f"Failed to get schema for tool {name}: {e}")
            return

        # Create strict wrapper that validates input
        strict_wrapper = self._create_strict_wrapper(func, name, schema)
        # Set tool name for parameter processing
        strict_wrapper._tool_name = name

        # Register with MCP server using the schema
        self.server.add_tool(
            name=name,
            description=description,
            fn=strict_wrapper
        )

        logger.debug(f"Registered strict tool: {name}")

    def _create_strict_wrapper(
        self,
        func: Callable,
        name: str,
        schema: Dict[str, Any]
    ) -> Callable:
        """
        Create a strict wrapper that validates input against JSON schema.

        Args:
            func: The original tool function
            name: The tool name
            schema: The JSON schema for validation

        Returns:
            A wrapper function with strict validation
        """
        is_async = inspect.iscoroutinefunction(func)

        async def strict_async_wrapper(**kwargs) -> str:
            """Strict async wrapper with JSON schema validation."""
            try:
                # Validate the tool call
                validate_tool_call(name, kwargs)

                # Call the function with validated arguments
                if is_async:
                    result = await func(**kwargs)
                else:
                    # Run sync function in executor
                    import asyncio
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(None, lambda: func(**kwargs))

                # Ensure result is JSON string
                if not isinstance(result, str):
                    result = json.dumps(result)

                return result

            except ValueError as e:
                # Schema validation error
                error_msg = f"Tool call validation failed for {name}: {str(e)}"
                logger.warning(error_msg)
                return json.dumps({
                    "error": error_msg,
                    "tool": name,
                    "status": "validation_error"
                })

            except Exception as e:
                logger.exception(f"Error executing strict tool {name}")
                return json.dumps({
                    "error": f"Error executing {name}: {str(e)}",
                    "tool": name,
                    "status": "error"
                })

        def strict_sync_wrapper(**kwargs) -> str:
            """Strict sync wrapper with JSON schema validation."""
            try:
                # Validate the tool call
                validate_tool_call(name, kwargs)

                # Call the function with validated arguments
                result = func(**kwargs)

                # Ensure result is JSON string
                if not isinstance(result, str):
                    result = json.dumps(result)

                return result

            except ValueError as e:
                # Schema validation error
                error_msg = f"Tool call validation failed for {name}: {str(e)}"
                logger.warning(error_msg)
                return json.dumps({
                    "error": error_msg,
                    "tool": name,
                    "status": "validation_error"
                })

            except Exception as e:
                logger.exception(f"Error executing strict tool {name}")
                return json.dumps({
                    "error": f"Error executing {name}: {str(e)}",
                    "tool": name,
                    "status": "error"
                })

        # Return appropriate wrapper
        if self.transport_mode == "http":
            return strict_async_wrapper
        else:
            return strict_sync_wrapper if not is_async else strict_async_wrapper

    def register_tools_from_loader(self, loaded_tools: Dict[str, Callable]) -> None:
        """
        Register tools from the loader with strict validation.

        Args:
            loaded_tools: Dictionary mapping tool names to functions
        """
        for name, func in loaded_tools.items():
            # Get description from function docstring
            description = func.__doc__ or f"Tool {name}"
            description = description.strip().split("\n")[0]

            # Register with strict validation
            self.register_strict_tool(
                name=name,
                func=func,
                description=description
            )

        logger.info(f"Registered {len(loaded_tools)} tools with strict validation")

    def run(self) -> None:
        """Run the strict MCP server."""
        logger.info(f"Starting strict YouTrack MCP server with {self.transport_mode} transport")

        if self.transport_mode == "stdio":
            import asyncio
            import sys

            # Ensure stdout is unbuffered for fast handshake
            try:
                if hasattr(sys.stdout, 'reconfigure'):
                    sys.stdout.reconfigure(line_buffering=True)
            except (AttributeError, OSError):
                pass

            asyncio.run(self._run_stdio_async())
        else:
            # HTTP mode
            self.server.run()

    async def _run_stdio_async(self) -> None:
        """Run stdio server with fast handshake."""
        await self.server.run_stdio_async()

    def stop(self) -> None:
        """Stop the strict MCP server."""
        logger.info("Stopping strict YouTrack MCP server")


__all__ = [
    "StrictYouTrackMCPServer"
]