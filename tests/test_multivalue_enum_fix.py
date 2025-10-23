#!/usr/bin/env python3
"""
Test script to verify multi-value enum field fix.

This tests that the "Change Type" field (which has bundle_id "enum[*]")
is properly detected as a multi-value field and formatted correctly.
"""

import asyncio
import sys
import os

# Add parent directory to path to import youtrack_mcp
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from youtrack_mcp.tools.issues_tools import IssuesTools
from youtrack_mcp.tools.projects_tools import ProjectsTools
from youtrack_mcp.logging import get_logger

logger = get_logger(__name__)


async def test_multivalue_enum_field():
    """Test that Change Type field is properly handled as multi-value enum."""

    print("\n=== Testing Multi-Value Enum Field Fix ===\n")

    # Initialize tools
    issues = IssuesTools()
    projects = ProjectsTools()

    try:
        # Step 1: Get project schema to check field configuration
        print("1. Getting project schema for CLUSTER...")
        schema = await projects.schema("CLUSTER")

        # Find the Change Type field in schema
        change_type_field = None
        for field_name, field_info in schema.get("schemas", {}).items():
            if field_name == "Change Type":
                change_type_field = field_info
                break

        if change_type_field:
            print(f"\n   ✓ Found 'Change Type' field in schema")
            print(f"     - Type: {change_type_field.get('type')}")
            print(f"     - Bundle ID: {change_type_field.get('bundle_id')}")
            print(f"     - Multi-value: {change_type_field.get('multi_value')}")  # This should now be True
            print(f"     - Required: {change_type_field.get('required')}")

            # Check if field is correctly detected as multi-value
            if change_type_field.get('multi_value'):
                print(f"   ✅ Field correctly detected as MULTI-VALUE")
            else:
                print(f"   ❌ Field INCORRECTLY detected as single-value (should be multi-value)")

            # Display allowed values if available
            allowed_values = change_type_field.get('allowed_values', [])
            if allowed_values and not any(v.get('name') == '__ENUM_ACCESS_ERROR__' for v in allowed_values):
                print(f"     - Allowed values ({len(allowed_values)}): {', '.join([v.get('name', '') for v in allowed_values[:5]])}")
                if len(allowed_values) > 5:
                    print(f"       ... and {len(allowed_values) - 5} more")
            else:
                print(f"     - Allowed values: Unable to fetch (may need different approach)")
        else:
            print(f"   ❌ 'Change Type' field not found in schema")

        # Step 2: Test updating an issue with the Change Type field
        print("\n2. Testing issue update with Change Type field...")
        print("   Attempting to update CLUSTER-4441 with Change Type = 'Configuration'")

        try:
            result = await issues.patch(
                issue_id="CLUSTER-4441",
                fields={
                    "Change Type": "Configuration Change"  # Single value for multi-value field
                }
            )

            if result.get("updated"):
                print(f"   ✅ Successfully updated issue!")
                print(f"      - Fields updated: {result.get('custom_fields_updated', [])}")
            else:
                print(f"   ❌ Update failed: {result}")

        except Exception as e:
            print(f"   ❌ Update failed with error: {e}")

        # Step 3: Test with array format (proper multi-value format)
        print("\n3. Testing with array format (proper multi-value)...")
        print("   Attempting to update with Change Type = ['Configuration']")

        try:
            result = await issues.patch(
                issue_id="CLUSTER-4441",
                fields={
                    "Change Type": ["Configuration Change"]  # Array format for multi-value
                }
            )

            if result.get("updated"):
                print(f"   ✅ Successfully updated issue with array format!")
                print(f"      - Fields updated: {result.get('custom_fields_updated', [])}")
            else:
                print(f"   ❌ Update failed: {result}")

        except Exception as e:
            print(f"   ❌ Update failed with error: {e}")

        # Step 4: Verify the update by getting the issue
        print("\n4. Verifying the update...")
        issue_data = await issues.get(
            issue_id="CLUSTER-4441",
            include=["customFields"]
        )

        if issue_data and issue_data.get("issue"):
            custom_fields = issue_data["issue"].get("customFields", [])
            change_type_value = None

            for cf in custom_fields:
                if cf.get("name") == "Change Type":
                    change_type_value = cf.get("value")
                    break

            if change_type_value:
                print(f"   ✓ Change Type field value: {change_type_value}")
            else:
                print(f"   ⚠ Change Type field not found in issue")

        print("\n=== Test Complete ===\n")

    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Run the test
    asyncio.run(test_multivalue_enum_field())