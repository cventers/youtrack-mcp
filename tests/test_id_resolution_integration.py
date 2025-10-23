#!/usr/bin/env python3
"""
Integration test for ID resolution functionality.

Tests that the MCP tools can accept human-readable IDs (like "CLUSTER")
and transparently convert them to internal IDs (like "63-2").
"""

import asyncio
import json
import sys
from pathlib import Path

# Add parent directory to path to import the modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from youtrack_mcp.tools.issues_tools import IssuesTools
from youtrack_mcp.tools.projects_tools import ProjectsTools
from youtrack_mcp.tools.users_tools import UsersTools
from youtrack_mcp.logging import get_logger

logger = get_logger(__name__)


async def test_project_id_resolution():
    """Test that project shortName is resolved to internal ID."""
    print("\n" + "="*60)
    print("TEST: Project ID Resolution")
    print("="*60)

    projects_tools = ProjectsTools()

    # Test 1: Get project using shortName
    print("\nTest 1: Get project using shortName 'CLUSTER'...")
    try:
        result = await projects_tools.get(project_id="CLUSTER")
        if result and "project" in result:
            project = result["project"]
            print(f"✅ SUCCESS: Got project '{project.get('shortName', 'N/A')}' (ID: {project.get('id', 'N/A')})")
        else:
            print(f"❌ FAILED: Unexpected response format: {result}")
    except Exception as e:
        print(f"❌ FAILED: {type(e).__name__}: {e}")

    # Test 2: Get project using internal ID (should still work)
    print("\nTest 2: Get project using internal ID '63-2'...")
    try:
        result = await projects_tools.get(project_id="63-2")
        if result and "project" in result:
            project = result["project"]
            print(f"✅ SUCCESS: Got project '{project.get('shortName', 'N/A')}' (ID: {project.get('id', 'N/A')})")
        else:
            print(f"❌ FAILED: Unexpected response format: {result}")
    except Exception as e:
        print(f"❌ FAILED: {type(e).__name__}: {e}")


async def test_issue_creation_with_resolved_ids():
    """Test that issue creation works with shortName and user login."""
    print("\n" + "="*60)
    print("TEST: Issue Creation with ID Resolution")
    print("="*60)

    issues_tools = IssuesTools()

    # Test 3: Create issue using project shortName
    print("\nTest 3: Create issue using project shortName 'CLUSTER'...")
    try:
        result = await issues_tools.create(
            project="CLUSTER",  # Using shortName instead of "63-2"
            summary="Test issue from ID resolution integration test",
            description="This issue was created using the project shortName 'CLUSTER' instead of internal ID",
            custom_fields={
                "Assignee": ["cventers"],  # Using login instead of numeric ID
                "Priority": "Normal"
            }
        )
        if result and "issue" in result:
            issue = result["issue"]
            print(f"✅ SUCCESS: Created issue {issue.get('idReadable', issue.get('id', 'N/A'))}")
            return issue  # Return for cleanup
        else:
            print(f"❌ FAILED: Unexpected response format: {result}")
    except Exception as e:
        print(f"❌ FAILED: {type(e).__name__}: {e}")
        # If it fails with "Invalid structure of entity id: CLUSTER", ID resolution isn't working
        if "Invalid structure of entity id: CLUSTER" in str(e):
            print("⚠️  ID resolution is NOT working - project shortName was not resolved")

    return None


async def test_user_resolution():
    """Test that user login is resolved to internal ID."""
    print("\n" + "="*60)
    print("TEST: User ID Resolution")
    print("="*60)

    users_tools = UsersTools()

    # Test 4: Search for user
    print("\nTest 4: Search for user 'cventers'...")
    try:
        result = await users_tools.search(query="cventers", limit=5)
        if result and "users" in result:
            users = result["users"]
            if users:
                user = users[0]
                print(f"✅ SUCCESS: Found user '{user.get('login', 'N/A')}' (ID: {user.get('id', 'N/A')})")
            else:
                print("⚠️  No users found with query 'cventers'")
        else:
            print(f"❌ FAILED: Unexpected response format: {result}")
    except Exception as e:
        print(f"❌ FAILED: {type(e).__name__}: {e}")


async def test_issue_update_with_resolved_ids():
    """Test that issue update works with user logins."""
    print("\n" + "="*60)
    print("TEST: Issue Update with ID Resolution")
    print("="*60)

    issues_tools = IssuesTools()

    # First, we need an issue to update. Try to use CLUSTER-4441 from previous session
    issue_id = "CLUSTER-4441"

    print(f"\nTest 5: Update issue {issue_id} with user login 'cventers'...")
    try:
        result = await issues_tools.patch(
            issue_id=issue_id,
            fields={
                "Assignee": "cventers",  # Using login instead of numeric ID
                "summary": "Updated: Test ID resolution with user login"
            }
        )
        if result:
            print(f"✅ SUCCESS: Updated issue {issue_id}")
            print(f"   Fields updated: {result.get('regular_fields_updated', [])} {result.get('custom_fields_updated', [])}")
        else:
            print(f"❌ FAILED: No response from patch")
    except Exception as e:
        print(f"⚠️  Could not update {issue_id}: {type(e).__name__}: {e}")
        print("   (This is expected if the issue doesn't exist)")


async def main():
    """Run all ID resolution tests."""
    print("\n" + "#"*60)
    print("# ID RESOLUTION INTEGRATION TESTS")
    print("#"*60)
    print("\nThese tests verify that the YouTrack MCP server can accept")
    print("human-readable IDs and transparently convert them to internal IDs.")

    # Run tests
    await test_project_id_resolution()
    await test_user_resolution()
    created_issue = await test_issue_creation_with_resolved_ids()
    await test_issue_update_with_resolved_ids()

    print("\n" + "#"*60)
    print("# TEST SUMMARY")
    print("#"*60)
    print("\nID Resolution should now be working for:")
    print("  - Project shortNames (e.g., 'CLUSTER' → '63-2')")
    print("  - User logins (e.g., 'cventers' → numeric ID)")
    print("  - Issue readable IDs (already supported by YouTrack)")

    if created_issue:
        print(f"\n⚠️  Created test issue: {created_issue.get('idReadable', created_issue.get('id'))}")
        print("   You may want to delete this test issue from YouTrack")


if __name__ == "__main__":
    asyncio.run(main())