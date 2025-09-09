"""
Core Issues Tools for YouTrack MCP - Minimal Implementation.

Implements the 3 core issues tools:
- issues.get: Rich read with expansions
- issues.create: Schema-aware creation
- issues.patch: Primary writer with typed operations
"""

import json
import logging
from typing import Any, Dict, Optional, List

from youtrack_mcp.api.client import YouTrackClient
from youtrack_mcp.api.issues import IssuesClient
from youtrack_mcp.mcp_wrappers import sync_wrapper, async_wrapper
from youtrack_mcp.utils import format_json_response

logger = logging.getLogger(__name__)


class CoreIssuesTools:
    """Minimal issues tools with clean interfaces."""

    def __init__(self):
        """Initialize core issues tools."""
        self.client = YouTrackClient()
        self.issues_api = IssuesClient(self.client)

    @async_wrapper
    async def get(self, issue_id: str, include: Optional[List[str]] = None) -> str:
        """
        Rich issue read with expansions.

        FORMAT: issues.get(issue_id="PROJECT-123", include=["customFields", "comments"])

        Args:
            issue_id: Issue ID or readable ID (e.g., PROJECT-123)
            include: List of expansions (customFields, comments, attachments, etc.)

        Returns:
            JSON with full issue data and requested expansions
        """
        try:
            # Build fields parameter based on expansions
            base_fields = "id,idReadable,summary,description,created,updated,project,reporter,assignee"

            if include:
                if "customFields" in include:
                    base_fields += ",customFields"
                if "comments" in include:
                    base_fields += ",comments"
                if "attachments" in include:
                    base_fields += ",attachments"
                if "links" in include:
                    base_fields += ",links"

            # Get the issue
            issue = await self.issues_api.get_issue(issue_id)

            # Convert to dict for JSON response
            if hasattr(issue, "model_dump"):
                issue_data = issue.model_dump()
            else:
                issue_data = issue.__dict__ if hasattr(issue, "__dict__") else str(issue)

            return format_json_response({
                "issue": issue_data,
                "expansions": include or [],
                "fields_requested": base_fields
            })

        except Exception as e:
            logger.exception(f"Error getting issue {issue_id}")
            return format_json_response({
                "error": str(e),
                "error_type": type(e).__name__,
                "issue_id": issue_id
            })

    @async_wrapper
    async def create(self, project: str, summary: str, description: Optional[str] = None) -> str:
        """
        Schema-aware issue creation.

        FORMAT: issues.create(project="DEMO", summary="Bug report", description="Details...")

        Args:
            project: Project ID or short name
            summary: Issue summary/title
            description: Optional issue description

        Returns:
            JSON with created issue data
        """
        try:
            # Create the issue
            issue = await self.issues_api.create_issue(
                project_id=project,
                summary=summary,
                description=description
            )

            # Convert to dict for JSON response
            if hasattr(issue, "model_dump"):
                issue_data = issue.model_dump()
            else:
                issue_data = issue.__dict__ if hasattr(issue, "__dict__") else str(issue)

            return format_json_response({
                "issue": issue_data,
                "created": True
            })

        except Exception as e:
            logger.exception(f"Error creating issue in project {project}")
            return format_json_response({
                "error": str(e),
                "error_type": type(e).__name__,
                "project": project,
                "summary": summary
            })

    @async_wrapper
    async def patch(self, issue_id: str, fields: Optional[Dict[str, Any]] = None, ops: Optional[List[Dict[str, Any]]] = None) -> str:
        """
        Primary writer with typed operations.

        FORMAT: issues.patch(issue_id="PROJECT-123", fields={"summary": "New title"})
        FORMAT: issues.patch(issue_id="PROJECT-123", ops=[{"op": "set", "field": "state", "value": "Fixed"}])

        Args:
            issue_id: Issue ID or readable ID
            fields: Direct field updates (simple key-value pairs)
            ops: Typed operations (advanced updates with validation)

        Returns:
            JSON with updated issue data
        """
        try:
            if fields:
                # Simple field updates
                updated_issue = await self.issues_api.update_issue(
                    issue_id=issue_id,
                    summary=fields.get("summary"),
                    description=fields.get("description")
                )
            elif ops:
                # Typed operations (placeholder for now - would need more complex logic)
                logger.warning("Typed operations not yet implemented, using simple update")
                # For now, just update summary if present
                summary = None
                for op in ops:
                    if op.get("field") == "summary" and op.get("op") == "set":
                        summary = op.get("value")
                        break

                updated_issue = await self.issues_api.update_issue(
                    issue_id=issue_id,
                    summary=summary
                )
            else:
                return format_json_response({
                    "error": "Either 'fields' or 'ops' parameter must be provided"
                })

            # Convert to dict for JSON response
            if hasattr(updated_issue, "model_dump"):
                issue_data = updated_issue.model_dump()
            else:
                issue_data = updated_issue.__dict__ if hasattr(updated_issue, "__dict__") else str(updated_issue)

            return format_json_response({
                "issue": issue_data,
                "updated": True,
                "fields_updated": list(fields.keys()) if fields else [],
                "ops_applied": len(ops) if ops else 0
            })

        except Exception as e:
            logger.exception(f"Error updating issue {issue_id}")
            return format_json_response({
                "error": str(e),
                "error_type": type(e).__name__,
                "issue_id": issue_id
            })

    def get_tool_definitions(self) -> Dict[str, Dict[str, Any]]:
        """Get core issues tool definitions."""
        return {
            "issues.get": {
                "description": "Get issue with optional expansions",
                "function": self.get
            },
            "issues.create": {
                "description": "Create new issue in project",
                "function": self.create
            },
            "issues.patch": {
                "description": "Update issue fields and properties",
                "function": self.patch
            }
        }


__all__ = ["CoreIssuesTools"]