"""
Core Projects Tools for YouTrack MCP - Minimal Implementation.

Implements the 4 core project tools:
- projects.list: Project discovery
- projects.get: Project details with expansions
- projects.patch: Project mutations with typed ops
- projects.create: Project creation
"""

import logging
from typing import Any, Dict, Optional, List

from youtrack_mcp.api.client import YouTrackClient
from youtrack_mcp.api.projects import ProjectsClient
from youtrack_mcp.mcp_wrappers import sync_wrapper
from youtrack_mcp.utils import format_json_response

logger = logging.getLogger(__name__)


class CoreProjectsTools:
    """Minimal projects tools with clean interfaces."""

    def __init__(self):
        """Initialize core projects tools."""
        self.client = YouTrackClient()
        self.projects_api = ProjectsClient(self.client)

    @sync_wrapper
    def list(self, include_archived: bool = False) -> str:
        """
        Discover accessible projects.

        FORMAT: projects.list(include_archived=False)

        Args:
            include_archived: Whether to include archived projects

        Returns:
            JSON with list of projects
        """
        try:
            projects = self.projects_api.get_projects(include_archived=include_archived)

            # Convert to dicts for JSON response
            result = []
            for project in projects:
                if hasattr(project, "model_dump"):
                    result.append(project.model_dump())
                else:
                    result.append(project)

            return format_json_response({
                "projects": result,
                "count": len(result),
                "include_archived": include_archived
            })

        except Exception as e:
            logger.exception("Error listing projects")
            return format_json_response({
                "error": str(e),
                "error_type": type(e).__name__,
                "include_archived": include_archived
            })

    @sync_wrapper
    def get(self, project_id: str, include: Optional[List[str]] = None) -> str:
        """
        Project details with expansions.

        FORMAT: projects.get(project_id="DEMO", include=["customFields", "issues"])

        Args:
            project_id: Project ID or short name
            include: List of expansions (customFields, issues, etc.)

        Returns:
            JSON with full project data and requested expansions
        """
        try:
            project = self.projects_api.get_project(project_id)

            # Convert to dict for JSON response
            if hasattr(project, "model_dump"):
                project_data = project.model_dump()
            else:
                project_data = project.__dict__ if hasattr(project, "__dict__") else str(project)

            # Handle expansions
            expansions = {}
            if include:
                if "customFields" in include:
                    try:
                        fields = self.projects_api.get_custom_fields(project_id)
                        expansions["customFields"] = fields
                    except Exception as e:
                        logger.warning(f"Failed to get custom fields: {e}")
                        expansions["customFields"] = []

                if "issues" in include:
                    try:
                        issues = self.projects_api.get_project_issues(project_id, limit=10)
                        expansions["issues"] = issues
                    except Exception as e:
                        logger.warning(f"Failed to get project issues: {e}")
                        expansions["issues"] = []

            return format_json_response({
                "project": project_data,
                "expansions": expansions,
                "expansions_requested": include or []
            })

        except Exception as e:
            logger.exception(f"Error getting project {project_id}")
            return format_json_response({
                "error": str(e),
                "error_type": type(e).__name__,
                "project_id": project_id
            })

    @sync_wrapper
    def patch(self, project_id: str, ops: Optional[List[Dict[str, Any]]] = None) -> str:
        """
        Project mutations with typed operations.

        FORMAT: projects.patch(project_id="DEMO", ops=[{"op": "set", "field": "name", "value": "New Name"}])

        Args:
            project_id: Project ID or short name
            ops: List of typed operations (set, add, remove)

        Returns:
            JSON with updated project data
        """
        try:
            if not ops:
                return format_json_response({
                    "error": "Operations list is required"
                })

            # Get current project data
            current_project = self.projects_api.get_project(project_id)

            # Apply operations
            updates = {}
            for op in ops:
                op_type = op.get("op")
                field = op.get("field")
                value = op.get("value")

                if op_type == "set":
                    if field == "name":
                        updates["name"] = value
                    elif field == "description":
                        updates["description"] = value
                    elif field == "archived":
                        updates["archived"] = value
                    elif field == "shortName":
                        updates["shortName"] = value
                    elif field == "leader":
                        updates["leader"] = {"id": value}
                elif op_type == "add":
                    # Handle add operations if needed
                    pass
                elif op_type == "remove":
                    # Handle remove operations if needed
                    pass

            if not updates:
                return format_json_response({
                    "error": "No valid operations provided"
                })

            # Apply updates via direct API call
            self.client.post(f"admin/projects/{project_id}", data=updates)

            # Get updated project
            updated_project = self.projects_api.get_project(project_id)

            # Convert to dict for JSON response
            if hasattr(updated_project, "model_dump"):
                project_data = updated_project.model_dump()
            else:
                project_data = updated_project.__dict__ if hasattr(updated_project, "__dict__") else str(updated_project)

            return format_json_response({
                "project": project_data,
                "updated": True,
                "operations_applied": len(ops)
            })

        except Exception as e:
            logger.exception(f"Error patching project {project_id}")
            return format_json_response({
                "error": str(e),
                "error_type": type(e).__name__,
                "project_id": project_id,
                "operations_requested": len(ops) if ops else 0
            })

    @sync_wrapper
    def create(self, name: str, short_name: str, lead_id: str) -> str:
        """
        Create new projects.

        FORMAT: projects.create(name="Demo Project", short_name="DEMO", lead_id="admin")

        Args:
            name: Project name
            short_name: Project short name/key
            lead_id: Project leader user ID

        Returns:
            JSON with created project data
        """
        try:
            project = self.projects_api.create_project(
                name=name,
                short_name=short_name,
                lead_id=lead_id
            )

            # Convert to dict for JSON response
            if hasattr(project, "model_dump"):
                project_data = project.model_dump()
            else:
                project_data = project.__dict__ if hasattr(project, "__dict__") else str(project)

            return format_json_response({
                "project": project_data,
                "created": True
            })

        except Exception as e:
            logger.exception(f"Error creating project {name}")
            return format_json_response({
                "error": str(e),
                "error_type": type(e).__name__,
                "name": name,
                "short_name": short_name,
                "lead_id": lead_id
            })

    def get_tool_definitions(self) -> Dict[str, Dict[str, Any]]:
        """Get core projects tool definitions."""
        return {
            "projects.list": {
                "description": "List accessible projects",
                "function": self.list
            },
            "projects.get": {
                "description": "Get project details",
                "function": self.get
            },
            "projects.patch": {
                "description": "Update project properties",
                "function": self.patch
            },
            "projects.create": {
                "description": "Create new project",
                "function": self.create
            }
        }


__all__ = ["CoreProjectsTools"]