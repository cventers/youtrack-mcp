"""
Core Projects Admin Tools for YouTrack MCP - Administrative Operations.

Implements admin-level project operations:
- projects.delete: Delete projects (admin only)
- projects.archive: Archive/unarchive projects (admin only)
- projects.restore: Restore deleted projects (admin only)
"""

import json
import logging
from typing import Any, Dict, Optional

from youtrack_mcp.api.client import YouTrackClient
from youtrack_mcp.api.projects import ProjectsClient
from youtrack_mcp.mcp_wrappers import async_wrapper
from youtrack_mcp.utils import format_json_response

logger = logging.getLogger(__name__)


class CoreProjectsAdminTools:
    """Administrative project tools with permission gating."""

    def __init__(self):
        """Initialize admin project tools."""
        self.client = YouTrackClient()
        self.projects_api = ProjectsClient(self.client)

    async def _check_admin_permissions(self) -> bool:
        """Check if user has admin permissions for project operations."""
        try:
            # Check if user can access admin endpoints
            # This is a basic check - in production you'd want more sophisticated permission checking
            response = await self.client.get("admin/projects", params={"$top": 1})
            return response is not None
        except Exception as e:
            logger.warning(f"Admin permission check failed: {e}")
            return False

    @async_wrapper
    async def delete(self, project_id: str, permanent: bool = False) -> str:
        """
        Delete a project (admin only).

        FORMAT: projects.delete(project_id="DEMO", permanent=False)

        Args:
            project_id: Project ID or short name to delete
            permanent: If True, permanently delete; if False, move to trash

        Returns:
            JSON with deletion confirmation
        """
        try:
            # Check admin permissions
            if not await self._check_admin_permissions():
                return format_json_response({
                    "error": "Admin permissions required for project deletion",
                    "project_id": project_id
                })

            # Delete the project
            if permanent:
                # Permanent deletion
                result = await self.client.delete(f"admin/projects/{project_id}")
            else:
                # Move to trash (soft delete)
                result = await self.client.post(f"admin/projects/{project_id}/trash")

            return format_json_response({
                "success": True,
                "project_id": project_id,
                "action": "permanently_deleted" if permanent else "moved_to_trash",
                "result": result
            })

        except Exception as e:
            logger.exception(f"Error deleting project {project_id}")
            return format_json_response({
                "error": str(e),
                "error_type": type(e).__name__,
                "project_id": project_id
            })

    @async_wrapper
    async def archive(self, project_id: str, archive: bool = True) -> str:
        """
        Archive or unarchive a project (admin only).

        FORMAT: projects.archive(project_id="DEMO", archive=True)

        Args:
            project_id: Project ID or short name
            archive: If True, archive; if False, unarchive

        Returns:
            JSON with archive status
        """
        try:
            # Check admin permissions
            if not await self._check_admin_permissions():
                return format_json_response({
                    "error": "Admin permissions required for project archiving",
                    "project_id": project_id
                })

            # Archive/unarchive the project
            action = "archive" if archive else "unarchive"
            result = await self.client.post(f"admin/projects/{project_id}/{action}")

            return format_json_response({
                "success": True,
                "project_id": project_id,
                "action": action,
                "archived": archive,
                "result": result
            })

        except Exception as e:
            logger.exception(f"Error archiving project {project_id}")
            return format_json_response({
                "error": str(e),
                "error_type": type(e).__name__,
                "project_id": project_id
            })

    @async_wrapper
    async def restore(self, project_id: str) -> str:
        """
        Restore a deleted project from trash (admin only).

        FORMAT: projects.restore(project_id="DEMO")

        Args:
            project_id: Project ID or short name to restore

        Returns:
            JSON with restoration confirmation
        """
        try:
            # Check admin permissions
            if not await self._check_admin_permissions():
                return format_json_response({
                    "error": "Admin permissions required for project restoration",
                    "project_id": project_id
                })

            # Restore the project from trash
            result = await self.client.post(f"admin/projects/{project_id}/restore")

            return format_json_response({
                "success": True,
                "project_id": project_id,
                "action": "restored_from_trash",
                "result": result
            })

        except Exception as e:
            logger.exception(f"Error restoring project {project_id}")
            return format_json_response({
                "error": str(e),
                "error_type": type(e).__name__,
                "project_id": project_id
            })

    def get_tool_definitions(self) -> Dict[str, Dict[str, Any]]:
        """Get admin project tool definitions."""
        return {
            "projects.delete": {
                "description": "Delete project (admin only)",
                "function": self.delete
            },
            "projects.archive": {
                "description": "Archive/unarchive project (admin only)",
                "function": self.archive
            },
            "projects.restore": {
                "description": "Restore deleted project (admin only)",
                "function": self.restore
            }
        }


__all__ = ["CoreProjectsAdminTools"]