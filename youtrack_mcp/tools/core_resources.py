"""
Core Resources Tools for YouTrack MCP - Minimal Implementation.

Implements the 1 core resources tool:
- resources.read: Secured URI proxy
"""

import json
import logging
from typing import Any, Dict
from urllib.parse import urlparse

from youtrack_mcp.api.client import YouTrackClient
from youtrack_mcp.mcp_wrappers import async_wrapper
from youtrack_mcp.utils import format_json_response
from youtrack_mcp.tools.help_resources import get_help_resource

logger = logging.getLogger(__name__)

# Resource URI schemes
YOUTRACK_URI_SCHEME = "youtrack"
HELP_URI_SCHEME = "help"


class CoreResourcesTools:
    """Minimal resources tools with clean interfaces."""

    def __init__(self):
        """Initialize core resources tools."""
        self._client = None

    @property
    def client(self):
        """Lazy initialization of YouTrack client."""
        if self._client is None:
            self._client = YouTrackClient()
        return self._client

    @async_wrapper
    async def read(self, uri: str) -> str:
        """
        Proxy read for secured URIs.

        FORMAT: resources.read(uri="youtrack://issues/DEMO-123")
        FORMAT: resources.read(uri="help://issues.get")

        Args:
            uri: YouTrack URI in youtrack:// format or help:// format

        Returns:
            JSON with resource content
        """
        try:
            # Parse the URI
            parsed = urlparse(uri)

            # Handle help:// URIs
            if parsed.scheme == HELP_URI_SCHEME:
                help_content = get_help_resource(uri)
                if help_content:
                    return format_json_response({
                        "uri": uri,
                        "resource_type": "help",
                        "content": help_content
                    })
                else:
                    return format_json_response({
                        "error": f"Help resource not found: {uri}"
                    })

            # Validate the scheme for YouTrack URIs
            if parsed.scheme != YOUTRACK_URI_SCHEME:
                return format_json_response({
                    "error": f"Invalid URI scheme: {parsed.scheme}. Expected: {YOUTRACK_URI_SCHEME} or {HELP_URI_SCHEME}"
                })

            # Extract path components
            path_parts = parsed.path.strip('/').split('/') if parsed.path.strip('/') else []

            # Handle different resource types
            if len(path_parts) == 2:
                resource_type, resource_id = path_parts

                if resource_type == "issues":
                    # Get issue data
                    issue_data = await self.client.get(f"issues/{resource_id}")
                    return format_json_response({
                        "uri": uri,
                        "resource_type": "issue",
                        "content": issue_data
                    })

                elif resource_type == "projects":
                    # Get project data
                    project_data = await self.client.get(f"admin/projects/{resource_id}")
                    return format_json_response({
                        "uri": uri,
                        "resource_type": "project",
                        "content": project_data
                    })

                elif resource_type == "users":
                    # Get user data
                    user_data = await self.client.get(f"users/{resource_id}")
                    return format_json_response({
                        "uri": uri,
                        "resource_type": "user",
                        "content": user_data
                    })

            elif len(path_parts) == 1:
                resource_type = path_parts[0]

                if resource_type == "projects":
                    # List all projects
                    projects_data = await self.client.get("admin/projects")
                    return format_json_response({
                        "uri": uri,
                        "resource_type": "projects_list",
                        "content": projects_data
                    })

                elif resource_type == "issues":
                    # List recent issues
                    issues_data = await self.client.get("issues", params={"$top": 50})
                    return format_json_response({
                        "uri": uri,
                        "resource_type": "issues_list",
                        "content": issues_data
                    })

                elif resource_type == "users":
                    # List users
                    users_data = await self.client.get("users")
                    return format_json_response({
                        "uri": uri,
                        "resource_type": "users_list",
                        "content": users_data
                    })

            return format_json_response({
                "error": f"Unsupported URI pattern: {uri}"
            })

        except Exception as e:
            logger.exception(f"Error reading resource: {uri}")
            return format_json_response({
                "error": str(e),
                "error_type": type(e).__name__,
                "uri": uri
            })

    def get_tool_definitions(self) -> Dict[str, Dict[str, Any]]:
        """Get core resources tool definitions."""
        return {
            "resources.read": {
                "description": "Read YouTrack resources by URI",
                "function": self.read
            }
        }


__all__ = ["CoreResourcesTools"]