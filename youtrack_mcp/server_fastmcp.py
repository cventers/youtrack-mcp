"""
FastMCP Server Implementation for YouTrack MCP.

This module provides a clean FastMCP-based server implementation that replaces
the legacy wrapper-based approach with typed, schema-driven tool registration.
"""

import logging
from typing import Dict, List, Any, Optional
from pydantic import BaseModel

from mcp.server import FastMCP

from youtrack_mcp.ai.registry import ai_registry
from youtrack_mcp.config import config
from youtrack_mcp.tools.search_tools import SearchTools
from youtrack_mcp.tools.issues_tools import IssuesTools
from youtrack_mcp.tools.projects_tools import ProjectsTools
from youtrack_mcp.tools.users_tools import UsersTools
from youtrack_mcp.tools.resources_tools import ResourcesTools
from youtrack_mcp.tools.projects_admin_tools import ProjectsAdminTools
from youtrack_mcp.tools.users_admin_tools import UsersAdminTools
from youtrack_mcp.tools.custom_fields import CustomFieldsTools
from youtrack_mcp.tools.ai_tools import AITools
from youtrack_mcp.mcp_resources import (
    YouTrackResources, 
    handle_query_syntax_resource,
    handle_projects_list_resource,
    handle_users_directory_resource
)
from youtrack_mcp.middleware import TimestampMiddleware

logger = logging.getLogger(__name__)

# Pydantic models for complex tool inputs
class AutoSearchInput(BaseModel):
    """Input model for search.autosearch tool."""
    natural_language_query: str
    project_context: Optional[str] = None
    limit: int = 50

# Initialize FastMCP server
mcp = FastMCP("youtrack")

# Initialize AI tools later (after config is loaded)
ai_tools = None

# Initialize tool classes (ai_tools will be set later)
search_tools = SearchTools(ai_tools=ai_tools)
issues_tools = IssuesTools()
projects_tools = ProjectsTools()
users_tools = UsersTools()
resources_tools = ResourcesTools()
projects_admin_tools = ProjectsAdminTools()
users_admin_tools = UsersAdminTools()
custom_fields_tools = CustomFieldsTools()

# Initialize resources
mcp_resources = YouTrackResources()

# Tool registration will happen in main.py after config is loaded
def register_mcp_tools():  # type: ignore
    """Register MCP tools after all dependencies are initialized."""
    global ai_tools  # Access the global ai_tools variable

    @mcp.tool()
    async def search_query(query: str, limit: int = 50, sort_by: Optional[str] = None, sort_order: Optional[str] = None) -> dict:
        """Execute explicit YouTrack Query Language."""
        return await search_tools.query(query, limit, sort_by, sort_order)

    # Only register autosearch if LLM is configured
    if ai_tools:
        @mcp.tool()
        async def search_autosearch(natural_language_query: str, project_context: Optional[str] = None) -> dict:
            """Natural language to YQL translation."""
            return await search_tools.autosearch(natural_language_query, project_context)

    @mcp.tool()
    async def projects_list(include_archived: bool = False) -> dict:
        """Discover accessible projects."""
        return await projects_tools.list(include_archived)

    @mcp.tool()
    async def projects_get(project_id: str, include: Optional[List[str]] = None) -> dict:
        """Project details with expansions."""
        return await projects_tools.get(project_id, include)

    @mcp.tool()
    async def projects_patch(project_id: str, ops: Optional[List[Dict[str, Any]]] = None) -> dict:
        """Project mutations with typed operations."""
        return await projects_tools.patch(project_id, ops)

    @mcp.tool()
    async def projects_create(name: str, short_name: str, lead_id: str, description: Optional[str] = None) -> dict:
        """Create new projects."""
        return await projects_tools.create(name, short_name, lead_id, description)

    @mcp.tool()
    async def issues_get(issue_id: str, include: Optional[List[str]] = None) -> dict:
        """Rich issue read with expansions."""
        return await issues_tools.get(issue_id, include)

    @mcp.tool()
    async def issues_create(project: str, summary: str, description: Optional[str] = None, custom_fields: Optional[Dict[str, Any]] = None) -> dict:
        """Schema-aware issue creation with custom field support."""
        return await issues_tools.create(project, summary, description, custom_fields)

    @mcp.tool()
    async def issues_patch(issue_id: str, fields: Optional[Dict[str, Any]] = None, ops: Optional[List[Dict[str, Any]]] = None) -> dict:
        """Update issue with /fields/<FieldName> support and schema-aware coercion."""
        return await issues_tools.patch(issue_id, fields, ops)

    @mcp.tool()
    async def users_search(query: str, limit: int = 10) -> dict:
        """Search for users by name or login."""
        return await users_tools.search(query, limit)

    # Only register ai.plan if LLM is configured
    if ai_tools is not None:
        @mcp.tool()
        async def ai_plan(intent: str, context: Optional[Dict[str, Any]] = None) -> dict:
            """LLM-powered intent planning and analysis."""
            # Type checker doesn't understand that ai_tools is not None here
            return await ai_tools.plan(intent, context)  # type: ignore

# Register resources using existing handlers
@mcp.resource("youtrack://query-syntax")
async def get_query_syntax() -> str:
    """YouTrack Query Language syntax guide."""
    return await handle_query_syntax_resource()

@mcp.resource("youtrack://projects")
async def get_projects_list() -> str:
    """List of all available projects."""
    return await handle_projects_list_resource()

@mcp.resource("youtrack://users")
async def get_users_directory() -> str:
    """Directory of available users."""
    return await handle_users_directory_resource()