#!/usr/bin/env python3
"""
YouTrack MCP Server - A Model Context Protocol server for JetBrains YouTrack.
"""
import argparse
import json
import os
import signal
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict, Any, Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, SecretStr

from youtrack_mcp.config import Config, config
from youtrack_mcp.version import __version__ as APP_VERSION
from youtrack_mcp.logging import get_logger, setup_logging as setup_harmonized_logging

# Optional imports - these are kept as runtime imports due to being optional dependencies
# Try importing nest_asyncio but don't fail if it's not available
try:
    import nest_asyncio
    nest_asyncio.apply()
    # Use temporary logger until harmonized logging is set up
    import logging as temp_logging
    temp_logger = temp_logging.getLogger(__name__)
    temp_logger.info("Successfully applied nest_asyncio")
except ImportError:
    import logging as temp_logging
    temp_logger = temp_logging.getLogger(__name__)
    temp_logger.warning("nest_asyncio not available, event loop nesting may cause issues")

# Global logger instance - will be set up after harmonized logging is configured
logger = None

# Don't load config here - will be done in main() after setting up basic logging
# from youtrack_mcp.server_fastmcp import mcp will be imported after config is loaded

def setup_logging():
    """Set up harmonized logging configuration."""
    global logger

    # Setup the harmonized logging system with the config
    context_enricher = setup_harmonized_logging(config.logging)

    # Get the logger for this module
    logger = get_logger(__name__)

    # Add global context
    if context_enricher:
        context_enricher.add_global_context(
            server_name=config.mcp.server_name,
            version=APP_VERSION
        )

    logger.info("Harmonized logging initialized",
                level=config.logging.level,
                console_enabled=config.logging.console_enabled,
                file_enabled=config.logging.file_enabled)

# Global server and tools instances
server = None
tools = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for FastAPI application."""
    # Server and config are already set up in main() before this runs
    if logger:
        logger.info("HTTP server starting")

    yield

    # Cleanup when the application is shutting down
    if logger:
        logger.info("Shutting down HTTP server")

# FastAPI app for HTTP mode
app = FastAPI(
    title="YouTrack MCP Server",
    description="MCP Server for JetBrains YouTrack",
    version=APP_VERSION,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define request/response models
class ToolRequest(BaseModel):
    name: str = Field(..., description="The name of the tool to execute")
    arguments: Dict[str, Any] = Field(default={}, description="Arguments for the tool")

class ToolResponse(BaseModel):
    result: Any = Field(..., description="Result of the tool execution")

@app.post("/api/tools/{tool_name}")
async def execute_tool(tool_name: str, request: Request):
    """
    Execute a specific tool by name.

    Args:
        tool_name: Name of the tool to execute
        request: The request object containing tool arguments

    Returns:
        Tool execution result
    """
    try:
        # Get tool from registry
        if tool_name not in tools:
            return JSONResponse(
                status_code=404,
                content={"error": f"Tool '{tool_name}' not found"}
            )

        # Parse request body
        body = await request.json()
        arguments = body.get("arguments", {})

        # FastMCP handles schema validation automatically

        # Execute tool (now async)
        logger.info(f"Executing tool: {tool_name} with arguments: {arguments}")
        result = await tools[tool_name](**arguments)

        return {"result": result}
    except Exception as e:
        logger.exception(f"Error executing tool {tool_name}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.get("/api/tools")
async def list_tools():
    """
    List all available tools.
    
    Returns:
        List of available tools with their definitions
    """
    tool_definitions = {}
    
    for name, tool_func in tools.items():
        # Get tool metadata if available
        tool_def = getattr(tool_func, "tool_definition", None)
        if tool_def:
            tool_definitions[name] = tool_def
        else:
            # Basic definition if metadata not available
            tool_definitions[name] = {
                "name": name,
                "description": tool_func.__doc__ or "No description available"
            }
    
    return {"tools": tool_definitions}



def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="YouTrack MCP Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind the server to (HTTP mode only)")
    parser.add_argument(
        "--log-level", 
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level"
    )
    parser.add_argument(
        "--youtrack-url", 
        help="YouTrack instance URL (not required for YouTrack Cloud)"
    )
    parser.add_argument(
        "--api-token", 
        help="YouTrack API token for authentication"
    )
    parser.add_argument(
        "--verify-ssl",
        action="store_true",
        default=None,
        help="Verify SSL certificates (default: True)"
    )
    parser.add_argument(
        "--no-verify-ssl",
        action="store_false",
        dest="verify_ssl",
        help="Disable SSL certificate verification"
    )
    parser.add_argument(
        "--transport",
        choices=["http", "stdio"],
        default="stdio",
        help="Transport mode: 'stdio' for Claude integration (default), 'http' for API server"
    )
    parser.add_argument(
        "--log-file",
        help="Path to log file (enables console + file logging by default)"
    )
    parser.add_argument(
        "--no-console-log",
        action="store_true",
        help="Disable console logging (only log to file if specified)"
    )
    parser.add_argument(
        "--openai-api-key",
        help="OpenAI API key for AI features"
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Display version information and exit"
    )
    
    return parser.parse_args()

def apply_cli_args(args):
    """Apply command line arguments to configuration."""
    # Apply YouTrack configuration
    if args.youtrack_url:
        config.youtrack.url = args.youtrack_url

    if args.api_token:
        config.youtrack.api_token = SecretStr(args.api_token)

    if args.verify_ssl is not None:
        config.youtrack.verify_ssl = args.verify_ssl

    if args.openai_api_key:
        config.llm.api_key = SecretStr(args.openai_api_key)

    # Apply logging configuration
    if hasattr(args, 'log_level') and args.log_level:
        config.logging.level = args.log_level

    if hasattr(args, 'log_file') and args.log_file:
        config.logging.file = Path(args.log_file)

    if hasattr(args, 'no_console_log') and args.no_console_log:
        config.logging.console_disable = True

def handle_signal(signum: int, frame) -> None:
    """
    Handle termination signals.
    
    Args:
        signum: Signal number
        frame: Current stack frame
    """
    logger.info(f"Received signal {signum}, shutting down...")
    
    # Close server gracefully if it exists
    global server
    if server:
        try:
            # FastMCP handles its own cleanup
            pass
        except Exception as e:
            logger.warning(f"Error closing server: {e}")
    
    # Force exit to ensure container stops
    logger.info("Forcing process termination...")
    os._exit(0)

def load_config():
    """Load configuration from environment variables, YAML file, or defaults."""
    # First, try to load from YAML file if specified
    yaml_file = os.getenv("YOUTRACK_CONFIG_FILE", "")
    if not yaml_file:
        # Try configuration file locations in priority order
        possible_files = [
            "./local/youtrack-mcp.yaml",      # Project local config (highest priority)
            "./local/youtrack-mcp.yml",
            os.path.expanduser("~/.config/youtrack-mcp.yaml"),  # User config
            os.path.expanduser("~/.config/youtrack-mcp.yml"),
            "./youtrack-mcp-config.yaml",     # Project root config
            "./config.yaml",
            "./youtrack-mcp.yaml",
            "/etc/youtrack-mcp/config.yaml"   # System config (lowest priority)
        ]
        for possible_file in possible_files:
            if os.path.exists(possible_file):
                yaml_file = possible_file
                break

    if yaml_file:
        config.load_from_yaml(yaml_file)

    # Get token value for validation
    token_value = ""
    try:
        token_value = config.get_api_token()
    except ValueError:
        # Token not configured yet, that's ok
        pass

    # Ensure token is properly formatted for YouTrack Cloud
    if token_value and not token_value.startswith(("perm:", "perm-")):
        # Check if we need to add the perm- prefix
        if "." in token_value and "=" in token_value:
            config.youtrack.api_token = SecretStr(f"perm-{token_value}")
            # Use print here since logger might not be initialized yet
            print("Added 'perm-' prefix to the API token")
        else:
            # For traditional tokens
            config.youtrack.api_token = SecretStr(f"perm:{token_value}")
            print("Added 'perm:' prefix to the API token")

    # URL is already cleaned in the validator, but we can still check env
    env_url = os.getenv("YOUTRACK_URL")
    if env_url and not config.youtrack.url:
        print(f"Using URL from environment: {env_url}")
        config.youtrack.url = env_url.rstrip("/")

    # Store config info to log later after logger is initialized
    config._load_messages = []
    if config.youtrack.url:
        config._load_messages.append(f"Configured for YouTrack instance at: {config.youtrack.url}")
    else:
        config._load_messages.append("Configured for YouTrack Cloud instance")

    config._load_messages.append(f"SSL verification: {'Enabled' if config.youtrack.verify_ssl else 'Disabled'}")


def main():
    """Run the MCP server."""
    args = parse_args()

    # Check if version information was requested
    if args.version:
        print(f"YouTrack MCP Server v{APP_VERSION}")
        sys.exit(0)

    # Load configuration first
    load_config()

    # Apply command line arguments (which may override config)
    apply_cli_args(args)

    # Set up logging BEFORE importing modules that use loggers
    setup_logging()

    # Log the config messages that were saved during load_config()
    if hasattr(config, '_load_messages'):
        for msg in config._load_messages:
            logger.info(msg)

    # Import these AFTER logging is set up
    from youtrack_mcp.server_fastmcp import mcp
    from youtrack_mcp.middleware import TimestampMiddleware

    # Initialize AI tools now that config is loaded
    if config.llm.enabled and config.llm.api_key:
        from youtrack_mcp.tools.ai_tools import AITools
        from youtrack_mcp import server_fastmcp
        server_fastmcp.ai_tools = AITools()
        # Update SearchTools with AI tools
        server_fastmcp.search_tools.ai_tools = server_fastmcp.ai_tools

    # Register MCP tools now that all dependencies are initialized
    from youtrack_mcp.server_fastmcp import register_mcp_tools
    register_mcp_tools()

    # Apply timestamp middleware
    timestamp_middleware = TimestampMiddleware(enable=True)
    timestamp_middleware.apply_to_mcp_server(mcp)
    
    global server
    server = mcp

    # Log which config file was loaded
    if config._config_file_path:
        logger.info(f"Configuration loaded from: {config._config_file_path}")
    else:
        logger.info("No configuration file found, using environment variables and defaults")

    # Log version information
    logger.info(f"Starting YouTrack MCP Server v{APP_VERSION}")
    
    # Register signal handlers
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    
    # Check if running in HTTP mode
    if args.transport == "http":
        logger.info(f"Starting HTTP server on {args.host}")
        import uvicorn
        uvicorn.run(app, host=args.host, port=8000, log_level=args.log_level.lower())
    else:
        # Use the FastMCP server instance (already set as global in main)

        # Tools are already registered in server_fastmcp.py
        # No need to load them again here

        # Run the server directly in stdio mode
        logger.info("Starting in stdio mode for Cursor/Claude integration")
        mcp.run(transport="stdio")

if __name__ == "__main__":
    main()