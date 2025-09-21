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


from youtrack_mcp.utils.error_educator import LLMErrorEducator

# Initialize the error educator
error_educator = LLMErrorEducator()

logger = logging.getLogger(__name__)


class IssuesTools:
    """Minimal issues tools with clean interfaces."""

    def __init__(self) -> None:
        """Initialize core issues tools."""
        self.client = YouTrackClient()
        self.issues_api = IssuesClient(self.client)

    async def get(self, issue_id: str, include: Optional[List[str]] = None) -> dict:
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

            return {
                "issue": issue_data,
                "expansions": include or [],
                "fields_requested": base_fields
            }

        except (ResourceNotFoundError, AuthenticationError, PermissionDeniedError,
                ValidationError, RateLimitError, ServerError, YouTrackAPIError) as e:
            # Use LLM-optimized error response
            llm_response = error_educator.create_educational_error_response(
                operation="get_issue",
                error=e,
                context={"issue_id": issue_id, "include": include}
            )
            return llm_response
        except Exception as e:
            logger.exception(f"Unexpected error getting issue {issue_id}: {e}")
            llm_response = error_educator.create_educational_error_response(
                operation="get_issue",
                error=e,
                context={"issue_id": issue_id, "include": include}
            )
            return llm_response

    async def create(self, project: str, summary: str, description: Optional[str] = None, custom_fields: Optional[Dict[str, Any]] = None) -> dict:
        """
        Schema-aware issue creation with custom field support.

        FORMAT: issues.create(project="DEMO", summary="Bug report", description="Details...", custom_fields={"Type": "Bug", "Priority": "High"})

        Args:
            project: Project ID or short name
            summary: Issue summary/title
            description: Optional issue description
            custom_fields: Optional dictionary of custom field names and values (e.g., {"Type": "Bug", "Priority": "High"})

        Returns:
            JSON with created issue data
        """
        try:
            # Create the issue
            issue = await self.issues_api.create_issue(
                project_id=project,
                summary=summary,
                description=description,
                custom_fields=custom_fields
            )

            # Convert to dict for JSON response
            if hasattr(issue, "model_dump"):
                issue_data = issue.model_dump()
            else:
                issue_data = issue.__dict__ if hasattr(issue, "__dict__") else str(issue)

            return {
                "issue": issue_data,
                "created": True
            }

        except (AuthenticationError, PermissionDeniedError, ValidationError,
                ResourceNotFoundError, RateLimitError, ServerError, YouTrackAPIError) as e:
            # Use LLM-optimized error response
            llm_response = error_educator.create_educational_error_response(
                operation="create_issue",
                error=e,
                context={"project": project, "summary": summary, "description": description, "custom_fields": custom_fields}
            )
            return llm_response
        except Exception as e:
            logger.exception(f"Unexpected error creating issue in {project}: {e}")
            llm_response = error_educator.create_educational_error_response(
                operation="create_issue",
                error=e,
                context={"project": project, "summary": summary, "description": description, "custom_fields": custom_fields}
            )
            return llm_response

    async def patch(self, issue_id: str, fields: Optional[Dict[str, Any]] = None, ops: Optional[List[Dict[str, Any]]] = None) -> dict:
        """Update issue with /fields/<FieldName> support and schema-aware coercion."""
        try:
            updated_issue = None
            custom_fields_updated = []
            regular_fields_updated = []

            # Handle friendly fields{} format - convert to ops format internally
            if fields and not ops:
                ops = []
                for field_name, value in fields.items():
                    if field_name in ["summary", "description"]:
                        # Regular fields
                        ops.append({
                            "op": "set",
                            "path": f"/fields/{field_name}",
                            "value": value
                        })
                    else:
                        # Custom fields
                        ops.append({
                            "op": "set",
                            "path": f"/fields/{field_name}",
                            "value": value
                        })

            if ops:
                # Process typed operations with /fields/<FieldName> support
                custom_fields_dict = {}
                regular_updates = {}

                for op in ops:
                    path = op.get("path", "")
                    value = op.get("value")
                    operation = op.get("op", "set")

                    if operation != "set":
                        continue  # Only support set operations for now

                    if path.startswith("/fields/"):
                        field_name = path[8:]  # Remove "/fields/" prefix

                        if field_name in ["summary", "description"]:
                            # Regular fields
                            regular_updates[field_name] = value
                            regular_fields_updated.append(field_name)
                        else:
                            # Custom fields - use IssuesClient builders for schema-aware coercion
                            custom_fields_dict[field_name] = value
                            custom_fields_updated.append(field_name)

                # Apply regular field updates
                if regular_updates:
                    updated_issue = await self.issues_api.update_issue(
                        issue_id=issue_id,
                        summary=regular_updates.get("summary"),
                        description=regular_updates.get("description")
                    )

                # Apply custom field updates with schema-aware processing
                if custom_fields_dict:
                    await self.issues_api.update_issue_custom_fields(
                        issue_id=issue_id,
                        custom_fields=custom_fields_dict
                    )

            elif not fields:
                return {
                    "error": "Either 'fields' or 'ops' parameter must be provided"
                }

            # Get the updated issue data for response
            if not updated_issue:
                # If we only updated custom fields, get the current issue
                updated_issue = await self.issues_api.get_issue(issue_id)

            # Convert to dict for JSON response
            if hasattr(updated_issue, "model_dump"):
                issue_data = updated_issue.model_dump()
            else:
                issue_data = updated_issue.__dict__ if hasattr(updated_issue, "__dict__") else str(updated_issue)

            return {
                "issue": issue_data,
                "updated": True,
                "regular_fields_updated": regular_fields_updated,
                "custom_fields_updated": custom_fields_updated,
                "total_fields_updated": len(regular_fields_updated) + len(custom_fields_updated),
                "ops_applied": len(ops) if ops else 0,
                "message": f"Successfully updated issue {issue_id}"
            }

        except (ResourceNotFoundError, AuthenticationError, PermissionDeniedError,
                ValidationError, RateLimitError, ServerError, YouTrackAPIError) as e:
            # Use LLM-optimized error response
            llm_response = error_educator.create_educational_error_response(
                operation="update_issue",
                error=e,
                context={"issue_id": issue_id, "fields": fields, "ops": ops}
            )
            return llm_response
        except Exception as e:
            logger.exception(f"Unexpected error updating issue {issue_id}: {e}")
            llm_response = error_educator.create_educational_error_response(
                operation="update_issue",
                error=e,
                context={"issue_id": issue_id, "fields": fields, "ops": ops}
            )
            return llm_response

    def get_tool_definitions(self) -> Dict[str, Dict[str, Any]]:
        """Get core issues tool definitions."""
        return {
            "issues.get": {
                "description": "Get issue with optional expansions",
                "function": self.get
            },
            "issues.create": {
                "description": "Create new issue in project with custom field support. Use projects.custom_fields() first to see required fields like Type, Priority, etc.",
                "function": self.create
            },
            "issues.patch": {
                "description": "Update issue fields with schema-aware coercion",
                "function": self.patch
            }
        }


__all__ = ["IssuesTools"]