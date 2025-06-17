"""
Utility functions for YouTrack MCP server.
"""
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Union, Optional


def current_datetime() -> str:
    """
    Get the current datetime as an ISO8601 formatted string in UTC.
    
    Returns:
        ISO8601 formatted timestamp string in UTC timezone
    """
    return datetime.now(timezone.utc).isoformat()


def convert_timestamp_to_iso8601(timestamp_ms: int) -> str:
    """
    Convert YouTrack epoch timestamp (in milliseconds) to ISO8601 format in UTC.
    
    Args:
        timestamp_ms: Timestamp in milliseconds since Unix epoch
        
    Returns:
        ISO8601 formatted timestamp string in UTC timezone
    """
    try:
        # Convert milliseconds to seconds
        timestamp_seconds = timestamp_ms / 1000
        # Create datetime object in UTC and format as ISO8601
        dt = datetime.fromtimestamp(timestamp_seconds, tz=timezone.utc)
        return dt.isoformat()
    except (ValueError, OSError, OverflowError):
        # Return original timestamp as string if conversion fails
        return str(timestamp_ms)


def add_iso8601_timestamps(data: Union[Dict, List, Any], no_epoch: bool = True) -> Union[Dict, List, Any]:
    """
    Recursively add ISO8601 formatted timestamps to YouTrack data.
    
    This function looks for timestamp fields (created, updated) that contain
    epoch timestamps in milliseconds and adds corresponding ISO8601 fields.
    When no_epoch is True, the original epoch values are removed.
    
    Args:
        data: The data structure to process (dict, list, or other)
        no_epoch: If True, remove epoch values and only keep ISO8601 timestamps
        
    Returns:
        The data structure with ISO8601 timestamps added (and epoch removed if no_epoch=True)
    """
    if isinstance(data, dict):
        # Create a copy to avoid modifying the original
        result = data.copy()
        
        # Process timestamp fields
        timestamp_fields = ['created', 'updated']
        for field in timestamp_fields:
            if field in result and isinstance(result[field], int):
                iso_field = f"{field}_iso8601"
                result[iso_field] = convert_timestamp_to_iso8601(result[field])
                
                # Remove epoch value if no_epoch is True
                if no_epoch:
                    del result[field]
        
        # Recursively process nested dictionaries and lists
        for key, value in result.items():
            if isinstance(value, (dict, list)):
                result[key] = add_iso8601_timestamps(value, no_epoch)
        
        return result
    
    elif isinstance(data, list):
        # Process each item in the list
        return [add_iso8601_timestamps(item, no_epoch) for item in data]
    
    else:
        # Return unchanged for other types
        return data


def format_json_response(data: Any) -> str:
    """
    Format data as JSON string with ISO8601 timestamps added.
    Respects the no_epoch configuration setting.
    
    Args:
        data: The data to format
        
    Returns:
        JSON string with ISO8601 timestamps added (epoch removed if configured)
    """
    # Import config to check no_epoch setting
    from .config import config
    
    # Add ISO8601 timestamps to the data, respecting no_epoch setting
    enhanced_data = add_iso8601_timestamps(data, no_epoch=config.NO_EPOCH)
    
    # Return formatted JSON
    return json.dumps(enhanced_data, indent=2)


def get_field_value_text(custom_fields: List[Dict[str, Any]], field_name: str) -> Optional[str]:
    """
    Get the human-readable text value for a custom field by name.
    
    Args:
        custom_fields: List of custom fields from an issue
        field_name: Name of the field to get the value for (e.g., "State", "Priority")
        
    Returns:
        Human-readable field value or None if not found
    """
    if not isinstance(custom_fields, list):
        return None
    
    for field in custom_fields:
        if isinstance(field, dict) and field.get("name") == field_name:
            # First try the resolved text value
            if "value_text" in field:
                return field["value_text"]
            
            # Fallback to original value if it has a name
            value = field.get("value", {})
            if isinstance(value, dict) and "name" in value:
                return value["name"]
    
    return None


def get_field_by_name(custom_fields: List[Dict[str, Any]], field_name: str) -> Optional[Dict[str, Any]]:
    """
    Get a custom field by name from the list of custom fields.
    
    Args:
        custom_fields: List of custom fields from an issue
        field_name: Name of the field to find
        
    Returns:
        The field dictionary or None if not found
    """
    if not isinstance(custom_fields, list):
        return None
    
    for field in custom_fields:
        if isinstance(field, dict) and field.get("name") == field_name:
            return field
    
    return None


def extract_field_summary(custom_fields: List[Dict[str, Any]]) -> Dict[str, str]:
    """
    Extract a summary of all resolved field values for easy reading.
    
    Args:
        custom_fields: List of custom fields from an issue
        
    Returns:
        Dictionary mapping field names to their human-readable values
    """
    summary = {}
    
    if not isinstance(custom_fields, list):
        return summary
    
    for field in custom_fields:
        if isinstance(field, dict):
            field_name = field.get("name")
            if field_name:
                # Try the resolved text value first
                if "value_text" in field:
                    summary[field_name] = field["value_text"]
                else:
                    # Fallback to original value if it has a name
                    value = field.get("value", {})
                    if isinstance(value, dict) and "name" in value:
                        summary[field_name] = value["name"]
    
    return summary


def generate_ticket_suggestions(issue_data: Dict[str, Any], project: Optional[str] = None, issue_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Generate attribute suggestions for a ticket based on what's missing and configuration.
    
    Args:
        issue_data: The issue data provided by the model
        project: Optional project identifier for project-specific suggestions
        
    Returns:
        Dictionary containing suggestions and example MCP calls
    """
    from .config import config
    
    if not config.SUGGESTIONS_ENABLED or not config.SUGGESTIONS_CONFIG:
        return {}
    
    suggestions_config = config.SUGGESTIONS_CONFIG
    ticket_attributes = suggestions_config.get('ticket_attributes', {})
    behavior = suggestions_config.get('behavior', {})
    project_overrides = suggestions_config.get('project_overrides', {})
    
    # Apply project-specific overrides if available
    if project and project_overrides and project in project_overrides:
        overrides = project_overrides[project]
        # Deep merge the overrides with the base configuration
        for attr, override_config in overrides.items():
            if attr in ticket_attributes:
                ticket_attributes[attr] = {**ticket_attributes[attr], **override_config}
    
    suggestions = []
    suggested_calls = []
    
    # Check each configured attribute
    for attr_name, attr_config in ticket_attributes.items():
        if not attr_config.get('enabled', True):
            continue
            
        # Skip if attribute was already provided by the model
        if _is_attribute_provided(issue_data, attr_name):
            continue
        
        # Generate suggestion for this attribute
        suggestion = _generate_attribute_suggestion(attr_name, attr_config, issue_data)
        if suggestion:
            suggestions.append(suggestion)
            
            # Generate example MCP call if enabled
            if behavior.get('include_example_calls', True):
                example_call = _generate_example_mcp_call(attr_name, attr_config, issue_data, issue_id)
                if example_call:
                    suggested_calls.append(example_call)
    
    # Limit suggestions based on configuration
    max_suggestions = behavior.get('max_suggestions', 5)
    if len(suggestions) > max_suggestions:
        suggestions = suggestions[:max_suggestions]
        suggested_calls = suggested_calls[:max_suggestions]
    
    # Format the response based on configuration
    result = {
        'suggestions_available': len(suggestions) > 0,
        'suggestion_count': len(suggestions)
    }
    
    if suggestions:
        format_type = behavior.get('format', 'structured')
        
        if format_type == 'structured':
            result.update({
                'attribute_suggestions': suggestions,
                'suggested_mcp_calls': suggested_calls,
                'suggestion_note': 'These suggestions can help improve the issue completeness and tracking.'
            })
        elif format_type == 'narrative':
            result['suggestion_text'] = _format_narrative_suggestions(suggestions)
            if suggested_calls:
                result['suggested_mcp_calls'] = suggested_calls
        elif format_type == 'minimal':
            result['missing_attributes'] = [s['attribute'] for s in suggestions]
            if suggested_calls:
                result['suggested_mcp_calls'] = suggested_calls
    
    return result


def _is_attribute_provided(issue_data: Dict[str, Any], attr_name: str) -> bool:
    """
    Check if an attribute was provided in the issue data.
    
    Args:
        issue_data: The issue data from the model
        attr_name: The attribute name to check
        
    Returns:
        True if the attribute was provided, False otherwise
    """
    # Map config attribute names to YouTrack API field names
    field_mapping = {
        'priority': ['priority'],
        'component': ['component', 'components'],
        'type': ['type', 'issue_type'],
        'tags': ['tags'],
        'assignee': ['assignee', 'assigned_to'],
        'due_date': ['due_date', 'dueDate'],
        'estimation': ['estimation', 'estimated_time', 'timeEstimate']
    }
    
    possible_fields = field_mapping.get(attr_name, [attr_name])
    
    for field in possible_fields:
        if field in issue_data and issue_data[field] is not None:
            # For list fields, check if non-empty
            if isinstance(issue_data[field], list):
                return len(issue_data[field]) > 0
            # For string fields, check if non-empty
            elif isinstance(issue_data[field], str):
                return len(issue_data[field].strip()) > 0
            # For other types, just check if not None
            else:
                return True
    
    return False


def _generate_attribute_suggestion(attr_name: str, attr_config: Dict[str, Any], issue_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Generate a suggestion for a specific attribute.
    
    Args:
        attr_name: The attribute name
        attr_config: The attribute configuration
        issue_data: The issue data
        
    Returns:
        Suggestion dictionary or None
    """
    suggestion = {
        'attribute': attr_name,
        'prompt': attr_config.get('prompt', f'Consider setting {attr_name}'),
        'reason': f'No {attr_name} was specified in the issue creation'
    }
    
    # Add default value if available
    if 'default' in attr_config and attr_config['default'] is not None:
        suggestion['suggested_value'] = attr_config['default']
    
    # Add options if available
    if 'options' in attr_config:
        suggestion['available_options'] = attr_config['options']
    
    # Add context-specific reasoning
    if attr_name == 'priority':
        # Analyze issue content for priority hints
        summary = issue_data.get('summary', '').lower()
        description = issue_data.get('description', '').lower()
        content = f"{summary} {description}"
        
        if any(word in content for word in ['critical', 'urgent', 'blocking', 'broken', 'down']):
            suggestion['suggested_value'] = 'Critical'
            suggestion['reason'] = 'Issue appears to be critical based on description'
        elif any(word in content for word in ['bug', 'error', 'issue', 'problem']):
            suggestion['suggested_value'] = 'High'
            suggestion['reason'] = 'Bug reports typically warrant higher priority'
        
    elif attr_name == 'type':
        # Analyze content for type hints
        summary = issue_data.get('summary', '').lower()
        description = issue_data.get('description', '').lower()
        content = f"{summary} {description}"
        
        if any(word in content for word in ['feature', 'enhancement', 'add', 'implement']):
            suggestion['suggested_value'] = 'Feature'
        elif any(word in content for word in ['bug', 'error', 'broken', 'issue']):
            suggestion['suggested_value'] = 'Bug'
        elif any(word in content for word in ['task', 'todo', 'chore']):
            suggestion['suggested_value'] = 'Task'
    
    return suggestion


def _generate_example_mcp_call(attr_name: str, attr_config: Dict[str, Any], issue_data: Dict[str, Any], issue_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Generate an example MCP call for updating the attribute.
    
    Args:
        attr_name: The attribute name
        attr_config: The attribute configuration
        issue_data: The issue data
        
    Returns:
        Example MCP call dictionary or None
    """
    # Map config attribute names to YouTrack API field names
    field_mapping = {
        'priority': 'priority',
        'component': 'component',
        'type': 'type',
        'tags': 'tags',
        'assignee': 'assignee',
        'due_date': 'due_date',
        'estimation': 'estimation'
    }
    
    api_field = field_mapping.get(attr_name, attr_name)
    suggested_value = attr_config.get('default')
    
    # Use contextual suggestion if available
    suggestion = _generate_attribute_suggestion(attr_name, attr_config, issue_data)
    if suggestion and 'suggested_value' in suggestion:
        suggested_value = suggestion['suggested_value']
    
    if suggested_value is not None:
        return {
            'tool': 'youtrack.update_issue',
            'parameters': {
                'issue_id': issue_id or '@last_created_issue',  # Use actual issue ID if provided
                api_field: suggested_value
            },
            'description': f'Update the issue to set {attr_name} to {suggested_value}'
        }
    
    return None


def _format_narrative_suggestions(suggestions: List[Dict[str, Any]]) -> str:
    """
    Format suggestions as a narrative text.
    
    Args:
        suggestions: List of suggestion dictionaries
        
    Returns:
        Formatted narrative text
    """
    if not suggestions:
        return ""
    
    parts = []
    for suggestion in suggestions:
        attr = suggestion['attribute']
        prompt = suggestion['prompt']
        
        if 'suggested_value' in suggestion:
            value = suggestion['suggested_value']
            parts.append(f"• {prompt}. Suggested: {value}")
        else:
            parts.append(f"• {prompt}")
    
    return "Consider the following improvements to this issue:\n" + "\n".join(parts)