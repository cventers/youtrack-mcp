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

from youtrack_mcp.api.client import (
    YouTrackClient,
    YouTrackAPIError,
    AuthenticationError,
    PermissionDeniedError,
    ResourceNotFoundError,
    ValidationError,
    ServerError,
    RateLimitError
)
from youtrack_mcp.api.issues import IssuesClient
from youtrack_mcp.mcp_wrappers import sync_wrapper, async_wrapper
from youtrack_mcp.utils import format_json_response
from youtrack_mcp.llm_error_responses import LLMErrorEducator

# Initialize the error educator
error_educator = LLMErrorEducator()

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

        except (ResourceNotFoundError, AuthenticationError, PermissionDeniedError,
                ValidationError, RateLimitError, ServerError, YouTrackAPIError) as e:
            # Use LLM-optimized error response
            llm_response = error_educator.create_educational_error_response(
                operation="get_issue",
                error=e,
                context={"issue_id": issue_id, "include": include}
            )
            return format_json_response(llm_response)
        except Exception as e:
            logger.exception(f"Unexpected error getting issue {issue_id}: {e}")
            llm_response = error_educator.create_educational_error_response(
                operation="get_issue",
                error=e,
                context={"issue_id": issue_id, "include": include}
            )
            return format_json_response(llm_response)

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

        except (AuthenticationError, PermissionDeniedError, ValidationError,
                ResourceNotFoundError, RateLimitError, ServerError, YouTrackAPIError) as e:
            # Use LLM-optimized error response
            llm_response = error_educator.create_educational_error_response(
                operation="create_issue",
                error=e,
                context={"project": project, "summary": summary, "description": description}
            )
            return format_json_response(llm_response)
        except Exception as e:
            logger.exception(f"Unexpected error creating issue in {project}: {e}")
            llm_response = error_educator.create_educational_error_response(
                operation="create_issue",
                error=e,
                context={"project": project, "summary": summary, "description": description}
            )
            return format_json_response(llm_response)

    @async_wrapper
    async def patch(self, issue_id: str, fields: Optional[Dict[str, Any]] = None, ops: Optional[List[Dict[str, Any]]] = None) -> str:
        """
        Primary writer with typed operations and custom field support.

        FORMAT: issues.patch(issue_id="PROJECT-123", fields={"summary": "New title"})
        FORMAT: issues.patch(issue_id="PROJECT-123", ops=[{"op": "set", "field": "state", "value": "Fixed"}])
        FORMAT: issues.patch(issue_id="PROJECT-123", fields={"customFields": {"Priority": "High", "Story Points": 5}})

        Args:
            issue_id: Issue ID or readable ID
            fields: Direct field updates (simple key-value pairs, supports customFields)
            ops: Typed operations (advanced updates with validation)

        Returns:
            JSON with updated issue data
        """
        try:
            updated_issue = None
            custom_fields_updated = []

            if fields:
                # Handle custom fields separately
                custom_fields = fields.get("customFields", {})

                if custom_fields:
                    # Update custom fields using the API
                    await self.issues_api.update_issue_custom_fields(
                        issue_id=issue_id,
                        custom_fields=custom_fields
                    )
                    custom_fields_updated = list(custom_fields.keys())

                    # Remove customFields from regular fields to avoid double processing
                    fields_copy = fields.copy()
                    fields_copy.pop("customFields", None)
                    fields = fields_copy if fields_copy else None

                # Handle regular field updates
                if fields:
                    updated_issue = await self.issues_api.update_issue(
                        issue_id=issue_id,
                        summary=fields.get("summary"),
                        description=fields.get("description")
                    )

            elif ops:
                # Typed operations with custom field support
                logger.warning("Typed operations with custom fields not yet fully implemented")

                # Process operations for custom fields
                custom_ops = []
                regular_ops = []

                for op in ops:
                    field_name = op.get("field", "")
                    if field_name and not field_name.startswith(("summary", "description", "reporter", "assignee")):
                        # Assume it's a custom field
                        custom_ops.append(op)
                    else:
                        regular_ops.append(op)

                # Handle custom field operations
                if custom_ops:
                    custom_fields_dict = {}
                    for op in custom_ops:
                        if op.get("op") == "set":
                            custom_fields_dict[op.get("field")] = op.get("value")

                    if custom_fields_dict:
                        await self.issues_api.update_issue_custom_fields(
                            issue_id=issue_id,
                            custom_fields=custom_fields_dict
                        )
                        custom_fields_updated = list(custom_fields_dict.keys())

                # Handle regular operations
                if regular_ops:
                    summary = None
                    for op in regular_ops:
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

            # Get the updated issue data for response
            if not updated_issue:
                # If we only updated custom fields, get the current issue
                updated_issue = await self.issues_api.get_issue(issue_id)

            # Convert to dict for JSON response
            if hasattr(updated_issue, "model_dump"):
                issue_data = updated_issue.model_dump()
            else:
                issue_data = updated_issue.__dict__ if hasattr(updated_issue, "__dict__") else str(updated_issue)

            return format_json_response({
                "issue": issue_data,
                "updated": True,
                "fields_updated": list(fields.keys()) if fields else [],
                "custom_fields_updated": custom_fields_updated,
                "ops_applied": len(ops) if ops else 0,
                "message": f"Successfully updated issue {issue_id}"
            })

        except (ResourceNotFoundError, AuthenticationError, PermissionDeniedError,
                ValidationError, RateLimitError, ServerError, YouTrackAPIError) as e:
            # Use LLM-optimized error response
            llm_response = error_educator.create_educational_error_response(
                operation="update_issue",
                error=e,
                context={"issue_id": issue_id, "fields": fields, "ops": ops}
            )
            return format_json_response(llm_response)
        except Exception as e:
            logger.exception(f"Unexpected error updating issue {issue_id}: {e}")
            llm_response = error_educator.create_educational_error_response(
                operation="update_issue",
                error=e,
                context={"issue_id": issue_id, "fields": fields, "ops": ops}
            )
            return format_json_response(llm_response)

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