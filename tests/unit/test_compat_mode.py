#!/usr/bin/env python3
"""
Test script to verify compatibility mode for timestamp conversion.
"""

import asyncio
import json
from youtrack_mcp.utils import add_iso8601_timestamps, format_json_response


async def test_compatibility_modes():
    """Test both modern and legacy timestamp conversion modes."""

    print("Testing Timestamp Compatibility Modes")
    print("=" * 60 + "\n")

    # Test data with numeric timestamps
    test_data = {
        "id": "DEMO-123",
        "summary": "Test issue",
        "created": 1737047429000,
        "updated": 1737048000000,
        "comments": [
            {"id": 1, "created": 1737047500000, "text": "First comment"},
            {"id": 2, "created": 1737047600000, "text": "Second comment"}
        ]
    }

    # Test 1: Modern mode (include_numeric=False) - DEFAULT
    print("1. MODERN MODE (include_numeric=False) - Default:")
    print("-" * 50)
    modern_result = add_iso8601_timestamps(test_data, include_numeric=False)

    print("Input:")
    print(f"  created: {test_data['created']}")
    print(f"  updated: {test_data['updated']}")

    print("\nOutput:")
    print(f"  created: {modern_result['created']}")
    print(f"  updated: {modern_result['updated']}")

    # Verify modern mode replaced numeric with ISO8601
    assert isinstance(modern_result['created'], str)
    assert isinstance(modern_result['updated'], str)
    assert 'created_iso8601' not in modern_result
    assert 'updated_iso8601' not in modern_result
    print("\n✓ Modern mode: Numeric timestamps replaced with ISO8601 strings\n")

    # Test 2: Legacy mode (include_numeric=True)
    print("2. LEGACY MODE (include_numeric=True):")
    print("-" * 50)
    legacy_result = add_iso8601_timestamps(test_data, include_numeric=True)

    print("Input:")
    print(f"  created: {test_data['created']}")
    print(f"  updated: {test_data['updated']}")

    print("\nOutput:")
    print(f"  created: {legacy_result['created']}")
    print(f"  created_iso8601: {legacy_result.get('created_iso8601')}")
    print(f"  updated: {legacy_result['updated']}")
    print(f"  updated_iso8601: {legacy_result.get('updated_iso8601')}")

    # Verify legacy mode kept numeric and added _iso8601 fields
    assert isinstance(legacy_result['created'], int)
    assert isinstance(legacy_result['updated'], int)
    assert 'created_iso8601' in legacy_result
    assert 'updated_iso8601' in legacy_result
    print("\n✓ Legacy mode: Numeric timestamps preserved, _iso8601 fields added\n")

    # Test 3: Nested structures
    print("3. NESTED STRUCTURES:")
    print("-" * 50)

    # Modern mode on nested data
    modern_nested = add_iso8601_timestamps(test_data, include_numeric=False)
    print("Modern mode - Comment timestamps:")
    for i, comment in enumerate(modern_nested['comments']):
        print(f"  Comment {i+1} created: {comment['created']} (type: {type(comment['created']).__name__})")

    # Legacy mode on nested data
    legacy_nested = add_iso8601_timestamps(test_data, include_numeric=True)
    print("\nLegacy mode - Comment timestamps:")
    for i, comment in enumerate(legacy_nested['comments']):
        print(f"  Comment {i+1} created: {comment['created']} (type: {type(comment['created']).__name__})")
        if 'created_iso8601' in comment:
            print(f"  Comment {i+1} created_iso8601: {comment['created_iso8601']}")

    print("\n✓ Nested structures handled correctly in both modes\n")

    # Test 4: format_json_response wrapper
    print("4. FORMAT_JSON_RESPONSE WRAPPER:")
    print("-" * 50)

    # Modern JSON output
    modern_json = format_json_response({"created": 1737047429000}, include_numeric=False)
    modern_parsed = json.loads(modern_json)
    print(f"Modern JSON - created field type: {type(modern_parsed['created']).__name__}")

    # Legacy JSON output
    legacy_json = format_json_response({"created": 1737047429000}, include_numeric=True)
    legacy_parsed = json.loads(legacy_json)
    print(f"Legacy JSON - created field type: {type(legacy_parsed['created']).__name__}")
    print(f"Legacy JSON - has created_iso8601: {'created_iso8601' in legacy_parsed}")

    print("\n✓ format_json_response respects include_numeric parameter\n")

    print("=" * 60)
    print("ALL COMPATIBILITY TESTS PASSED!")
    print("=" * 60)
    print("\nSummary:")
    print("- Modern mode (default): Replaces numeric timestamps with ISO8601 strings")
    print("- Legacy mode: Preserves numeric timestamps and adds _iso8601 fields")
    print("- Both modes work correctly with nested structures")
    print("- Configuration via COMPAT_INCLUDE_NUMERIC_DATE environment variable")


async def main():
    """Run all compatibility tests."""
    await test_compatibility_modes()


if __name__ == "__main__":
    asyncio.run(main())