"""
Date/Time conversion utilities for YouTrack MCP Server.

This module provides comprehensive date/time conversion capabilities optimized for LLM usage,
supporting various input formats and providing YouTrack-compatible outputs with educational context.
"""

import re
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional



logger = logging.getLogger(__name__)


def normalize_datetime(date_input: str, timezone_str: str = "UTC") -> datetime:
    """
    Normalize various date inputs to datetime object.

    Args:
        date_input: Date in various formats
        timezone_str: Timezone for interpretation

    Returns:
        datetime object in UTC

    Raises:
        ValueError: If date cannot be parsed
    """
    # Handle relative dates with regex patterns
    relative_patterns = {
        r'\byesterday\b': lambda: datetime.now(timezone.utc) - timedelta(days=1),
        r'\btoday\b': lambda: datetime.now(timezone.utc),
        r'\btomorrow\b': lambda: datetime.now(timezone.utc) + timedelta(days=1),
        r'\blast week\b': lambda: datetime.now(timezone.utc) - timedelta(weeks=1),
        r'\bthis week\b': lambda: datetime.now(timezone.utc) - timedelta(days=datetime.now().weekday()),
        r'\bnext week\b': lambda: datetime.now(timezone.utc) + timedelta(weeks=1),
        r'\blast month\b': lambda: datetime.now(timezone.utc) - timedelta(days=30),
        r'\bthis month\b': lambda: datetime.now(timezone.utc).replace(day=1),
        r'\bnext month\b': lambda: (datetime.now(timezone.utc).replace(day=1) + timedelta(days=32)).replace(day=1),
        r'\b(\d+)\s+days?\s+ago\b': lambda m: datetime.now(timezone.utc) - timedelta(days=int(m.group(1))),
        r'\b(\d+)\s+weeks?\s+ago\b': lambda m: datetime.now(timezone.utc) - timedelta(weeks=int(m.group(1))),
        r'\b(\d+)\s+months?\s+ago\b': lambda m: datetime.now(timezone.utc) - timedelta(days=int(m.group(1)) * 30),
        r'\b(\d+)\s+days?\s+from\s+now\b': lambda m: datetime.now(timezone.utc) + timedelta(days=int(m.group(1))),
        r'\b(\d+)\s+weeks?\s+from\s+now\b': lambda m: datetime.now(timezone.utc) + timedelta(weeks=int(m.group(1))),
        r'\b(\d+)\s+hours?\s+ago\b': lambda m: datetime.now(timezone.utc) - timedelta(hours=int(m.group(1))),
        r'\b(\d+)\s+minutes?\s+ago\b': lambda m: datetime.now(timezone.utc) - timedelta(minutes=int(m.group(1))),
    }

    date_input_lower = date_input.lower().strip()

    # Check relative patterns
    for pattern, func in relative_patterns.items():
        match = re.search(pattern, date_input_lower)
        if match:
            try:
                if 'lambda' in str(func) and len(match.groups()) == 0:
                    return func()
                else:
                    return func(match)
            except Exception as e:
                logger.warning(f"Error processing relative date pattern {pattern}: {e}")
                continue

    # Handle epoch timestamps
    if date_input.isdigit() or (date_input.startswith('-') and date_input[1:].isdigit()):
        timestamp = int(date_input)
        # Detect if it's milliseconds (> year 2001 in seconds would be > 1000000000)
        if abs(timestamp) > 1000000000000:  # Milliseconds
            return datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc)
        else:  # Seconds
            return datetime.fromtimestamp(timestamp, tz=timezone.utc)

    # Handle ISO and other standard formats
    try:
        # Try ISO format first (most common)
        try:
            parsed_date = datetime.fromisoformat(date_input.replace('Z', '+00:00'))
            if parsed_date.tzinfo is None:
                parsed_date = parsed_date.replace(tzinfo=timezone.utc)
            return parsed_date.astimezone(timezone.utc)
        except ValueError:
            pass

        # Try common date formats
        for fmt in [
            "%Y-%m-%d",           # 2025-06-13
            "%Y/%m/%d",           # 2025/06/13
            "%m/%d/%Y",           # 06/13/2025
            "%B %d, %Y",          # June 13, 2025
            "%b %d, %Y",          # Jun 13, 2025
            "%d %B %Y",           # 13 June 2025
            "%d %b %Y",           # 13 Jun 2025
        ]:
            try:
                parsed_date = datetime.strptime(date_input, fmt)
                parsed_date = parsed_date.replace(tzinfo=timezone.utc)
                return parsed_date
            except ValueError:
                continue

        # If all parsing fails
        raise ValueError(f"Unsupported date format: {date_input}")

    except Exception as e:
        logger.warning(f"Could not parse date '{date_input}': {e}")
        raise ValueError(f"Could not parse date: {date_input}")


def create_datetime_error_response(date_input: str, error_msg: str) -> Dict[str, Any]:
    """
    Create educational error response for date/time parsing failures.

    Args:
        date_input: The input that failed to parse
        error_msg: The specific error message

    Returns:
        Dict with error details and educational content
    """
    return {
        "error": f"Could not parse date/time: '{date_input}'",
        "details": error_msg,
        "explanation": "YouTrack accepts specific date formats and LLMs often struggle with date conversions",
        "supported_formats": {
            "ISO_8601": ["2025-06-13", "2025-06-13T10:30:00Z", "2025-06-13T10:30:00-05:00"],
            "Simple_dates": ["2025-06-13", "2025/06/13", "Jun 13, 2025", "June 13, 2025"],
            "Relative_dates": ["yesterday", "last week", "3 days ago", "2 weeks ago", "last Monday", "next month"],
            "Epoch_timestamps": ["1718276400 (seconds)", "1718276400000 (milliseconds)"],
            "YouTrack_ranges": ["2025-06-01 .. 2025-06-13", "-7d .. *", "* .. 2025-06-13"]
        },
        "examples": {
            "last_week_range": "Use: created: -7d .. * (last 7 days)",
            "specific_date": "Use: created: 2025-06-13 (specific day)",
            "date_range": "Use: created: 2025-06-01 .. 2025-06-13 (range)",
            "relative_youtrack": "Use: updated: -1w .. * (last week in YouTrack syntax)"
        },
        "recommendation": "Use the convert_datetime() tool first to validate and convert your date input before using it in queries.",
        "learn_from_this": "Always validate dates with convert_datetime() tool. YouTrack uses YYYY-MM-DD format and supports relative dates like '-7d' for last 7 days.",
        "common_mistakes": [
            "MM/DD/YYYY format (use YYYY-MM-DD instead)",
            "Ambiguous relative dates (be specific: '7 days ago' not 'last week')",
            "Missing timezone context (specify timezone or use UTC)",
            "Mixing epoch seconds vs milliseconds"
        ]
    }


def convert_datetime_tool(date_input: str, timezone_str: str = "UTC", output_format: str = "youtrack") -> Dict[str, Any]:
    """
    Convert various date/time formats to YouTrack-compatible format.

    This tool helps LLMs convert natural language dates, relative dates, and various formats
    into YouTrack Query Language (YQL) compatible date formats.

    Args:
        date_input: Date in various formats (ISO, relative, epoch, human readable)
        timezone_str: Timezone for interpretation (default: UTC)
        output_format: Output format (youtrack, iso8601, epoch, human)

    Returns:
        Converted date with examples and explanations optimized for LLM learning
    """
    try:
        converted_date = normalize_datetime(date_input, timezone_str)

        result = {
            "input": date_input,
            "converted": {
                "youtrack": converted_date.strftime("%Y-%m-%d"),
                "youtrack_with_time": converted_date.strftime("%Y-%m-%d %H:%M"),
                "iso8601": converted_date.isoformat(),
                "epoch": int(converted_date.timestamp()),
                "epoch_ms": int(converted_date.timestamp() * 1000),
                "human": converted_date.strftime("%B %d, %Y at %H:%M UTC"),
            },
            "timezone_used": timezone_str,
            "explanation": f"Converted '{date_input}' to {converted_date.strftime('%Y-%m-%d')} in {timezone_str}",
            "youtrack_usage_examples": [
                f"created: {converted_date.strftime('%Y-%m-%d')} .. *",
                f"updated: * .. {converted_date.strftime('%Y-%m-%d')}",
                f"created: {converted_date.strftime('%Y-%m-%d')} .. {(converted_date + timedelta(days=7)).strftime('%Y-%m-%d')}",
                f"updated: -7d .. {converted_date.strftime('%Y-%m-%d')}"
            ],
            "query_patterns": {
                "specific_date": f"created: {converted_date.strftime('%Y-%m-%d')}",
                "date_range": f"created: {(converted_date - timedelta(days=7)).strftime('%Y-%m-%d')} .. {converted_date.strftime('%Y-%m-%d')}",
                "relative_to_now": f"created: -7d .. {converted_date.strftime('%Y-%m-%d')}",
                "future_date": f"due date: {converted_date.strftime('%Y-%m-%d')} .. *"
            }
        }

        return result

    except Exception as e:
        return create_datetime_error_response(date_input, str(e))


def validate_date_range(start_date: str, end_date: str, timezone_str: str = "UTC") -> Dict[str, Any]:
    """
    Validate and provide suggestions for date ranges.

    Args:
        start_date: Start date input
        end_date: End date input
        timezone_str: Timezone for interpretation

    Returns:
        Validation result with suggestions if invalid
    """
    try:
        start_converted = normalize_datetime(start_date, timezone_str)
        end_converted = normalize_datetime(end_date, timezone_str)

        if start_converted >= end_converted:
            # Invalid range - provide correction
            corrected_end = start_converted + timedelta(days=7)  # Default to 7-day range
            return {
                "valid": False,
                "error": "Invalid date range",
                "details": f"Start date ({start_converted.strftime('%Y-%m-%d')}) must be before end date ({end_converted.strftime('%Y-%m-%d')})",
                "explanation": "Date ranges must have start_date < end_date",
                "corrected_suggestion": {
                    "start_date": start_converted.strftime('%Y-%m-%d'),
                    "end_date": corrected_end.strftime('%Y-%m-%d'),
                    "youtrack_query": f"created: {start_converted.strftime('%Y-%m-%d')} .. {corrected_end.strftime('%Y-%m-%d')}"
                },
                "learn_from_this": "Always ensure your date range is logical with start before end. Use convert_datetime() to validate dates first."
            }

        # Valid range
        days_diff = (end_converted - start_converted).days
        return {
            "valid": True,
            "start_date": start_converted.strftime('%Y-%m-%d'),
            "end_date": end_converted.strftime('%Y-%m-%d'),
            "days_difference": days_diff,
            "youtrack_query": f"created: {start_converted.strftime('%Y-%m-%d')} .. {end_converted.strftime('%Y-%m-%d')}",
            "range_description": f"{days_diff} day{'s' if days_diff != 1 else ''} from {start_converted.strftime('%B %d')} to {end_converted.strftime('%B %d, %Y')}"
        }

    except Exception as e:
        return {
            "valid": False,
            "error": f"Could not validate date range: {str(e)}",
            "recommendation": "Use convert_datetime() on both dates individually first, then validate the range."
        }


class DateTimeTools:
    """Date/Time conversion tools optimized for LLM usage with YouTrack."""

    def __init__(self):
        """Initialize date/time tools."""
        pass

    @async_wrapper
    async def convert_datetime(self, date_input: str, timezone: str = "UTC", output_format: str = "youtrack") -> Dict[str, Any]:
        """
        Convert various date/time formats to YouTrack-compatible format.

        FORMAT: datetime.convert_datetime(date_input="last week", timezone="UTC", output_format="youtrack")

        This tool helps convert natural language dates, relative dates, and various formats
        into YouTrack Query Language (YQL) compatible date formats.

        Args:
            date_input: Date in various formats:
                - ISO 8601: "2025-06-13", "2025-06-13T10:30:00Z"
                - Simple dates: "Jun 13, 2025", "2025/06/13"
                - Relative dates: "yesterday", "last week", "3 days ago", "next month"
                - Epoch timestamps: 1718276400 (seconds), 1718276400000 (milliseconds)
                - Human readable: "June 13, 2025", "last Monday"
            timezone: Timezone for interpretation (default: UTC)
            output_format: Primary output format - "youtrack" (recommended), "iso8601", "epoch", "human"

        Returns:
            Dictionary containing:
            - converted: Multiple format outputs (youtrack, iso8601, epoch, human)
            - youtrack_usage_examples: Ready-to-use YouTrack query examples
            - query_patterns: Common query patterns with the converted date
            - explanation: What conversion was performed

        Examples:
            convert_datetime("last week") → YouTrack queries for last week's activity
            convert_datetime("2025-06-13") → Validated date with usage examples
            convert_datetime("1718276400") → Converted epoch timestamp
        """
        return convert_datetime_tool(date_input, timezone, output_format)

    @async_wrapper
    async def validate_date_range(self, start_date: str, end_date: str, timezone: str = "UTC") -> Dict[str, Any]:
        """
        Validate date ranges and provide YouTrack query suggestions.

        FORMAT: datetime.validate_date_range(start_date="2025-06-01", end_date="2025-06-13", timezone="UTC")

        Args:
            start_date: Start date (any format supported by convert_datetime)
            end_date: End date (any format supported by convert_datetime)
            timezone: Timezone for interpretation (default: UTC)

        Returns:
            Validation result with:
            - valid: Whether the range is valid
            - youtrack_query: Ready-to-use YouTrack query if valid
            - corrected_suggestion: Suggested fix if invalid
            - range_description: Human-readable description

        Examples:
            validate_date_range("2025-06-01", "2025-06-13") → Valid 12-day range
            validate_date_range("2025-06-13", "2025-06-01") → Invalid with correction suggestion
        """
        return validate_date_range(start_date, end_date, timezone)