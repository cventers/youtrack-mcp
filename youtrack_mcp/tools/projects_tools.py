"""
Core Projects Tools for YouTrack MCP - Minimal Implementation.

Implements the 4 core project tools:
- projects.list: Project discovery
- projects.get: Project details with expansions
- projects.patch: Project mutations with typed ops
- projects.create: Project creation
"""

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
from youtrack_mcp.api.projects import ProjectsClient

from youtrack_mcp.utils.resolver_registry import resolver_registry
from youtrack_mcp.utils.id_resolver import IDResolutionError

# format_json_response removed - middleware handles timestamp conversion
from youtrack_mcp.utils.error_educator import create_llm_friendly_error

logger = get_logger(__name__)


class ProjectsTools:
    """Minimal projects tools with clean interfaces."""

    def __init__(self):
        """Initialize core projects tools with ID resolution support."""
        # Get singleton ID resolver
        id_resolver = resolver_registry.get_resolver()

        # Initialize client with resolver
        self.client = YouTrackClient(id_resolver=id_resolver)

        # Set client reference and initialize API clients in resolver
        if id_resolver.client is None:
            id_resolver.client = self.client
            # Re-initialize API clients now that we have the client
            from youtrack_mcp.api.projects import ProjectsClient as ProjClient
            from youtrack_mcp.api.users import UsersClient
            id_resolver.projects_api = ProjClient(self.client)
            id_resolver.users_api = UsersClient(self.client)

        self.projects_api = ProjectsClient(self.client)

    async def list(self, include_archived: bool = False) -> dict:
        """
        Discover accessible projects.

        FORMAT: projects.list(include_archived=False)

        Args:
            include_archived: Whether to include archived projects

        Returns:
            JSON with list of projects
        """
        try:
            projects = await self.projects_api.get_projects(include_archived=include_archived)

            # Convert to dicts for JSON response
            result = []
            for project in projects:
                if hasattr(project, "model_dump"):
                    result.append(project.model_dump())
                else:
                    result.append(project)

            return {
                "projects": result,
                "count": len(result),
                "include_archived": include_archived
            }

        except YouTrackAPIError as e:
            # Log the error but propagate it so MCP marks as is_error=True
            logger.error("YouTrack API error listing projects",
                       error_type=type(e).__name__,
                       status_code=getattr(e, 'status_code', None))
            raise
        except Exception as e:
            # Log unexpected errors and propagate
            logger.exception("Unexpected error listing projects")
            raise

    async def get(self, project_id: str, include: Optional[List[str]] = None) -> dict:
        """
        Project details with expansions.

        FORMAT: projects.get(project_id="DEMO", include=["schema", "issues"])

        Args:
            project_id: Project ID or short name (e.g., "CLUSTER" or "63-2")
            include: List of expansions (schema, issues, etc.)

        Returns:
            JSON with full project data and requested expansions
        """
        try:
            # Resolve project ID if resolver is available
            resolved_project_id = project_id
            if self.client.id_resolver:
                try:
                    resolved_project_id = await self.client.id_resolver.resolve_project_id(project_id)
                    if resolved_project_id != project_id:
                        logger.info(f"Resolved project '{project_id}' to ID '{resolved_project_id}'")
                except IDResolutionError as e:
                    logger.warning(f"Failed to resolve project ID for '{project_id}', using as-is: {e}")
                    resolved_project_id = project_id
                except (YouTrackAPIError, ValueError) as e:
                    logger.warning(f"Error resolving project ID for '{project_id}': {e}")
                    resolved_project_id = project_id

            project = await self.projects_api.get_project(resolved_project_id)

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
                        fields = await self.projects_api.get_custom_fields(project_id)
                        expansions["customFields"] = fields
                    except Exception as e:
                        logger.warning("failed_to_get_custom_fields_e", e=e)
                        expansions["customFields"] = []

                if "schema" in include:
                    try:
                        # Use the schema method for comprehensive field information
                        # The schema method already returns a dict, not a JSON string
                        schema_data = await self.schema(project_id)
                        expansions["schema"] = schema_data
                    except Exception as e:
                        logger.warning("failed_to_get_project_schema_e", e=e)
                        expansions["schema"] = {}

                if "issues" in include:
                    try:
                        issues = await self.projects_api.get_project_issues(project_id, limit=10)
                        expansions["issues"] = issues
                    except Exception as e:
                        logger.warning("failed_to_get_project_issues_e", e=e)
                        expansions["issues"] = []

            return {
                "project": project_data,
                "expansions": expansions,
                "expansions_requested": include or []
            }

        except YouTrackAPIError as e:
            # Log the error but propagate it so MCP marks as is_error=True
            logger.error(f"YouTrack API error getting project: {project_id}",
                       error_type=type(e).__name__,
                       status_code=getattr(e, 'status_code', None))
            raise
        except Exception as e:
            # Log unexpected errors and propagate
            logger.exception(f"Unexpected error getting project {project_id}")
            raise

    async def patch(self, project_id: str, ops: Optional[List[Dict[str, Any]]] = None) -> dict:
        """
        Project mutations with typed operations.

        FORMAT: projects.patch(project_id="DEMO", ops=[{"op": "set", "field": "name", "value": "New Name"}])

        Args:
            project_id: Project ID or short name (e.g., "CLUSTER" or "63-2")
            ops: List of typed operations (set, add, remove)

        Returns:
            JSON with updated project data
        """
        try:
            if not ops:
                return {
                    "error": "Operations list is required"
                }

            # Resolve project ID if resolver is available
            resolved_project_id = project_id
            if self.client.id_resolver:
                try:
                    resolved_project_id = await self.client.id_resolver.resolve_project_id(project_id)
                    if resolved_project_id != project_id:
                        logger.info(f"Resolved project '{project_id}' to ID '{resolved_project_id}'")
                except IDResolutionError as e:
                    logger.warning(f"Failed to resolve project ID for '{project_id}', using as-is: {e}")
                    resolved_project_id = project_id
                except (YouTrackAPIError, ValueError) as e:
                    logger.warning(f"Error resolving project ID for '{project_id}': {e}")
                    resolved_project_id = project_id

            # Get current project data
            current_project = await self.projects_api.get_project(resolved_project_id)

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
                return {
                    "error": "No valid operations provided"
                }

            # Apply updates via direct API call
            await self.client.post(f"admin/projects/{project_id}", data=updates)

            # Get updated project
            updated_project = await self.projects_api.get_project(project_id)

            # Convert to dict for JSON response
            if hasattr(updated_project, "model_dump"):
                project_data = updated_project.model_dump()
            else:
                project_data = updated_project.__dict__ if hasattr(updated_project, "__dict__") else str(updated_project)

            return {
                "project": project_data,
                "updated": True,
                "operations_applied": len(ops)
            }

        except YouTrackAPIError as e:
            # Log the error but propagate it so MCP marks as is_error=True
            logger.error(f"YouTrack API error patching project: {project_id}",
                       error_type=type(e).__name__,
                       status_code=getattr(e, 'status_code', None))
            raise
        except Exception as e:
            # Log unexpected errors and propagate
            logger.exception(f"Unexpected error patching project {project_id}")
            raise


    async def schema(self, project_id: str) -> dict:
        """Get project schema with custom fields and validation rules."""
        try:
            # Get custom fields schema
            schemas = self.projects_api.get_all_custom_fields_schemas(project_id)

            # Get basic custom fields list for backward compatibility
            fields = await self.projects_api.get_custom_fields(project_id)

            # Separate required and optional fields
            required_fields = []
            optional_fields = []

            for field_name, schema in schemas.items():
                if schema.get("required", False):
                    required_fields.append({
                        "name": field_name,
                        "type": schema.get("type", "string"),
                        "allowed_values": schema.get("allowed_values", []),
                        "description": f"Required {schema.get('type', 'string')} field"
                    })
                else:
                    optional_fields.append({
                        "name": field_name,
                        "type": schema.get("type", "string"),
                        "allowed_values": schema.get("allowed_values", []),
                        "description": f"Optional {schema.get('type', 'string')} field"
                    })

            return {
                "project_id": project_id,
                "custom_fields": fields,
                "schemas": schemas,
                "required_fields": required_fields,
                "optional_fields": optional_fields,
                "total_fields": len(schemas),
                "required_count": len(required_fields),
                "usage_guide": {
                    "for_issue_creation": "Include required_fields in custom_fields parameter when creating issues",
                    "example": "issues.create(project='CLUSTER', summary='Test', custom_fields={'Type': 'Bug', 'Priority': 'High'})"
                }
            }

        except YouTrackAPIError as e:
            # Log the error but propagate it so MCP marks as is_error=True
            logger.error(f"YouTrack API error getting project schema: {project_id}",
                       error_type=type(e).__name__,
                       status_code=getattr(e, 'status_code', None))
            raise
        except Exception as e:
            # Log unexpected errors and propagate
            logger.exception(f"Unexpected error getting project schema {project_id}")
            raise


    async def create(self, name: str, short_name: str, lead_id: str, description: Optional[str] = None) -> dict:
        """
        Create new projects.

        FORMAT: projects.create(name="Demo Project", short_name="DEMO", lead_id="admin", description="Optional description")

        Args:
            name: Project name
            short_name: Project short name/key
            lead_id: Project leader user ID or login (e.g., "admin" or "cventers")
            description: Optional project description

        Returns:
            JSON with created project data
        """
        try:
            # Resolve lead user ID if resolver is available
            resolved_lead_id = lead_id
            if self.client.id_resolver:
                try:
                    resolved_lead_id = await self.client.id_resolver.resolve_user_id(lead_id)
                    if resolved_lead_id != lead_id:
                        logger.info(f"Resolved lead user '{lead_id}' to ID '{resolved_lead_id}'")
                except IDResolutionError as e:
                    logger.warning(f"Failed to resolve lead user ID for '{lead_id}', using as-is: {e}")
                    resolved_lead_id = lead_id
                except (YouTrackAPIError, ValueError) as e:
                    logger.warning(f"Error resolving lead user ID for '{lead_id}': {e}")
                    resolved_lead_id = lead_id
            project = await self.projects_api.create_project(
                name=name,
                short_name=short_name,
                lead_id=resolved_lead_id,
                description=description
            )

            # Convert to dict for JSON response
            if hasattr(project, "model_dump"):
                project_data = project.model_dump()
            else:
                project_data = project.__dict__ if hasattr(project, "__dict__") else str(project)

            return {
                "project": project_data,
                "created": True
            }

        except YouTrackAPIError as e:
            # Log the error but propagate it so MCP marks as is_error=True
            logger.error(f"YouTrack API error creating project: {name}",
                       error_type=type(e).__name__,
                       status_code=getattr(e, 'status_code', None))
            raise
        except Exception as e:
            # Log unexpected errors and propagate
            logger.exception(f"Unexpected error creating project {name}")
            raise

    def get_tool_definitions(self) -> Dict[str, Dict[str, Any]]:
        """Get core projects tool definitions."""
        return {
            "projects.list": {
                "description": "List accessible projects",
                "function": self.list
            },
            "projects.get": {
                "description": "Get project details with optional expansions. Accepts project short name (e.g., 'ACC') or numeric ID (e.g., '63-13')",
                "function": self.get
            },
            "projects.schema": {
                "description": "Get project schema with custom fields. Accepts project short name (e.g., 'ACC') or numeric ID (e.g., '63-13')",
                "function": self.schema
            },
            "projects.patch": {
                "description": "Update project properties. Accepts project short name (e.g., 'ACC') or numeric ID (e.g., '63-13')",
                "function": self.patch
            },
            "projects.create": {
                "description": "Create new project",
                "function": self.create
            }
        }


__all__ = ["ProjectsTools"]