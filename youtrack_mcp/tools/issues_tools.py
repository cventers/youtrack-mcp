"""
Core Issues Tools for YouTrack MCP - Minimal Implementation.

Implements the 3 core issues tools:
- issues.get: Rich read with expansions
- issues.create: Schema-aware creation
- issues.patch: Primary writer with typed operations
"""

import json
from youtrack_mcp.logging import get_logger
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

from youtrack_mcp.utils.resolver_registry import resolver_registry
from youtrack_mcp.utils.id_resolver import IDResolutionError
from youtrack_mcp.utils.error_educator import LLMErrorEducator

# Initialize the error educator
error_educator = LLMErrorEducator()

logger = get_logger(__name__)


class IssuesTools:
    """Minimal issues tools with clean interfaces."""

    def __init__(self) -> None:
        """Initialize core issues tools with ID resolution support."""
        # Get singleton ID resolver
        id_resolver = resolver_registry.get_resolver()

        # Initialize client with resolver
        self.client = YouTrackClient(id_resolver=id_resolver)

        # Set client reference and initialize API clients in resolver
        if id_resolver.client is None:
            id_resolver.client = self.client
            # Re-initialize API clients now that we have the client
            from youtrack_mcp.api.projects import ProjectsClient
            from youtrack_mcp.api.users import UsersClient
            id_resolver.projects_api = ProjectsClient(self.client)
            id_resolver.users_api = UsersClient(self.client)

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

        except YouTrackAPIError as e:
            # Log the error but propagate it so MCP marks as is_error=True
            logger.error(f"YouTrack API error getting issue: {issue_id}",
                       error_type=type(e).__name__,
                       status_code=getattr(e, 'status_code', None))
            raise
        except Exception as e:
            # Log unexpected errors and propagate
            logger.exception(f"Unexpected error getting issue {issue_id}: {e}")
            raise

    async def create(self, project: str, summary: str, description: Optional[str] = None, custom_fields: Optional[Dict[str, Any]] = None) -> dict:
        """
        Schema-aware issue creation with custom field support.

        FORMAT: issues.create(project="DEMO", summary="Bug report", description="Details...", custom_fields={"Type": "Bug", "Priority": "High"})

        Args:
            project: Project ID or short name (e.g., "CLUSTER" or "63-2")
            summary: Issue summary/title
            description: Optional issue description
            custom_fields: Optional dictionary of custom field names and values (e.g., {"Type": "Bug", "Priority": "High"})

        Returns:
            JSON with created issue data
        """
        try:
            # Resolve project ID if resolver is available
            resolved_project_id = project
            if self.client.id_resolver:
                try:
                    resolved_project_id = await self.client.id_resolver.resolve_project_id(project)
                    if resolved_project_id != project:
                        logger.info(f"Resolved project '{project}' to ID '{resolved_project_id}'")
                except IDResolutionError as e:
                    logger.warning(f"Failed to resolve project ID for '{project}', using as-is: {e}")
                    # Fall back to using the project parameter as-is
                    resolved_project_id = project
                except (YouTrackAPIError, ValueError) as e:
                    logger.warning(f"Error resolving project ID for '{project}': {e}")
                    resolved_project_id = project

            # Resolve user references in custom fields if needed
            resolved_custom_fields = custom_fields
            if custom_fields and self.client.id_resolver:
                resolved_custom_fields = {}
                for field_name, value in custom_fields.items():
                    # Check for user-type fields that might need resolution
                    if field_name in ["Assignee", "Reporter", "Owner"] and value:
                        try:
                            if isinstance(value, list):
                                resolved_value = []
                                for user_ref in value:
                                    if user_ref:  # Skip empty values
                                        resolved_id = await self.client.id_resolver.resolve_user_id(user_ref)
                                        resolved_value.append(resolved_id)
                                        if resolved_id != user_ref:
                                            logger.info(f"Resolved user '{user_ref}' to ID '{resolved_id}'")
                                resolved_custom_fields[field_name] = resolved_value
                            else:
                                resolved_id = await self.client.id_resolver.resolve_user_id(value)
                                resolved_custom_fields[field_name] = resolved_id
                                if resolved_id != value:
                                    logger.info(f"Resolved user '{value}' to ID '{resolved_id}'")
                        except (IDResolutionError, YouTrackAPIError, ValueError) as e:
                            logger.warning(f"Failed to resolve user ID for field '{field_name}': {e}")
                            resolved_custom_fields[field_name] = value  # Use original value on failure
                    else:
                        resolved_custom_fields[field_name] = value

            # Create the issue with resolved IDs
            issue = await self.issues_api.create_issue(
                project_id=resolved_project_id,
                summary=summary,
                description=description,
                custom_fields=resolved_custom_fields
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

        except YouTrackAPIError as e:
            # Log the error but propagate it so MCP marks as is_error=True
            logger.error(f"YouTrack API error creating issue in {project}",
                       error_type=type(e).__name__,
                       status_code=getattr(e, 'status_code', None))
            raise
        except Exception as e:
            # Log unexpected errors and propagate
            logger.exception(f"Unexpected error creating issue in {project}: {e}")
            raise

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
                    # Built-in fields that should be handled as regular fields, not custom fields
                    # Note: "assignee" (lowercase) is built-in, but "Assignee" (capital) could be custom
                    if field_name in ["summary", "description"]:
                        # Regular/built-in fields
                        ops.append({
                            "op": "set",
                            "path": f"/fields/{field_name}",
                            "value": value,
                            "builtin": True  # Mark as built-in for special handling
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
                    is_builtin = op.get("builtin", False)

                    if operation != "set":
                        continue  # Only support set operations for now

                    if path.startswith("/fields/"):
                        field_name = path[8:]  # Remove "/fields/" prefix

                        # Check if this is a built-in field
                        if field_name.lower() in ["summary", "description", "assignee", "reporter"] or is_builtin:
                            # Handle built-in fields
                            if field_name.lower() == "assignee":
                                # Assignee needs special handling - resolve user ID if needed
                                if value and self.client.id_resolver:
                                    try:
                                        resolved_id = await self.client.id_resolver.resolve_user_id(value)
                                        regular_updates["assignee"] = resolved_id
                                        if resolved_id != value:
                                            logger.info(f"Resolved assignee '{value}' to ID '{resolved_id}'")
                                    except (IDResolutionError, YouTrackAPIError, ValueError) as e:
                                        logger.warning(f"Failed to resolve assignee ID: {e}")
                                        regular_updates["assignee"] = value
                                else:
                                    regular_updates["assignee"] = value
                                regular_fields_updated.append("assignee")
                            else:
                                # Other regular fields
                                regular_updates[field_name] = value
                                regular_fields_updated.append(field_name)
                        else:
                            # Custom fields - resolve user references if needed
                            if field_name in ["Owner"] and value and self.client.id_resolver:
                                try:
                                    if isinstance(value, list):
                                        resolved_value = []
                                        for user_ref in value:
                                            if user_ref:  # Skip empty values
                                                resolved_id = await self.client.id_resolver.resolve_user_id(user_ref)
                                                resolved_value.append(resolved_id)
                                                if resolved_id != user_ref:
                                                    logger.info(f"Resolved user '{user_ref}' to ID '{resolved_id}'")
                                        custom_fields_dict[field_name] = resolved_value
                                    else:
                                        resolved_id = await self.client.id_resolver.resolve_user_id(value)
                                        custom_fields_dict[field_name] = resolved_id
                                        if resolved_id != value:
                                            logger.info(f"Resolved user '{value}' to ID '{resolved_id}'")
                                except (IDResolutionError, YouTrackAPIError, ValueError) as e:
                                    logger.warning(f"Failed to resolve user ID for field '{field_name}': {e}")
                                    custom_fields_dict[field_name] = value  # Use original value on failure
                            else:
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

        except YouTrackAPIError as e:
            # Log the error but propagate it so MCP marks as is_error=True
            logger.error(f"YouTrack API error updating issue: {issue_id}",
                       error_type=type(e).__name__,
                       status_code=getattr(e, 'status_code', None))
            raise
        except Exception as e:
            # Log unexpected errors and propagate
            logger.exception(f"Unexpected error updating issue {issue_id}: {e}")
            raise

    def get_tool_definitions(self) -> Dict[str, Dict[str, Any]]:
        """Get core issues tool definitions."""
        return {
            "issues.get": {
                "description": "Get issue with optional expansions",
                "function": self.get
            },
            "issues.create": {
                "description": "Create new issue in project with custom field support. Accepts project short name (e.g., 'ACC') or numeric ID (e.g., '63-13'). Use projects.custom_fields() first to see required fields like Type, Priority, etc.",
                "function": self.create
            },
            "issues.patch": {
                "description": "Update issue fields with schema-aware coercion",
                "function": self.patch
            }
        }


__all__ = ["IssuesTools"]