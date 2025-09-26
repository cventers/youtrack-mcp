"""
Utility modules for YouTrack MCP server.
"""

import json
import logging
import re
import yaml
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Union
from dataclasses import dataclass
from cachetools import TTLCache

from .help_resources import get_help_resource
# Tool loader removed - tools are registered via FastMCP

logger = logging.getLogger(__name__)


# Import functions from main utils.py to avoid circular imports
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


def add_iso8601_timestamps(
    data: Union[Dict, List, Any],
    include_numeric: bool = False,
) -> Union[Dict, List, Any]:
    """
    Recursively add or replace timestamps with ISO8601 formatted values.

    This function looks for timestamp fields (created, updated) that contain
    epoch timestamps in milliseconds and either:
    - Replaces them with ISO8601 strings (default, include_numeric=False)
    - Adds corresponding _iso8601 fields alongside numeric values (legacy, include_numeric=True)

    Args:
        data: The data structure to process (dict, list, or other)
        include_numeric: If True, keep numeric timestamps and add _iso8601 fields.
                        If False, replace numeric timestamps with ISO8601 strings.

    Returns:
        The data structure with timestamps formatted according to include_numeric setting
    """
    if isinstance(data, dict):
        # Create a copy to avoid modifying the original
        result = data.copy()

        # Process timestamp fields
        timestamp_fields = ["created", "updated"]
        for field in timestamp_fields:
            if field in result and isinstance(result[field], int):
                iso_value = convert_timestamp_to_iso8601(result[field])

                if include_numeric:
                    # Legacy format: keep numeric, add _iso8601 field
                    iso_field = f"{field}_iso8601"
                    result[iso_field] = iso_value
                else:
                    # New format: replace numeric with ISO8601 string
                    result[field] = iso_value

        # Recursively process nested dictionaries and lists
        for key, value in result.items():
            if isinstance(value, (dict, list)):
                result[key] = add_iso8601_timestamps(value, include_numeric)

        return result

    elif isinstance(data, list):
        # Process each item in the list
        return [add_iso8601_timestamps(item, include_numeric) for item in data]

    else:
        # Return unchanged for other types
        return data


def format_json_response(data: Any, include_numeric: bool = False) -> str:
    """
    Format data as JSON string with ISO8601 timestamps.

    This is a convenience wrapper for add_iso8601_timestamps + json.dumps.
    Consider using add_iso8601_timestamps directly if you don't need a JSON string.

    Args:
        data: The data to format
        include_numeric: If True, keep numeric timestamps alongside ISO8601 (legacy format).
                        If False, replace numeric with ISO8601 (new format).

    Returns:
        JSON string with timestamps formatted according to include_numeric setting
    """
    # Add/replace timestamps based on config
    enhanced_data = add_iso8601_timestamps(data, include_numeric)

    # Return formatted JSON
    return json.dumps(enhanced_data, indent=2)



@dataclass
class ErrorEnhancementResult:
    """Result of error enhancement processing."""
    enhanced_explanation: str
    fix_suggestion: str
    example_correction: str
    learning_tip: str
    confidence: float


class ErrorHandler:
    """
    Rule-based error enhancement for YouTrack API errors.

    Loads error patterns from YAML and provides intelligent error explanations
    and fix suggestions based on pattern matching.
    """

    def __init__(self):
        """Initialize error handler with pattern loading and caching."""
        # Cache for enhanced errors
        self.error_cache = TTLCache(maxsize=500, ttl=1800)  # 30 minutes

        # Load error patterns
        self.error_patterns = self._load_error_patterns()

        logger.info(f"ErrorHandler initialized with {len(self.error_patterns)} error patterns")

    def _load_error_patterns(self) -> List[Dict[str, Any]]:
        """Load error patterns from YAML file."""
        patterns_file = Path(__file__).parent.parent.parent / "data" / "error_patterns.yaml"

        try:
            with open(patterns_file, 'r') as f:
                data = yaml.safe_load(f)

            if not isinstance(data, dict) or 'patterns' not in data:
                raise ValueError("Invalid patterns file structure")

            patterns = data['patterns']
            if not isinstance(patterns, list):
                raise ValueError("Patterns must be a list")

            # Validate each pattern
            for pattern in patterns:
                required_keys = ['id', 'match', 'scope', 'classification', 'explanation', 'remediation_steps']
                for key in required_keys:
                    if key not in pattern:
                        raise ValueError(f"Pattern {pattern.get('id', 'unknown')} missing required key: {key}")

            logger.info(f"Loaded {len(patterns)} error patterns")
            return patterns

        except Exception as e:
            logger.error(f"Failed to load error patterns: {e}")
            raise RuntimeError(f"Cannot load error patterns: {e}")

    def enhance_error(self, error: Union[Exception, str], context: Dict[str, Any]) -> ErrorEnhancementResult:
        """
        Enhance error message using rule-based processing.

        Args:
            error: Error exception or string
            context: Operation context

        Returns:
            Enhanced error result
        """
        error_str = str(error).lower()

        # Find matching pattern
        for pattern in self.error_patterns:
            match_type, match_value = pattern['match'].split('|', 1)

            if match_type == 'regex':
                if re.search(match_value, error_str, re.IGNORECASE):
                    return self._build_error_result_from_pattern(pattern, error, context)
            elif match_type == 'exact':
                if match_value.lower() in error_str:
                    return self._build_error_result_from_pattern(pattern, error, context)

        # Default fallback
        return ErrorEnhancementResult(
            enhanced_explanation=f"Operation failed: {str(error)}",
            fix_suggestion="Please check your input parameters and try again",
            example_correction="",
            learning_tip="Review the error message for specific details",
            confidence=0.5
        )

    def _build_error_result_from_pattern(self, pattern: Dict[str, Any], error: Union[Exception, str], context: Dict[str, Any]) -> ErrorEnhancementResult:
        """Build error result from pattern."""
        explanation = pattern['explanation']
        remediation = pattern['remediation_steps'][0] if pattern['remediation_steps'] else "Check documentation"

        # Generate example correction if possible
        example_correction = ""
        if 'query' in context and pattern['scope'] == 'queries':
            example_correction = self._generate_example_correction(context['query'], pattern['id'])

        return ErrorEnhancementResult(
            enhanced_explanation=explanation,
            fix_suggestion=remediation,
            example_correction=example_correction,
            learning_tip=f"Learn more about {pattern['scope']} in YouTrack documentation",
            confidence=0.8
        )

    def _generate_example_correction(self, original_query: str, pattern_id: str) -> str:
        """Generate example correction based on pattern."""
        if pattern_id == 'syntax_error':
            return original_query.replace('=', ':').replace('"', '{').replace('"', '}')
        elif pattern_id == 'field_unknown':
            corrected = re.sub(r'\bassignee\b', 'assignee', original_query, flags=re.IGNORECASE)
            corrected = re.sub(r'\bstatus\b', 'state', corrected, flags=re.IGNORECASE)
            return corrected
        elif pattern_id == 'date_invalid':
            return re.sub(r'\d{1,2}/\d{1,2}/\d{4}', '2025-01-18', original_query)
        return original_query


__all__ = [
    "get_help_resource",
    "load_all_tools",
    "convert_timestamp_to_iso8601",
    "add_iso8601_timestamps",
    "format_json_response",
    "ErrorEnhancementResult",
    "ErrorHandler"
]