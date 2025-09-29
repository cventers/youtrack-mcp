"""
Tests for youtrack_mcp/utils.py
"""

import json
import pytest
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from unittest.mock import patch
from youtrack_mcp.utils import (
    convert_timestamp_to_iso8601,
    add_iso8601_timestamps,
    format_json_response
)


class TestConvertTimestampToIso8601:
    """Test convert_timestamp_to_iso8601 function."""

    def test_valid_timestamp_conversion(self):
        """Test converting valid timestamp to ISO8601."""
        # Test timestamp: 2023-01-01 00:00:00 UTC in milliseconds
        timestamp_ms = 1672531200000
        result = convert_timestamp_to_iso8601(timestamp_ms)

        # The result should be a valid ISO8601 string
        # The actual timezone depends on configuration
        assert isinstance(result, str)
        assert 'T' in result  # ISO8601 format includes T separator
        # Parse it to ensure it's valid
        datetime.fromisoformat(result.replace('+00:00', '+00:00'))

    def test_zero_timestamp(self):
        """Test converting zero timestamp."""
        result = convert_timestamp_to_iso8601(0)
        # Unix epoch in whatever timezone is configured
        assert isinstance(result, str)
        assert 'T' in result
        assert '1970' in result or '1969' in result  # Could be Dec 31 1969 in some timezones

    def test_negative_timestamp(self):
        """Test handling negative timestamp."""
        result = convert_timestamp_to_iso8601(-1000)
        assert isinstance(result, str)
        assert '1969' in result or '1970' in result

    def test_invalid_timestamp_value_error(self):
        """Test handling invalid timestamp that causes ValueError."""
        # Very large timestamp that might cause overflow
        invalid_timestamp = 9999999999999999999999
        result = convert_timestamp_to_iso8601(invalid_timestamp)
        assert result == str(invalid_timestamp)

    def test_invalid_timestamp_overflow_error(self):
        """Test handling timestamp that causes OverflowError."""
        # Test with extremely large value
        invalid_timestamp = float('inf')
        result = convert_timestamp_to_iso8601(invalid_timestamp)
        assert result == str(invalid_timestamp)

    def test_invalid_timestamp_os_error(self):
        """Test handling timestamp that might cause OSError."""
        # Test with very negative value that might cause platform-specific issues
        invalid_timestamp = -999999999999999999
        result = convert_timestamp_to_iso8601(invalid_timestamp)
        # Should either return valid ISO string or fallback to string representation
        assert isinstance(result, str)


class TestAddIso8601Timestamps:
    """Test add_iso8601_timestamps function."""

    def test_dict_with_created_timestamp(self):
        """Test adding ISO8601 timestamp to dict with created field."""
        data = {"created": 1672531200000, "name": "test"}
        result = add_iso8601_timestamps(data)

        assert result["created"] == 1672531200000
        assert "created_iso8601" in result
        assert isinstance(result["created_iso8601"], str)
        assert result["name"] == "test"

    def test_dict_with_updated_timestamp(self):
        """Test adding ISO8601 timestamp to dict with updated field."""
        data = {"updated": 1672531200000, "id": "123"}
        result = add_iso8601_timestamps(data)

        assert result["updated"] == 1672531200000
        assert "updated_iso8601" in result
        assert isinstance(result["updated_iso8601"], str)
        assert result["id"] == "123"

    def test_dict_with_both_timestamps(self):
        """Test adding ISO8601 timestamps for both created and updated."""
        data = {
            "created": 1672531200000,
            "updated": 1672617600000,  # 2023-01-02 00:00:00 UTC
            "summary": "Test issue"
        }
        result = add_iso8601_timestamps(data)

        assert "created_iso8601" in result
        assert "updated_iso8601" in result
        assert isinstance(result["created_iso8601"], str)
        assert isinstance(result["updated_iso8601"], str)
        assert result["summary"] == "Test issue"

    def test_dict_with_non_integer_timestamp(self):
        """Test dict with non-integer timestamp values."""
        data = {"created": "not-a-number", "updated": None}
        result = add_iso8601_timestamps(data)

        # Should not add ISO8601 fields for non-integer values
        assert "created_iso8601" not in result
        assert "updated_iso8601" not in result

    def test_dict_without_timestamp_fields(self):
        """Test dict without any timestamp fields."""
        data = {"id": "123", "name": "test"}
        result = add_iso8601_timestamps(data)

        assert result == data
        assert "created_iso8601" not in result
        assert "updated_iso8601" not in result

    def test_list_with_timestamps(self):
        """Test adding ISO8601 timestamps to list of dicts."""
        data = [
            {"created": 1672531200000, "id": "1"},
            {"updated": 1672617600000, "id": "2"}
        ]
        result = add_iso8601_timestamps(data)

        assert isinstance(result, list)
        assert len(result) == 2
        assert "created_iso8601" in result[0]
        assert "updated_iso8601" in result[1]

    def test_nested_dict_with_timestamps(self):
        """Test adding ISO8601 timestamps to nested dicts."""
        data = {
            "issue": {
                "created": 1672531200000,
                "author": {"updated": 1672617600000}
            }
        }
        result = add_iso8601_timestamps(data)

        assert "created_iso8601" in result["issue"]
        assert "updated_iso8601" in result["issue"]["author"]

    def test_empty_dict(self):
        """Test empty dict."""
        result = add_iso8601_timestamps({})
        assert result == {}

    def test_none_value(self):
        """Test None value."""
        result = add_iso8601_timestamps(None)
        assert result is None


class TestFormatJsonResponse:
    """Test format_json_response function."""

    def test_format_dict_response(self):
        """Test formatting dict response."""
        data = {"id": "123", "created": 1672531200000}
        result = format_json_response(data)

        # Should be JSON string
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert parsed["id"] == "123"
        assert "created_iso8601" in parsed

    def test_format_list_response(self):
        """Test formatting list response."""
        data = [{"id": "1"}, {"id": "2"}]
        result = format_json_response(data)

        assert isinstance(result, str)
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert len(parsed) == 2

    def test_format_string_response(self):
        """Test formatting string response."""
        data = "simple string"
        result = format_json_response(data)

        # Should be JSON string (quoted)
        assert isinstance(result, str)
        assert result == '"simple string"'

    def test_format_with_timestamps(self):
        """Test formatting with timestamp conversion."""
        data = {"created": 1672531200000, "updated": 1672617600000}
        result = format_json_response(data)

        parsed = json.loads(result)
        assert "created_iso8601" in parsed
        assert "updated_iso8601" in parsed

    def test_format_with_indent(self):
        """Test formatting with indentation."""
        data = {"id": "123", "name": "test"}
        result = format_json_response(data, indent=4)

        assert isinstance(result, str)
        assert '\n' in result  # Indented JSON contains newlines
        parsed = json.loads(result)
        assert parsed["id"] == "123"

    def test_format_none_value(self):
        """Test formatting None value."""
        result = format_json_response(None)
        assert result == 'null'

    def test_format_boolean_value(self):
        """Test formatting boolean values."""
        assert format_json_response(True) == 'true'
        assert format_json_response(False) == 'false'

    def test_format_number_value(self):
        """Test formatting number values."""
        assert format_json_response(42) == '42'
        assert format_json_response(3.14) == '3.14'

    def test_format_complex_nested_structure(self):
        """Test formatting complex nested structure."""
        data = {
            "issues": [
                {"id": "1", "created": 1672531200000},
                {"id": "2", "updated": 1672617600000}
            ],
            "meta": {
                "total": 2,
                "timestamp": 1672531200000
            }
        }
        result = format_json_response(data)

        parsed = json.loads(result)
        assert "created_iso8601" in parsed["issues"][0]
        assert "updated_iso8601" in parsed["issues"][1]
        assert "timestamp_iso8601" in parsed["meta"]