"""
Utility functions for YouTrack MCP server.
"""
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Union, Optional


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


def add_iso8601_timestamps(data: Union[Dict, List, Any]) -> Union[Dict, List, Any]:
    """
    Recursively add ISO8601 formatted timestamps to YouTrack data.
    
    This function looks for timestamp fields (created, updated) that contain
    epoch timestamps in milliseconds and adds corresponding ISO8601 fields.
    
    Args:
        data: The data structure to process (dict, list, or other)
        
    Returns:
        The data structure with ISO8601 timestamps added
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
        
        # Recursively process nested dictionaries and lists
        for key, value in result.items():
            if isinstance(value, (dict, list)):
                result[key] = add_iso8601_timestamps(value)
        
        return result
    
    elif isinstance(data, list):
        # Process each item in the list
        return [add_iso8601_timestamps(item) for item in data]
    
    else:
        # Return unchanged for other types
        return data


def format_json_response(data: Any) -> str:
    """
    Format data as JSON string with ISO8601 timestamps added.
    
    Args:
        data: The data to format
        
    Returns:
        JSON string with ISO8601 timestamps added
    """
    # Add ISO8601 timestamps to the data
    enhanced_data = add_iso8601_timestamps(data)
    
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