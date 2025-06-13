#!/usr/bin/env python3
"""
YouTrack MCP Server - Consolidated Standard SDK Implementation
A Model Context Protocol server for JetBrains YouTrack using the standard MCP Python SDK.
Supports both stdio and HTTP transports with configurable binding.
"""
import argparse
import asyncio
import logging
import os
import sys
from typing import Any, Dict, List, Optional

# Standard MCP SDK imports
from mcp.server.fastmcp import FastMCP
from mcp.server.stdio import stdio_server

# YouTrack API clients
from youtrack_mcp.api.client import YouTrackClient
from youtrack_mcp.api.issues import IssuesClient
from youtrack_mcp.api.projects import ProjectsClient
from youtrack_mcp.api.users import UsersClient
from youtrack_mcp.api.search import SearchClient
from youtrack_mcp.config import Config, config
from youtrack_mcp.utils import convert_timestamp_to_iso8601, add_iso8601_timestamps

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# App version
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")

# Initialize the MCP server
mcp = FastMCP("YouTrack MCP")

# Global API clients - initialized after config load
youtrack_client: Optional[YouTrackClient] = None
issues_api: Optional[IssuesClient] = None
projects_api: Optional[ProjectsClient] = None
users_api: Optional[UsersClient] = None
search_api: Optional[SearchClient] = None


def load_config():
    """Load configuration from environment variables."""
    logger.info("Loading configuration from environment variables")
    
    # Load from environment variables
    if os.getenv("YOUTRACK_URL"):
        config.YOUTRACK_URL = os.getenv("YOUTRACK_URL")
    
    if os.getenv("YOUTRACK_TOKEN_FILE"):
        token_file = os.getenv("YOUTRACK_TOKEN_FILE")
        if os.path.exists(token_file):
            with open(token_file, 'r') as f:
                config.YOUTRACK_API_TOKEN = f.read().strip()
            logger.info(f"Loaded API token from file: {token_file}")
    elif os.getenv("YOUTRACK_TOKEN"):
        config.YOUTRACK_API_TOKEN = os.getenv("YOUTRACK_TOKEN")
    
    config.YOUTRACK_CLOUD = os.getenv("YOUTRACK_CLOUD", "true").lower() == "true"
    config.VERIFY_SSL = os.getenv("YOUTRACK_VERIFY_SSL", "true").lower() == "true"
    
    # Validate configuration
    config.validate()
    
    logger.info(f"Configured for YouTrack at: {config.YOUTRACK_URL}")
    logger.info(f"SSL verification: {'Enabled' if config.VERIFY_SSL else 'Disabled'}")


def initialize_clients():
    """Initialize API clients."""
    global youtrack_client, issues_api, projects_api, users_api, search_api
    
    youtrack_client = YouTrackClient()
    issues_api = IssuesClient(youtrack_client)
    projects_api = ProjectsClient(youtrack_client)
    users_api = UsersClient(youtrack_client)
    search_api = SearchClient(youtrack_client)
    
    logger.info("API clients initialized")


# Issue Tools
@mcp.tool()
def get_issue(issue_id: str) -> Dict[str, Any]:
    """
    Get information about a specific issue.
    
    Args:
        issue_id: The issue ID or readable ID (e.g., PROJECT-123)
        
    Returns:
        Issue information
    """
    try:
        fields = "id,idReadable,summary,description,created,updated,project(id,name,shortName),reporter(id,login,name),assignee(id,login,name),customFields(id,name,value(id,name,$type))"
        raw_issue = youtrack_client.get(f"issues/{issue_id}?fields={fields}")
        
        # Enhance with ISO8601 timestamps
        raw_issue = add_iso8601_timestamps(raw_issue)
        
        return raw_issue
        
    except Exception as e:
        logger.exception(f"Error getting issue {issue_id}")
        return {"error": str(e)}


@mcp.tool()
def create_issue(project: str, summary: str, description: str = None) -> Dict[str, Any]:
    """
    Create a new issue in YouTrack.
    
    Args:
        project: Project key or ID
        summary: Issue summary/title
        description: Issue description (optional)
        
    Returns:
        Created issue information
    """
    try:
        issue_data = {
            "project": {"shortName": project},
            "summary": summary
        }
        
        if description:
            issue_data["description"] = description
        
        result = youtrack_client.post("issues", data=issue_data)
        return result
        
    except Exception as e:
        logger.exception(f"Error creating issue in project {project}")
        return {"error": str(e)}


@mcp.tool()
def search_issues(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Search for issues using YouTrack query language.
    
    Args:
        query: YouTrack search query
        limit: Maximum number of results (default: 10)
        
    Returns:
        List of matching issues
    """
    try:
        fields = "id,idReadable,summary,description,created,updated,project(id,name,shortName),reporter(id,login,name),customFields(id,name,value(id,name,$type))"
        params = {
            "query": query,
            "fields": fields,
            "$top": limit
        }
        
        results = youtrack_client.get("issues", params=params)
        
        # Enhance with ISO8601 timestamps
        results = add_iso8601_timestamps(results)
        
        return results if isinstance(results, list) else []
        
    except Exception as e:
        logger.exception(f"Error searching issues with query: {query}")
        return [{"error": str(e)}]


@mcp.tool()
def add_comment(issue_id: str, text: str) -> Dict[str, Any]:
    """
    Add a comment to an issue.
    
    Args:
        issue_id: The issue ID or readable ID
        text: Comment text
        
    Returns:
        Comment creation result
    """
    try:
        comment_data = {"text": text}
        result = youtrack_client.post(f"issues/{issue_id}/comments", data=comment_data)
        return {"status": "success", "result": result}
        
    except Exception as e:
        logger.exception(f"Error adding comment to issue {issue_id}")
        return {"error": str(e)}


@mcp.tool()
def update_issue(issue_id: str, assignee: str = None, priority: str = None, 
                state: str = None, type: str = None) -> Dict[str, Any]:
    """
    Update issue fields using YouTrack commands.
    
    Args:
        issue_id: The issue ID or readable ID
        assignee: Username to assign to (optional)
        priority: Priority level (optional)
        state: Issue state (optional)
        type: Issue type (optional)
        
    Returns:
        Update result
    """
    try:
        command_parts = []
        
        if assignee:
            if assignee.lower() in ['unassigned', 'none', '']:
                command_parts.append("for Unassigned")
            else:
                command_parts.append(f"for {assignee}")
        
        if priority:
            command_parts.append(f"Priority {priority}")
        
        if state:
            command_parts.append(f"State {state}")
            
        if type:
            command_parts.append(f"Type {type}")
        
        if not command_parts:
            return {"error": "No valid field updates provided"}
        
        query = " ".join(command_parts)
        command_data = {
            "query": query,
            "issues": [{"idReadable": issue_id}]
        }
        
        result = youtrack_client.post("commands", data=command_data)
        return {"status": "success", "message": f"Successfully updated issue {issue_id}", "result": result}
        
    except Exception as e:
        logger.exception(f"Error updating issue {issue_id}")
        return {"error": str(e)}


@mcp.tool()
def link_issues(source_issue_id: str, target_issue_id: str, link_type: str = "relates to") -> Dict[str, Any]:
    """
    Link two issues together using a specified link type.
    
    Args:
        source_issue_id: The ID of the issue that will have the link applied to it
        target_issue_id: The ID of the issue to link to
        link_type: The type of link (default: "relates to")
        
    Returns:
        Link creation result
    """
    try:
        command_data = {
            "query": f"{link_type} {target_issue_id}",
            "issues": [{"idReadable": source_issue_id}]
        }
        
        result = youtrack_client.post("commands", data=command_data)
        return {
            "status": "success",
            "message": f"Successfully linked {source_issue_id} to {target_issue_id} with link type '{link_type}'",
            "result": result
        }
        
    except Exception as e:
        logger.exception(f"Error linking issues {source_issue_id} -> {target_issue_id}")
        return {"error": str(e)}


@mcp.tool()
def remove_link(source_issue_id: str, target_issue_id: str, link_type: str = "relates to") -> Dict[str, Any]:
    """
    Remove a link between two issues.
    
    Args:
        source_issue_id: The issue that will have the link removed from it
        target_issue_id: The issue to unlink from
        link_type: The type of link to remove (default: "relates to")
        
    Returns:
        Link removal result
    """
    try:
        command_data = {
            "query": f"remove {link_type} {target_issue_id}",
            "issues": [{"idReadable": source_issue_id}]
        }
        
        result = youtrack_client.post("commands", data=command_data)
        return {
            "status": "success", 
            "message": f"Successfully removed {link_type} link from {source_issue_id} to {target_issue_id}",
            "result": result
        }
        
    except Exception as e:
        logger.exception(f"Error removing link {source_issue_id} -> {target_issue_id}")
        return {"error": str(e)}


@mcp.tool()
def create_dependency(dependent_issue_id: str, dependency_issue_id: str) -> Dict[str, Any]:
    """
    Create a dependency relationship where one issue depends on another.
    
    Args:
        dependent_issue_id: The issue that depends on another
        dependency_issue_id: The issue that is required
        
    Returns:
        Dependency creation result
    """
    return link_issues(dependent_issue_id, dependency_issue_id, "depends on")


@mcp.tool()
def get_issue_links(issue_id: str) -> List[Dict[str, Any]]:
    """
    Get all links for a specific issue.
    
    Args:
        issue_id: The issue ID or readable ID
        
    Returns:
        List of issue links
    """
    try:
        fields = "id,direction,linkType(id,name,directed),issues(id,idReadable,summary,project(id,name,shortName))"
        params = {"fields": fields}
        
        links = youtrack_client.get(f"issues/{issue_id}/links", params=params)
        return links if isinstance(links, list) else []
        
    except Exception as e:
        logger.exception(f"Error getting links for issue {issue_id}")
        return [{"error": str(e)}]


@mcp.tool()
def get_available_link_types() -> List[Dict[str, Any]]:
    """
    Get available issue link types from YouTrack.
    
    Returns:
        List of available link types
    """
    try:
        fields = "id,name,directed,sourceToTarget,targetToSource,aggregation,readOnly"
        params = {"fields": fields}
        link_types = youtrack_client.get("issueLinkTypes", params=params)
        return link_types if isinstance(link_types, list) else []
        
    except Exception as e:
        logger.exception("Error getting available link types")
        return [{"error": str(e)}]


# Project Tools
@mcp.tool()
def get_projects(include_archived: bool = False) -> List[Dict[str, Any]]:
    """
    Get a list of all projects.
    
    Args:
        include_archived: Include archived projects (default: False)
        
    Returns:
        List of projects
    """
    try:
        fields = "id,name,shortName,description,archived"
        params = {"fields": fields}
        
        projects = youtrack_client.get("admin/projects", params=params)
        
        if not include_archived and isinstance(projects, list):
            projects = [p for p in projects if not p.get("archived", False)]
        
        return projects if isinstance(projects, list) else []
        
    except Exception as e:
        logger.exception("Error getting projects")
        return [{"error": str(e)}]


@mcp.tool()
def get_project(project: str) -> Dict[str, Any]:
    """
    Get information about a specific project.
    
    Args:
        project: Project short name or ID
        
    Returns:
        Project information
    """
    try:
        fields = "id,name,shortName,description,archived,leader(id,login,name)"
        result = youtrack_client.get(f"admin/projects/{project}?fields={fields}")
        return result
        
    except Exception as e:
        logger.exception(f"Error getting project {project}")
        return {"error": str(e)}


# User Tools
@mcp.tool()
def get_current_user() -> Dict[str, Any]:
    """
    Get information about the currently authenticated user.
    
    Returns:
        Current user information
    """
    try:
        fields = "id,login,name,email,guest,online,banned"
        result = youtrack_client.get(f"users/me?fields={fields}")
        return result
        
    except Exception as e:
        logger.exception("Error getting current user")
        return {"error": str(e)}


@mcp.tool()
def search_users(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Search for users using YouTrack query.
    
    Args:
        query: User search query
        limit: Maximum number of results (default: 10)
        
    Returns:
        List of matching users
    """
    try:
        fields = "id,login,name,email,guest,online,banned"
        params = {
            "query": query,
            "fields": fields,
            "$top": limit
        }
        
        results = youtrack_client.get("users", params=params)
        return results if isinstance(results, list) else []
        
    except Exception as e:
        logger.exception(f"Error searching users with query: {query}")
        return [{"error": str(e)}]


@mcp.tool()
def get_user_by_login(login: str) -> Dict[str, Any]:
    """
    Get a user by their login name.
    
    Args:
        login: User login name
        
    Returns:
        User information
    """
    try:
        fields = "id,login,name,email,guest,online,banned,ringId"
        result = youtrack_client.get(f"users/{login}?fields={fields}")
        return result
        
    except Exception as e:
        logger.exception(f"Error getting user by login {login}")
        return {"error": str(e)}


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="YouTrack MCP Server (Consolidated)")
    
    # Transport options
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="Transport mode: 'stdio' for Claude integration (default), 'http' for API server"
    )
    
    # HTTP server options
    parser.add_argument(
        "--host",
        default=os.getenv("YOUTRACK_MCP_HOST", "127.0.0.2"),
        help="Host to bind HTTP server to (default: 127.0.0.2, env: YOUTRACK_MCP_HOST)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("YOUTRACK_MCP_PORT", "8000")),
        help="Port to bind HTTP server to (default: 8000, env: YOUTRACK_MCP_PORT)"
    )
    
    # YouTrack configuration
    parser.add_argument(
        "--youtrack-url",
        default=os.getenv("YOUTRACK_URL"),
        help="YouTrack instance URL (env: YOUTRACK_URL)"
    )
    parser.add_argument(
        "--youtrack-token",
        default=os.getenv("YOUTRACK_TOKEN"),
        help="YouTrack API token (env: YOUTRACK_TOKEN)"
    )
    parser.add_argument(
        "--youtrack-token-file",
        default=os.getenv("YOUTRACK_TOKEN_FILE"),
        help="Path to file containing YouTrack API token (env: YOUTRACK_TOKEN_FILE)"
    )
    
    # Logging
    parser.add_argument(
        "--log-level",
        default=os.getenv("LOG_LEVEL", "INFO"),
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level (default: INFO, env: LOG_LEVEL)"
    )
    
    # SSL verification
    parser.add_argument(
        "--verify-ssl",
        action="store_true",
        default=None,
        help="Verify SSL certificates"
    )
    parser.add_argument(
        "--no-verify-ssl",
        action="store_false",
        dest="verify_ssl",
        help="Disable SSL certificate verification"
    )
    
    # Version
    parser.add_argument(
        "--version",
        action="store_true",
        help="Display version information and exit"
    )
    
    return parser.parse_args()


def apply_cli_config(args):
    """Apply CLI arguments to configuration."""
    # Set log level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Apply YouTrack configuration from CLI args
    if args.youtrack_url:
        config.YOUTRACK_URL = args.youtrack_url
    
    if args.youtrack_token:
        config.YOUTRACK_API_TOKEN = args.youtrack_token
    
    if args.youtrack_token_file and os.path.exists(args.youtrack_token_file):
        with open(args.youtrack_token_file, 'r') as f:
            config.YOUTRACK_API_TOKEN = f.read().strip()
        logger.info(f"Loaded API token from file: {args.youtrack_token_file}")
    
    if args.verify_ssl is not None:
        config.VERIFY_SSL = args.verify_ssl


async def run_http_server(host: str, port: int):
    """Run HTTP server using FastMCP's built-in HTTP support."""
    logger.info(f"Starting HTTP server on {host}:{port}")
    logger.info("HTTP mode - tools available via REST API")
    
    # FastMCP should handle HTTP server creation
    # This is a placeholder - actual implementation depends on FastMCP's HTTP capabilities
    from fastapi import FastAPI
    import uvicorn
    
    # Create FastAPI app
    app = FastAPI(
        title="YouTrack MCP Server",
        description="MCP Server for JetBrains YouTrack",
        version=APP_VERSION
    )
    
    # Add CORS
    from fastapi.middleware.cors import CORSMiddleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Mount MCP endpoints (this would need FastMCP HTTP integration)
    logger.warning("HTTP server setup - FastMCP HTTP integration needed")
    
    # Run server
    await uvicorn.run(app, host=host, port=port, log_level="info")


def main():
    """Main entry point."""
    args = parse_args()
    
    # Version check
    if args.version:
        print(f"YouTrack MCP Server (Consolidated) v{APP_VERSION}")
        sys.exit(0)
    
    # Apply CLI configuration
    apply_cli_config(args)
    
    # Load configuration
    load_config()
    
    # Initialize API clients
    initialize_clients()
    
    logger.info(f"Starting YouTrack MCP Server (Consolidated) v{APP_VERSION}")
    logger.info("Using standard MCP Python SDK with FastMCP")
    
    if args.transport == "http":
        logger.info(f"HTTP mode: {args.host}:{args.port}")
        # Run HTTP server
        asyncio.run(run_http_server(args.host, args.port))
    else:
        logger.info("STDIO mode: for Claude/MCP integration")
        # Run stdio server
        mcp.run()


if __name__ == "__main__":
    main()