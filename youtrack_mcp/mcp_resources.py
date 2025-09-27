"""
MCP Resources for YouTrack MCP Server.

This module implements MCP Resources that provide context to LLMs without consuming
limited tool slots. Resources are cached and provide reference data like:
- Query syntax documentation
- Available fields for projects
- Project lists
- User directories
"""

import json
from youtrack_mcp.logging import get_logger
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from youtrack_mcp.api.client import YouTrackClient
from youtrack_mcp.api.projects import ProjectsClient
from youtrack_mcp.api.users import UsersClient

logger = get_logger(__name__)


class YouTrackResources:
    """MCP Resources provider for YouTrack context data."""

    def __init__(self):
        """Initialize resources with clients."""
        self.client = YouTrackClient()
        self.projects_api = ProjectsClient(self.client)
        self.users_api = UsersClient(self.client)
        self._cache = {}
        self._cache_ttl = 300  # 5 minutes cache

    def _is_cache_valid(self, key: str) -> bool:
        """Check if cached data is still valid."""
        if key not in self._cache:
            return False

        cached_time = self._cache[key].get('_cached_at', 0)
        now = datetime.now(timezone.utc).timestamp()
        return (now - cached_time) < self._cache_ttl

    def _cache_data(self, key: str, data: Dict[str, Any]) -> None:
        """Cache data with timestamp."""
        data['_cached_at'] = datetime.now(timezone.utc).timestamp()
        self._cache[key] = data

    def _get_cached_data(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached data if valid."""
        if self._is_cache_valid(key):
            cached = self._cache[key].copy()
            cached.pop('_cached_at', None)  # Remove internal timestamp
            return cached
        return None

    async def get_query_syntax_guide(self) -> Dict[str, Any]:
        """
        Get YouTrack Query Language (YQL) syntax guide.

        This resource provides comprehensive documentation for YouTrack's query syntax
        that LLMs can reference when constructing queries.
        """
        cache_key = 'query_syntax'
        cached = self._get_cached_data(cache_key)
        if cached:
            return cached

        # Static query syntax documentation
        syntax_guide = {
            "resource_type": "documentation",
            "title": "YouTrack Query Language (YQL) Syntax Guide",
            "description": "Complete reference for YouTrack query syntax and operators",
            "last_updated": "2025-01-15",

            "basic_syntax": {
                "field_operators": {
                    "equals": "field: value",
                    "not_equals": "field: -value",
                    "contains": "field: *value*",
                    "starts_with": "field: value*",
                    "ends_with": "field: *value",
                    "greater_than": "field: >value",
                    "less_than": "field: <value",
                    "range": "field: value1 .. value2"
                },

                "logical_operators": {
                    "and": "field1: value1 field2: value2",
                    "or": "field1: value1 or field2: value2",
                    "not": "not field: value",
                    "grouping": "(field1: value1 or field2: value2) and field3: value3"
                }
            },

            "common_fields": {
                "issue_fields": [
                    "id", "summary", "description", "created", "updated", "resolved",
                    "priority", "state", "type", "assignee", "reporter", "project"
                ],
                "date_fields": [
                    "created", "updated", "resolved", "due date"
                ],
                "user_fields": [
                    "assignee", "reporter", "updater", "resolver"
                ]
            },

            "date_formats": {
                "youtrack_format": "YYYY-MM-DD",
                "examples": [
                    "created: 2025-06-13",
                    "updated: -7d .. *",
                    "created: 2025-01-01 .. 2025-12-31",
                    "due date: >2025-06-01"
                ],
                "relative_dates": [
                    "-1d (yesterday)",
                    "-7d (last week)",
                    "-30d (last month)",
                    "* (current time)"
                ]
            },

            "custom_fields": {
                "syntax": "{Field Name}: value",
                "examples": [
                    "{Priority}: High",
                    "{Component}: Backend",
                    "{Severity}: Critical"
                ],
                "notes": "Custom field names are case-sensitive and must match exactly"
            },

            "query_examples": {
                "basic_search": "project: MYPROJECT state: Open",
                "complex_filter": "project: MYPROJECT state: Open assignee: john.doe created: -7d .. *",
                "custom_fields": "project: MYPROJECT {Priority}: High {Component}: Backend",
                "date_range": "created: 2025-01-01 .. 2025-12-31 state: Resolved",
                "user_search": "assignee: john.doe or reporter: jane.smith",
                "text_search": "summary: *bug* description: *crash*"
            },

            "common_mistakes": {
                "wrong_operators": "Don't use '=' instead of ':' (use 'assignee: john.doe' not 'assignee = john.doe')",
                "case_sensitivity": "Project names and field names are case-sensitive",
                "date_formats": "Use YYYY-MM-DD format, not MM/DD/YYYY",
                "custom_fields": "Use curly braces for custom fields: {Priority}: High"
            },

            "best_practices": {
                "specific_queries": "Be specific with project names to avoid large result sets",
                "date_ranges": "Use date ranges to limit results: created: -30d .. *",
                "field_combination": "Combine multiple fields for precise filtering",
                "test_queries": "Test queries with small date ranges first"
            }
        }

        self._cache_data(cache_key, syntax_guide)
        return syntax_guide

    async def get_project_fields(self, project_id: str) -> Dict[str, Any]:
        """
        Get available custom fields for a specific project.

        Args:
            project_id: YouTrack project ID (e.g., "MYPROJECT")

        Returns:
            Project field information including custom fields
        """
        cache_key = f'project_fields_{project_id}'
        cached = self._get_cached_data(cache_key)
        if cached:
            return cached

        try:
            # Get project info
            project_info = await self.projects_api.get_project(project_id)

            field_info = {
                "resource_type": "project_fields",
                "project_id": project_id,
                "project_name": project_info.name,
                "custom_fields": [],

                "built_in_fields": {
                    "issue_fields": [
                        {"name": "id", "type": "string", "description": "Issue ID (e.g., PROJECT-123)"},
                        {"name": "summary", "type": "string", "description": "Issue title/summary"},
                        {"name": "description", "type": "text", "description": "Issue description"},
                        {"name": "created", "type": "date", "description": "Creation date"},
                        {"name": "updated", "type": "date", "description": "Last update date"},
                        {"name": "resolved", "type": "date", "description": "Resolution date"},
                        {"name": "priority", "type": "enum", "description": "Issue priority"},
                        {"name": "state", "type": "state", "description": "Issue state/workflow"},
                        {"name": "type", "type": "enum", "description": "Issue type"},
                        {"name": "assignee", "type": "user", "description": "Assigned user"},
                        {"name": "reporter", "type": "user", "description": "Issue reporter"}
                    ]
                },

                "query_examples": [
                    f"project: {project_id} state: Open",
                    f"project: {project_id} assignee: john.doe",
                    f"project: {project_id} created: -7d .. *"
                ],

                "note": "Custom fields information requires additional API calls. Use get_issue() to see actual custom fields for specific issues."
            }

            self._cache_data(cache_key, field_info)
            return field_info

        except Exception as e:
            logger.warning("failed_to_get_project_fields_for_project_id_e", project_id=project_id, e=e)
            return {
                "resource_type": "project_fields",
                "project_id": project_id,
                "error": f"Could not retrieve project fields: {str(e)}",
                "fallback_fields": [
                    "id", "summary", "description", "created", "updated",
                    "priority", "state", "type", "assignee", "reporter"
                ]
            }

    async def get_projects_list(self) -> Dict[str, Any]:
        """
        Get list of all available projects.

        Returns:
            Comprehensive project list with metadata
        """
        cache_key = 'projects_list'
        cached = self._get_cached_data(cache_key)
        if cached:
            return cached

        try:
            projects = await self.projects_api.get_projects()

            projects_info = {
                "resource_type": "projects_list",
                "total_projects": len(projects),
                "projects": [],

                "query_examples": [
                    "project: MYPROJECT state: Open",
                    "project: MYPROJECT or project: OTHERPROJECT",
                    "#MYPROJECT-123 (direct issue reference)"
                ],

                "common_patterns": {
                    "by_short_name": "Use project short name (key) in queries, not display name",
                    "case_sensitive": "Project names are case-sensitive",
                    "direct_reference": "Use #PROJECT-123 for direct issue references"
                }
            }

            for project in projects:
                project_data = {
                    "id": project.id,
                    "name": project.name,
                    "short_name": project.shortName,
                    "description": project.description,
                    "query_syntax": f"project: {project.shortName}"
                }
                projects_info["projects"].append(project_data)

            self._cache_data(cache_key, projects_info)
            return projects_info

        except Exception as e:
            logger.warning("failed_to_get_projects_list_e", e=e)
            return {
                "resource_type": "projects_list",
                "error": f"Could not retrieve projects: {str(e)}",
                "total_projects": 0,
                "projects": []
            }

    async def get_users_directory(self) -> Dict[str, Any]:
        """
        Get directory of all users.

        Returns:
            User directory with login names and metadata
        """
        cache_key = 'users_directory'
        cached = self._get_cached_data(cache_key)
        if cached:
            return cached

        try:
            # Use search_users with empty query to get all users (limited to 100 for performance)
            users = await self.users_api.search_users("", limit=100)

            users_info = {
                "resource_type": "users_directory",
                "total_users": len(users),
                "users": [],

                "query_examples": [
                    "assignee: john.doe",
                    "reporter: jane.smith",
                    "assignee: john.doe or assignee: jane.smith"
                ],

                "common_patterns": {
                    "login_names": "Use login names (john.doe) not display names",
                    "case_sensitive": "User login names are case-sensitive",
                    "multiple_users": "Use 'or' to search for multiple users"
                },

                "note": "Limited to first 100 users for performance. Use search_users() for more specific queries."
            }

            for user in users:
                user_data = {
                    "login": user.login,
                    "name": user.name,
                    "email": user.email,
                    "query_syntax": f"assignee: {user.login}"
                }
                users_info["users"].append(user_data)

            self._cache_data(cache_key, users_info)
            return users_info

        except Exception as e:
            logger.warning("failed_to_get_users_directory_e", e=e)
            return {
                "resource_type": "users_directory",
                "error": f"Could not retrieve users: {str(e)}",
                "total_users": 0,
                "users": []
            }


# Global resources instance
youtrack_resources = YouTrackResources()


# MCP Resource handlers
async def handle_query_syntax_resource() -> str:
    """Handle youtrack://query-syntax resource request."""
    data = await youtrack_resources.get_query_syntax_guide()
    return json.dumps(data, indent=2)


async def handle_project_fields_resource(project_id: str) -> str:
    """Handle youtrack://project/{id}/fields resource request."""
    data = await youtrack_resources.get_project_fields(project_id)
    return json.dumps(data, indent=2)


async def handle_projects_list_resource() -> str:
    """Handle youtrack://projects resource request."""
    data = await youtrack_resources.get_projects_list()
    return json.dumps(data, indent=2)


async def handle_users_directory_resource() -> str:
    """Handle youtrack://users resource request."""
    data = await youtrack_resources.get_users_directory()
    return json.dumps(data, indent=2)