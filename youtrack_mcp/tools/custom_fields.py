"""
Custom Fields Tools for YouTrack MCP Server.

This module provides comprehensive custom field management capabilities,
including generic field updates, field validation, and field type handling.
"""

from youtrack_mcp.logging import get_logger
import re
from typing import Dict, Any, List, Optional, Union

from youtrack_mcp.api.client import YouTrackClient
from youtrack_mcp.api.issues import IssuesClient
from youtrack_mcp.api.projects import ProjectsClient

logger = get_logger(__name__)


class CustomFieldsTools:
    """Tools for managing YouTrack custom fields."""

    def __init__(self):
        """Initialize custom fields tools."""
        self.client = YouTrackClient()
        self.issues_api = IssuesClient(self.client)

    async def update_custom_field(self, issue_id: str, field_name: str, field_value: Union[str, int, float, bool, List[str]]) -> Dict[str, Any]:
        """
        Update a custom field value for an issue.

        FORMAT: custom_fields.update_custom_field(issue_id="PROJECT-123", field_name="Priority", field_value="High")

        This tool provides generic custom field update capability supporting all YouTrack field types:
        - Text fields (string values)
        - Enum fields (predefined values)
        - User fields (user login names)
        - Date fields (ISO format dates)
        - Number fields (integers/floats)
        - Boolean fields (true/false)
        - Multi-value fields (arrays of values)

        Args:
            issue_id: Issue ID (e.g., "PROJECT-123")
            field_name: Custom field name (case-sensitive, use exact name)
            field_value: New field value (type depends on field type)

        Returns:
            Update result with validation and success confirmation

        Examples:
            # Text field
            update_custom_field("PROJ-123", "Description", "Updated description")

            # Enum field
            update_custom_field("PROJ-123", "Priority", "High")

            # User field
            update_custom_field("PROJ-123", "Assignee", "john.doe")

            # Date field
            update_custom_field("PROJ-123", "Due Date", "2025-06-13")

            # Number field
            update_custom_field("PROJ-123", "Story Points", 5)

            # Boolean field
            update_custom_field("PROJ-123", "Ready for Review", true)

            # Multi-value field
            update_custom_field("PROJ-123", "Tags", ["frontend", "urgent"])
        """
        try:
            # First get the issue to understand current custom fields
            issue_data = await self.issues_api.get_issue(issue_id)

            if not issue_data or not hasattr(issue_data, 'custom_fields') or not issue_data.custom_fields:
                return {
                    "error": f"Issue {issue_id} not found or has no custom fields",
                    "issue_id": issue_id,
                    "field_name": field_name,
                    "recommendation": "Verify the issue ID is correct and check available custom fields with get_issue()"
                }

            # Find the target field
            target_field = None
            for field in issue_data.custom_fields or []:
                if isinstance(field, dict) and field.get('name') == field_name:
                    target_field = field
                    break

            if not target_field:
                available_fields = [f.get('name', '') if isinstance(f, dict) else str(f) for f in issue_data.custom_fields or []]
                return {
                    "error": f"Custom field '{field_name}' not found on issue {issue_id}",
                    "issue_id": issue_id,
                    "field_name": field_name,
                    "available_fields": available_fields,
                    "recommendation": f"Use one of the available fields: {', '.join(available_fields[:5])}",
                    "note": "Custom field names are case-sensitive"
                }

            # Validate field value based on field type
            field_type = target_field.get('fieldType', {}).get('id', 'unknown')
            validation_result = self._validate_field_value(field_value, field_type)

            if not validation_result['valid']:
                return {
                    "error": f"Invalid value for {field_type} field '{field_name}'",
                    "issue_id": issue_id,
                    "field_name": field_name,
                    "field_type": field_type,
                    "provided_value": field_value,
                    "validation_error": validation_result['error'],
                    "recommendation": validation_result['recommendation']
                }

            # Prepare the update payload
            update_payload = {
                "id": issue_id,
                "customFields": [{
                    "name": field_name,
                    "$type": target_field.get('$type', 'CustomField'),
                    "value": self._format_field_value(field_value, field_type)
                }]
            }

            # Perform the update
            result = await self.issues_api.update_issue_custom_fields(issue_id, update_payload)

            return {
                "success": True,
                "issue_id": issue_id,
                "field_name": field_name,
                "field_type": field_type,
                "old_value": target_field.get('value'),
                "new_value": field_value,
                "update_result": result,
                "message": f"Successfully updated {field_name} to {field_value}"
            }

        except Exception as e:
            logger.exception(f"Error updating custom field {field_name} on issue {issue_id}")
            return {
                "error": f"Failed to update custom field: {str(e)}",
                "issue_id": issue_id,
                "field_name": field_name,
                "field_value": field_value,
                "recommendation": "Check field name spelling, ensure field exists, and verify value format matches field type"
            }

    async def get_custom_fields(self, issue_id: str) -> Dict[str, Any]:
        """
        Get all custom fields for an issue with their current values and types.

        FORMAT: custom_fields.get_custom_fields(issue_id="PROJECT-123")

        Args:
            issue_id: Issue ID (e.g., "PROJECT-123")

        Returns:
            Complete custom fields information with types and values

        Examples:
            get_custom_fields("PROJ-123") → All custom fields with current values
        """
        try:
            issue_data = await self.issues_api.get_issue(issue_id)

            if not issue_data:
                return {
                    "error": f"Issue {issue_id} not found",
                    "issue_id": issue_id
                }

            custom_fields = issue_data.custom_fields or []

            fields_info = {
                "issue_id": issue_id,
                "total_custom_fields": len(custom_fields),
                "custom_fields": []
            }

            for field in custom_fields:
                field_info = {
                    "name": field.get('name', ''),
                    "type": field.get('fieldType', {}).get('id', 'unknown'),
                    "value": field.get('value'),
                    "has_value": field.get('value') is not None,
                    "update_syntax": f"update_custom_field('{issue_id}', '{field.get('name', '')}', value)"
                }
                fields_info["custom_fields"].append(field_info)

            return fields_info

        except Exception as e:
            logger.exception(f"Error getting custom fields for issue {issue_id}")
            return {
                "error": f"Failed to get custom fields: {str(e)}",
                "issue_id": issue_id
            }

    async def validate_field_value(self, field_name: str, field_value: Union[str, int, float, bool, List[str]], project_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Validate a custom field value without updating the issue.

        FORMAT: custom_fields.validate_field_value(field_name="Priority", field_value="High", project_id="MYPROJECT")

        Args:
            field_name: Custom field name
            field_value: Value to validate
            project_id: Optional project ID for field type lookup

        Returns:
            Validation result with field type information

        Examples:
            validate_field_value("Priority", "High") → Validation result
            validate_field_value("Due Date", "2025-06-13") → Date validation
        """
        # This is a simplified validation - in practice you'd look up field types from project
        # For now, we'll do basic type validation

        if project_id:
            # Look up actual field type from project schema
            try:
                # Get project field schemas
                projects_client = ProjectsClient(YouTrackClient())
                all_schemas = projects_client.get_all_custom_fields_schemas(project_id)

                # Find the specific field
                for field_schema in all_schemas.values():
                    if field_schema.get("name") == field_name:
                        actual_field_type = field_schema.get("type", "text")
                        logger.info("Found actual field type", field_name=field_name, field_type=actual_field_type)
                        validation = self._validate_field_value(field_value, actual_field_type)

                        return {
                            "field_name": field_name,
                            "field_value": field_value,
                            "actual_type": actual_field_type,
                            "validation": validation,
                            "source": "project_schema"
                        }
            except Exception as e:
                logger.warning("failed_to_lookup_field_type_from_project_schema_e_", e=e)

        # Fallback: Basic validation based on value type
        if isinstance(field_value, str):
            field_type_guess = "text"
        elif isinstance(field_value, int):
            field_type_guess = "integer"
        elif isinstance(field_value, float):
            field_type_guess = "float"
        elif isinstance(field_value, bool):
            field_type_guess = "boolean"
        elif isinstance(field_value, list):
            field_type_guess = "multi-value"
        else:
            field_type_guess = "unknown"

        validation = self._validate_field_value(field_value, field_type_guess)

        return {
            "field_name": field_name,
            "field_value": field_value,
            "field_type": field_type_guess,
            "validation": validation,
            "recommendation": "Use update_custom_field() to apply this value to an issue"
        }

    def _validate_field_value(self, value: Union[str, int, float, bool, List[str]], field_type: str) -> Dict[str, Any]:
        """Validate a field value based on its type."""
        try:
            if field_type in ['text', 'string']:
                if not isinstance(value, str):
                    return {
                        "valid": False,
                        "error": f"Text field expects string value, got {type(value).__name__}",
                        "recommendation": f"Provide a string value like '{value}'"
                    }

            elif field_type in ['integer', 'int']:
                if not isinstance(value, int):
                    return {
                        "valid": False,
                        "error": f"Integer field expects int value, got {type(value).__name__}",
                        "recommendation": f"Provide an integer value like {int(value) if isinstance(value, (float, str)) and str(value).isdigit() else '42'}"
                    }

            elif field_type in ['float', 'number']:
                if not isinstance(value, (int, float)):
                    return {
                        "valid": False,
                        "error": f"Number field expects numeric value, got {type(value).__name__}",
                        "recommendation": f"Provide a numeric value like {float(value) if isinstance(value, str) and value.replace('.', '').isdigit() else '3.14'}"
                    }

            elif field_type == 'boolean':
                if not isinstance(value, bool):
                    return {
                        "valid": False,
                        "error": f"Boolean field expects true/false, got {type(value).__name__}",
                        "recommendation": f"Provide a boolean value like {str(value).lower() in ['true', '1', 'yes']}"
                    }

            elif field_type in ['date', 'datetime']:
                if not isinstance(value, str):
                    return {
                        "valid": False,
                        "error": f"Date field expects string value, got {type(value).__name__}",
                        "recommendation": "Provide a date string like '2025-06-13' or '2025-06-13T10:30:00Z'"
                    }
                # Basic ISO date validation
                if not (re.match(r'^\d{4}-\d{2}-\d{2}', value) or re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', value)):
                    return {
                        "valid": False,
                        "error": "Date format should be YYYY-MM-DD or ISO 8601",
                        "recommendation": "Use format like '2025-06-13' or '2025-06-13T10:30:00Z'"
                    }

            elif field_type in ['enum', 'state']:
                if not isinstance(value, str):
                    return {
                        "valid": False,
                        "error": f"Enum field expects string value, got {type(value).__name__}",
                        "recommendation": f"Provide a valid enum value as a string like '{value}'"
                    }

            elif field_type == 'user':
                if not isinstance(value, str):
                    return {
                        "valid": False,
                        "error": f"User field expects string login name, got {type(value).__name__}",
                        "recommendation": f"Provide a user login name like '{value}'"
                    }

            elif 'multi' in field_type.lower() or isinstance(value, list):
                if not isinstance(value, list):
                    return {
                        "valid": False,
                        "error": f"Multi-value field expects array, got {type(value).__name__}",
                        "recommendation": f"Provide an array of values like ['{value}']"
                    }

            # If we get here, validation passed
            return {
                "valid": True,
                "field_type": field_type,
                "message": f"Value is valid for {field_type} field"
            }

        except Exception as e:
            return {
                "valid": False,
                "error": f"Validation error: {str(e)}",
                "recommendation": "Check the field type and value format"
            }

    def _format_field_value(self, value: Union[str, int, float, bool, List[str]], field_type: str) -> Any:
        """Format a field value for YouTrack API."""
        if field_type in ['text', 'string', 'enum', 'state', 'user']:
            return str(value)
        elif field_type in ['integer', 'int']:
            return int(value) if isinstance(value, (str, int)) else 0
        elif field_type in ['float', 'number']:
            return float(value) if isinstance(value, (str, int, float)) else 0.0
        elif field_type == 'boolean':
            return bool(value)
        elif field_type in ['date', 'datetime']:
            return str(value)  # Assume it's already in correct format
        elif 'multi' in field_type.lower() or isinstance(value, list):
            return [str(v) for v in value] if isinstance(value, list) else [str(value)]
        else:
            return value