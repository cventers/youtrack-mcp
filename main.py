#!/usr/bin/env python3
"""
YouTrack MCP Server - A Model Context Protocol server for JetBrains YouTrack.
"""
import argparse
import logging
import os
import signal
import sys
from typing import Dict, Any, Optional
import json
from contextlib import asynccontextmanager

# Try importing nest_asyncio but don't fail if it's not available
try:
    import nest_asyncio
    nest_asyncio.apply()
    logger = logging.getLogger(__name__)
    logger.info("Successfully applied nest_asyncio")
except ImportError:
    logger = logging.getLogger(__name__)
    logger.warning("nest_asyncio not available, event loop nesting may cause issues")

# App version - now imported from version.py to ensure consistency
from youtrack_mcp.version import __version__ as APP_VERSION


from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from youtrack_mcp.config import Config, config
from youtrack_mcp.server import YouTrackMCPServer
from youtrack_mcp.utils.loader import load_all_tools

# Check if structlog is available
structlog_available = False
try:
    import structlog
    structlog_available = True
except ImportError:
    pass

# Global logger instance (will be initialized after config is loaded)
logger = logging.getLogger(__name__)

def setup_logging():
    """Set up logging configuration based on config values."""
    global logger

    # Get logging configuration from environment variables (with config fallback)
    log_level = os.getenv('LOG_LEVEL', getattr(config, 'LOG_LEVEL', 'INFO'))
    log_file = os.getenv('LOG_FILE', getattr(config, 'LOG_FILE', None))
    console_disabled = os.getenv('LOG_CONSOLE_DISABLE', 'false').lower() in ('true', '1', 'yes') or getattr(config, 'LOG_CONSOLE_DISABLE', False)

    # Convert log level string to logging level
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Set up handlers
    handlers = []

    # Add console handler unless disabled
    if not console_disabled:
        console_handler = logging.StreamHandler()
        if structlog_available:
            console_handler.setFormatter(logging.Formatter("%(message)s"))
        else:
            console_handler.setFormatter(logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            ))
        handlers.append(console_handler)

    # Add file handler if log file is specified
    if log_file:
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            file_handler = logging.FileHandler(log_file)
            if structlog_available:
                file_handler.setFormatter(logging.Formatter("%(message)s"))
            else:
                file_handler.setFormatter(logging.Formatter(
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                ))
            handlers.append(file_handler)
        except (OSError, IOError) as e:
            # If we can't create the log file, log to console only
            if not console_disabled:
                print(f"Warning: Could not create log file {log_file}: {e}")

    # Configure logging
    if structlog_available:
        try:
            # Import structlog here to avoid linter issues
            import structlog
            # Configure structlog for JSON output
            structlog.configure(
                processors=[
                    structlog.stdlib.filter_by_level,
                    structlog.stdlib.add_logger_name,
                    structlog.stdlib.add_log_level,
                    structlog.stdlib.PositionalArgumentsFormatter(),
                    structlog.processors.TimeStamper(fmt="iso"),
                    structlog.processors.StackInfoRenderer(),
                    structlog.processors.format_exc_info,
                    structlog.processors.UnicodeDecoder(),
                    structlog.processors.JSONRenderer()
                ],
                context_class=dict,
                logger_factory=structlog.stdlib.LoggerFactory(),
                wrapper_class=structlog.stdlib.BoundLogger,
                cache_logger_on_first_use=True,
            )

            # Replace standard logging with structlog
            logging.basicConfig(
                format="%(message)s",
                level=numeric_level,
                handlers=handlers
            )

            logger = structlog.get_logger(__name__)
            logger.info("Structured JSON logging enabled")
        except Exception as e:
            # If structlog setup fails, fall back to standard logging
            logging.basicConfig(
                level=numeric_level,
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                handlers=handlers
            )
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to set up structlog: {e}, using standard logging")
    else:
        # Fallback to standard logging if structlog is not available
        logging.basicConfig(
            level=numeric_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=handlers
        )
        logger = logging.getLogger(__name__)
        logger.warning("structlog not available, using standard logging")

# Global server and tools instances
server = None
tools = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for FastAPI application."""
    global tools, server

    # Load configuration
    load_config()

    # Initialize httpx client for the application
    import httpx
    async with httpx.AsyncClient() as http_client:
        # Store client in app state for use by tools
        app.state.http_client = http_client

        # Initialize MCP server with HTTP transport
        server = YouTrackMCPServer(transport="http")

        # Load all tools
        all_tools = load_all_tools()
        tools = all_tools

        # Register the tools with the server
        server.register_loaded_tools(all_tools)

        logger.info(f"HTTP server started with {len(all_tools)} tools")

        yield

        # Cleanup when the application is shutting down
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
                logger.info(f"Found configuration file: {yaml_file}")
                break

    if yaml_file:
        try:
            logger.info(f"Loading configuration from YAML file: {yaml_file}")
            config.load_from_yaml(yaml_file)
        except Exception as e:
            logger.warning(f"Failed to load YAML configuration from {yaml_file}: {e}")
            logger.info("Falling back to environment variables and defaults")

    # Environment variables have higher priority than config file
    env_config = {}

    # Extract config variables from environment
    for key in dir(Config):
        if key.isupper() and not key.startswith("_"):
            env_key = f"YOUTRACK_MCP_{key}"
            if env_key in os.environ:
                env_value = os.environ[env_key]
                # Convert string booleans to actual booleans
                if env_value.lower() in ("true", "false"):
                    env_value = env_value.lower() == "true"
                env_config[key] = env_value

    # Create config instance from environment variables
    if env_config:
        logger.info("Loading configuration from environment variables")
        Config.from_dict(env_config)

    # Ensure token is properly formatted for YouTrack Cloud
    if config.YOUTRACK_API_TOKEN and not config.YOUTRACK_API_TOKEN.startswith(("perm:", "perm-")):
        # Check if we need to add the perm- prefix
        if "." in config.YOUTRACK_API_TOKEN and "=" in config.YOUTRACK_API_TOKEN:
            config.YOUTRACK_API_TOKEN = f"perm-{config.YOUTRACK_API_TOKEN}"
            logger.info("Added 'perm-' prefix to the API token")
        else:
            # For traditional tokens
            config.YOUTRACK_API_TOKEN = f"perm:{config.YOUTRACK_API_TOKEN}"
            logger.info("Added 'perm:' prefix to the API token")
    
    # Force YouTrack URL to be properly formatted
    if config.YOUTRACK_URL and config.YOUTRACK_URL.endswith("/"):
        config.YOUTRACK_URL = config.YOUTRACK_URL.rstrip("/")
        logger.info("Removed trailing slash from YouTrack URL")
    
    # Initialize configuration from environment variables
    config.validate()
    
    # Use environment variable for URL if specified instead of auto-detection
    env_url = os.getenv("YOUTRACK_URL")
    if env_url and not config.YOUTRACK_URL:
        logger.info(f"Using URL from environment: {env_url}")
        config.YOUTRACK_URL = env_url
    
    # Log configuration status
    if config.YOUTRACK_URL:
        logger.info(f"Configured for YouTrack instance at: {config.YOUTRACK_URL}")
    else:
        logger.info("Configured for YouTrack Cloud instance")
    
    logger.info(f"SSL verification: {'Enabled' if config.VERIFY_SSL else 'Disabled'}")

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
    config_dict = {}

    if args.youtrack_url:
        config_dict["YOUTRACK_URL"] = args.youtrack_url

    if args.api_token:
        config_dict["YOUTRACK_API_TOKEN"] = args.api_token

    if args.verify_ssl is not None:
        config_dict["VERIFY_SSL"] = args.verify_ssl

    if args.openai_api_key:
        config_dict["OPENAI_API_KEY"] = args.openai_api_key

    # Apply logging configuration
    if hasattr(args, 'log_level') and args.log_level:
        config_dict["LOG_LEVEL"] = args.log_level

    if hasattr(args, 'log_file') and args.log_file:
        config_dict["LOG_FILE"] = args.log_file

    if hasattr(args, 'no_console_log') and args.no_console_log:
        config_dict["LOG_CONSOLE_DISABLE"] = True

    if config_dict:
        config.from_dict(config_dict)

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
            server.close()
        except Exception as e:
            logger.warning(f"Error closing server: {e}")
    
    # Force exit to ensure container stops
    logger.info("Forcing process termination...")
    os._exit(0)

def main():
    """Run the MCP server."""
    args = parse_args()
    
    # Check if version information was requested
    if args.version:
        print(f"YouTrack MCP Server v{APP_VERSION}")
        sys.exit(0)
    
    # Apply command line arguments
    apply_cli_args(args)

    # Load configuration
    load_config()

    # Set up logging based on configuration
    setup_logging()

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
        # Initialize MCP server with stdio transport
        global server
        server = YouTrackMCPServer(transport="stdio")
        
        # Load all tools just once
        all_tools = load_all_tools()
        
        # Register the tools with the server
        server.register_loaded_tools(all_tools)
        
        # Run the server directly in stdio mode
        logger.info("Starting in stdio mode for Cursor/Claude integration")
        server.run()

if __name__ == "__main__":
    main()