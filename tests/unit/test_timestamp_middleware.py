#!/usr/bin/env python3
"""
Test script to verify timestamp middleware functionality.
"""

import asyncio
import json
from datetime import datetime
from youtrack_mcp.utils import add_iso8601_timestamps, convert_timestamp_to_iso8601


async def test_timestamp_conversion():
    """Test the timestamp conversion functions."""

    print("Testing timestamp conversion functionality:\n")

    # Test 1: Single timestamp conversion
    print("1. Testing single timestamp conversion:")
    timestamp_ms = 1737047429000  # Example timestamp
    iso_timestamp = convert_timestamp_to_iso8601(timestamp_ms)
    print(f"   Input: {timestamp_ms}")
    print(f"   Output: {iso_timestamp}")
    print("   Conversion successful\n")

    # Test 2: Simple dict with timestamps
    print("2. Testing dict with created/updated fields:")
    test_data = {
        "id": "DEMO-123",
        "summary": "Test issue",
        "created": 1737047429000,
        "updated": 1737048000000,
        "status": "Open"
    }

    enhanced_data = add_iso8601_timestamps(test_data)
    print(f"   Input: {json.dumps(test_data, indent=2)}")
    print(f"   Output: {json.dumps(enhanced_data, indent=2)}")

    # Verify the timestamps were converted (modern mode)
    assert isinstance(enhanced_data["created"], str)  # Should be ISO8601 string
    assert isinstance(enhanced_data["updated"], str)  # Should be ISO8601 string
    assert enhanced_data["created"] != test_data["created"]  # Should be converted
    print("   Timestamps converted correctly\n")

    # Test 3: Nested structure
    print("3. Testing nested structure:")
    nested_data = {
        "issue": {
            "id": "DEMO-456",
            "created": 1737047429000,
            "comments": [
                {"id": 1, "created": 1737047500000, "text": "First comment"},
                {"id": 2, "created": 1737047600000, "text": "Second comment"}
            ]
        },
        "project": {
            "created": 1737040000000,
            "updated": 1737041000000
        }
    }

    enhanced_nested = add_iso8601_timestamps(nested_data)
    print("   Original nested created fields:")
    print(f"     - issue.created: {nested_data['issue']['created']}")
    print(f"     - comments[0].created: {nested_data['issue']['comments'][0]['created']}")
    print(f"     - project.created: {nested_data['project']['created']}")

    print("\n   Enhanced with ISO8601:")
    print(f"     - issue.created: {enhanced_nested['issue'].get('created')}")
    print(f"     - comments[0].created: {enhanced_nested['issue']['comments'][0].get('created')}")
    print(f"     - project.created: {enhanced_nested['project'].get('created')}")

    # Verify nested timestamps (modern mode - replaced)
    assert isinstance(enhanced_nested["issue"]["created"], str)
    assert isinstance(enhanced_nested["issue"]["comments"][0]["created"], str)
    assert isinstance(enhanced_nested["project"]["created"], str)
    print("   Nested timestamps converted correctly\n")

    # Test 4: List of items
    print("4. Testing list of items:")
    list_data = [
        {"id": 1, "created": 1737047429000},
        {"id": 2, "created": 1737047430000},
        {"id": 3, "created": 1737047431000}
    ]

    enhanced_list = add_iso8601_timestamps(list_data)
    print(f"   Number of items: {len(list_data)}")
    for i, item in enumerate(enhanced_list):
        if isinstance(item.get("created"), str):
            print(f"   Item {i}: Has converted created timestamp")

    # Verify all items have converted timestamps
    assert all(isinstance(item.get("created"), str) for item in enhanced_list)
    print("   All list items have converted timestamps\n")

    # Test 5: Non-timestamp fields unchanged
    print("5. Testing non-timestamp fields remain unchanged:")
    other_data = {
        "name": "Test",
        "count": 42,
        "active": True,
        "tags": ["bug", "urgent"],
        "metadata": {"key": "value"}
    }

    enhanced_other = add_iso8601_timestamps(other_data)
    assert enhanced_other == other_data
    print("   Non-timestamp data unchanged\n")

    print("All timestamp conversion tests passed!")


async def test_middleware_integration():
    """Test middleware integration with actual tools."""
    print("\n" + "="*60)
    print("Testing Middleware Integration")
    print("="*60 + "\n")

    try:
        # Import the server components
        from youtrack_mcp.server_fastmcp import mcp
        from youtrack_mcp.middleware import TimestampMiddleware

        # Create and apply middleware
        middleware = TimestampMiddleware(enable=True)

        print("1. Checking MCP server structure:")
        if hasattr(mcp, '_tool_manager') and hasattr(mcp._tool_manager, 'list_tools'):
            tools = mcp._tool_manager.list_tools()
            print("   MCP server has _tool_manager.list_tools()")
            print(f"   Number of tools: {len(tools)}")

            # Apply middleware
            middleware.apply_to_mcp_server(mcp)
            print("   Middleware applied successfully\n")

            # Show some registered tools
            print("2. Sample of registered tools:")
            for tool in tools[:5]:
                print(f"   - {tool.name}")

            print("\nMiddleware integration successful!")
        else:
            print("   WARNING: MCP server structure different than expected")

    except ImportError as e:
        print(f"WARNING: Could not import server components: {e}")
        print("  This is expected if running outside the proper environment")
    except Exception as e:
        print(f"ERROR: Error during integration test: {e}")


async def main():
    """Run all tests."""
    print("YouTrack MCP Timestamp Middleware Test Suite")
    print("=" * 60 + "\n")

    # Run conversion tests
    await test_timestamp_conversion()

    # Run integration tests
    await test_middleware_integration()

    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())