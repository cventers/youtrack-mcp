"""
LLM-Optimized Error Response System for YouTrack MCP.

This module provides educational error responses that help LLMs learn from mistakes
and provide better user experiences.
"""

import json
import logging
from typing import Dict, Any, Optional, List
from youtrack_mcp.api.client import (
    YouTrackAPIError,
    AuthenticationError,
    PermissionDeniedError,
    ResourceNotFoundError,
    ValidationError,
    ServerError,
    RateLimitError
)

logger = logging.getLogger(__name__)


class LLMErrorEducator:
    """Provides educational error responses optimized for LLM learning."""

    def __init__(self):
        """Initialize the LLM error educator."""
        self.error_patterns = self._initialize_error_patterns()

    def _initialize_error_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Initialize common error patterns and their educational responses."""
        return {
            "project_not_found": {
                "explanation": "Project names in YouTrack are case-sensitive short names (keys), not display names.",
                "examples": [
                    "Use 'DEMO' not 'Demo Project'",
                    "Use 'PROJ' not 'Project Name'"
                ],
                "how_to_find": "Call get_projects() to see all available project keys",
                "common_mistake": "Using display names instead of shortName keys"
            },
            "issue_not_found": {
                "explanation": "Issue IDs must be in the correct format and exist in the system.",
                "examples": [
                    "PROJECT-123 (correct format)",
                    "123 (numeric ID, also valid)",
                    "project-123 (wrong - should be uppercase)"
                ],
                "validation_tips": [
                    "Project prefix must be uppercase",
                    "Issue number follows the hyphen",
                    "Check that the issue actually exists"
                ]
            },
            "authentication_failed": {
                "explanation": "API token authentication is required and must be valid.",
                "token_formats": [
                    "perm:username.workspace.12345... (for cloud)",
                    "perm-base64string (alternative format)",
                    "Check token hasn't expired"
                ],
                "troubleshooting": [
                    "Verify token in YOUTRACK_API_TOKEN environment variable",
                    "Check token file if using YOUTRACK_TOKEN_FILE",
                    "Ensure token has required permissions"
                ]
            },
            "permission_denied": {
                "explanation": "Your API token lacks the required permissions for this operation.",
                "permission_types": [
                    "Read Issue - required for viewing issues",
                    "Create Issue - required for creating issues",
                    "Update Issue - required for modifying issues",
                    "Project Admin - required for project management"
                ],
                "solutions": [
                    "Request additional permissions from your YouTrack administrator",
                    "Use a different API token with appropriate permissions",
                    "Check if you're trying to access restricted projects"
                ]
            },
            "query_syntax_error": {
                "explanation": "YouTrack Query Language (YQL) has specific syntax requirements.",
                "basic_syntax": "field: value",
                "common_operators": [
                    "assignee: username",
                    "state: Open",
                    "project: PROJECT",
                    "created: 2025-01-01 .. *"
                ],
                "custom_fields": [
                    "{Field Name}: value (use curly braces for custom fields)",
                    "Check field names are spelled correctly",
                    "Custom fields are case-sensitive"
                ]
            },
            "rate_limit_exceeded": {
                "explanation": "YouTrack API has rate limits to prevent abuse.",
                "limits": [
                    "Typically 100-1000 requests per minute",
                    "Depends on your YouTrack instance configuration",
                    "Cloud instances may have different limits"
                ],
                "best_practices": [
                    "Implement exponential backoff",
                    "Batch operations when possible",
                    "Cache results to reduce API calls",
                    "Use pagination for large result sets"
                ]
            },
            "server_error": {
                "explanation": "YouTrack server encountered an internal error.",
                "possible_causes": [
                    "Temporary server overload",
                    "Database connectivity issues",
                    "Ongoing maintenance or updates",
                    "Bug in YouTrack server"
                ],
                "recommendations": [
                    "Wait a few minutes and retry",
                    "Check YouTrack status page if available",
                    "Contact your YouTrack administrator",
                    "Try with a simpler request first"
                ]
            }
        }

    def create_educational_error_response(
        self,
        operation: str,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create an educational error response optimized for LLM learning.

        Args:
            operation: The operation that failed (e.g., "get_issue", "create_issue")
            error: The exception that occurred
            context: Additional context about the operation

        Returns:
            Educational error response with examples and guidance
        """
        context = context or {}
        error_type = type(error).__name__

        # Base response structure
        response = {
            "error": str(error),
            "error_type": error_type,
            "operation": operation,
            "context": context,
            "educational_response": True
        }

        # Add specific educational content based on error type
        if isinstance(error, ResourceNotFoundError):
            response.update(self._handle_resource_not_found(operation, error, context))
        elif isinstance(error, AuthenticationError):
            response.update(self._handle_authentication_error(operation, error, context))
        elif isinstance(error, PermissionDeniedError):
            response.update(self._handle_permission_error(operation, error, context))
        elif isinstance(error, ValidationError):
            response.update(self._handle_validation_error(operation, error, context))
        elif isinstance(error, RateLimitError):
            response.update(self._handle_rate_limit_error(operation, error, context))
        elif isinstance(error, ServerError):
            response.update(self._handle_server_error(operation, error, context))
        elif isinstance(error, YouTrackAPIError):
            response.update(self._handle_api_error(operation, error, context))
        else:
            response.update(self._handle_generic_error(operation, error, context))

        return response

    def _handle_resource_not_found(
        self, operation: str, error: ResourceNotFoundError, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle resource not found errors."""
        if "project" in operation.lower():
            pattern = self.error_patterns["project_not_found"]
            return {
                "explanation": pattern["explanation"],
                "examples": pattern["examples"],
                "how_to_find": pattern["how_to_find"],
                "common_mistake": pattern["common_mistake"],
                "suggestion": "Use get_projects() to see all available project keys",
                "learn_from_this": "Always use project shortName (key) not display name in API calls"
            }
        else:
            pattern = self.error_patterns["issue_not_found"]
            return {
                "explanation": pattern["explanation"],
                "examples": pattern["examples"],
                "validation_tips": pattern["validation_tips"],
                "suggestion": "Verify the issue ID format and that the issue exists",
                "learn_from_this": "Issue IDs must be in PROJECT-123 format with uppercase project prefix"
            }

    def _handle_authentication_error(
        self, operation: str, error: AuthenticationError, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle authentication errors."""
        pattern = self.error_patterns["authentication_failed"]
        return {
            "explanation": pattern["explanation"],
            "token_formats": pattern["token_formats"],
            "troubleshooting": pattern["troubleshooting"],
            "suggestion": "Check your YOUTRACK_API_TOKEN environment variable",
            "learn_from_this": "API tokens must be valid and have required permissions"
        }

    def _handle_permission_error(
        self, operation: str, error: PermissionDeniedError, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle permission errors."""
        pattern = self.error_patterns["permission_denied"]
        return {
            "explanation": pattern["explanation"],
            "permission_types": pattern["permission_types"],
            "solutions": pattern["solutions"],
            "suggestion": "Request additional permissions or use a different API token",
            "learn_from_this": "Different operations require different permission levels"
        }

    def _handle_validation_error(
        self, operation: str, error: ValidationError, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle validation errors."""
        if "query" in context or "search" in operation.lower():
            pattern = self.error_patterns["query_syntax_error"]
            return {
                "explanation": pattern["explanation"],
                "basic_syntax": pattern["basic_syntax"],
                "common_operators": pattern["common_operators"],
                "custom_fields": pattern["custom_fields"],
                "suggestion": "Check YouTrack Query Language syntax",
                "learn_from_this": "YQL syntax is case-sensitive and requires specific formats"
            }
        else:
            return {
                "explanation": "The provided data failed validation.",
                "suggestion": "Check that all required fields are provided and values are valid",
                "learn_from_this": "Always validate input data before API calls"
            }

    def _handle_rate_limit_error(
        self, operation: str, error: RateLimitError, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle rate limit errors."""
        pattern = self.error_patterns["rate_limit_exceeded"]
        return {
            "explanation": pattern["explanation"],
            "limits": pattern["limits"],
            "best_practices": pattern["best_practices"],
            "suggestion": "Wait a moment before retrying, or implement exponential backoff",
            "learn_from_this": "API rate limits are enforced to ensure fair usage"
        }

    def _handle_server_error(
        self, operation: str, error: ServerError, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle server errors."""
        pattern = self.error_patterns["server_error"]
        return {
            "explanation": pattern["explanation"],
            "possible_causes": pattern["possible_causes"],
            "recommendations": pattern["recommendations"],
            "suggestion": "Try again later or contact your YouTrack administrator",
            "learn_from_this": "Server errors are usually temporary and can be retried"
        }

    def _handle_api_error(
        self, operation: str, error: YouTrackAPIError, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle general YouTrack API errors."""
        return {
            "explanation": "YouTrack API returned an error response.",
            "youtrack_error": str(error),
            "status_code": getattr(error, 'status_code', None),
            "suggestion": "Check the YouTrack error message for specific guidance",
            "learn_from_this": "YouTrack's error messages are authoritative for its own validation"
        }

    def _handle_generic_error(
        self, operation: str, error: Exception, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle generic/unexpected errors."""
        return {
            "explanation": "An unexpected error occurred.",
            "error_details": str(error),
            "suggestion": "This appears to be an unexpected error. Please report it to the developers.",
            "learn_from_this": "Some errors may indicate bugs in the integration",
            "troubleshooting": [
                "Check your input parameters",
                "Verify your YouTrack instance is accessible",
                "Try with simpler parameters first",
                "Check the logs for additional details"
            ]
        }

    def get_query_syntax_help(self) -> Dict[str, Any]:
        """Get comprehensive YouTrack Query Language help."""
        return {
            "title": "YouTrack Query Language (YQL) Guide",
            "basic_syntax": "field: value",
            "examples": {
                "simple_queries": [
                    "assignee: john.doe",
                    "state: Open",
                    "project: DEMO",
                    "priority: Critical"
                ],
                "date_queries": [
                    "created: 2025-01-01 .. *",
                    "updated: -7d .. *",
                    "due date: * .. 2025-12-31"
                ],
                "custom_fields": [
                    "{Priority}: High",
                    "{Component}: Backend",
                    "{Story Points}: 5"
                ],
                "complex_queries": [
                    "project: DEMO and state: Open and assignee: john.doe",
                    "created: -30d .. * and priority: {High Priority}",
                    "text: login and state: Open"
                ]
            },
            "operators": [
                "and (implicit, can also use explicitly)",
                "or",
                "not",
                "has: field (check if field has a value)",
                "is: value (exact match)"
            ],
            "tips": [
                "Field names are case-sensitive",
                "Use curly braces {} for custom fields",
                "Dates can be relative (-7d for 7 days ago)",
                "Project names must be shortName keys, not display names"
            ]
        }


# Global instance for easy access
llm_error_educator = LLMErrorEducator()


def create_llm_friendly_error(
    operation: str,
    error: Exception,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create an LLM-friendly error response.

    Args:
        operation: The operation that failed
        error: The exception that occurred
        context: Additional context

    Returns:
        Educational error response
    """
    return llm_error_educator.create_educational_error_response(operation, error, context)


def get_query_syntax_help() -> Dict[str, Any]:
    """Get YouTrack Query Language help."""
    return llm_error_educator.get_query_syntax_help()