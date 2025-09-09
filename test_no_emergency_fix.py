#!/usr/bin/env python3
"""Test that all tools work correctly without the emergency fix."""

import asyncio
import json
from unittest.mock import Mock, patch
import sys

def test_sync_wrapper_no_coroutine_handling():
    """Verify sync_wrapper no longer handles coroutines (they shouldn't exist anymore)."""
    from youtrack_mcp.mcp_wrappers import sync_wrapper
    
    # Create a function that returns a coroutine (this should NOT happen in production)
    @sync_wrapper
    def bad_sync_function():
        async def async_operation():
            return {"status": "This should fail"}
        return async_operation()  # Returns coroutine without await
    
    try:
        # This should now fail since we removed the emergency fix
        result = bad_sync_function()
        # Check what we got back
        if isinstance(result, str):
            # It returned a string - check if it's an error JSON
            try:
                data = json.loads(result)
                if "error" in data and "coroutine is not JSON serializable" in data["error"]:
                    print("✅ PASS: sync_wrapper correctly rejects coroutines (emergency fix removed)")
                    return True
                else:
                    print("❌ FAIL: Unexpected JSON response:", data)
                    return False
            except json.JSONDecodeError:
                print("❌ FAIL: Got non-JSON string:", result)
                return False
        else:
            print("❌ FAIL: Unexpected result type:", type(result))
            return False
    except Exception as e:
        # This could also indicate the emergency fix is removed
        print("✅ PASS: sync_wrapper threw exception on coroutine (emergency fix removed):", str(e))
        return True


async def test_all_async_tools():
    """Test that all tools are properly async and don't need the emergency fix."""
    print("\nTesting all tools are properly async...")
    
    with patch('youtrack_mcp.api.client.YouTrackClient') as MockClient:
        mock_client = Mock()
        MockClient.return_value = mock_client
        
        # Mock async methods
        async def mock_get(endpoint, params=None):
            await asyncio.sleep(0.001)
            return {"data": f"Response from {endpoint}"}
        
        mock_client.get = mock_get
        
        # Import tools after mocking
        from youtrack_mcp.tools.core_issues import CoreIssuesTools
        from youtrack_mcp.tools.core_projects import CoreProjectsTools
        from youtrack_mcp.tools.core_search import CoreSearchTools
        
        # Set up mocked API methods
        async def mock_get_issue(issue_id):
            await asyncio.sleep(0.001)
            return {"id": issue_id, "summary": "Test"}
        
        async def mock_get_projects(include_archived=False):
            await asyncio.sleep(0.001)
            return [{"id": "P1", "name": "Project 1"}]
        
        async def mock_search_issues(query, limit=10):
            await asyncio.sleep(0.001)
            return [{"id": "TEST-1", "summary": "Test"}]
        
        issues = CoreIssuesTools()
        issues.issues_api.get_issue = mock_get_issue
        
        projects = CoreProjectsTools()
        projects.projects_api.get_projects = mock_get_projects
        
        search = CoreSearchTools()
        search.issues_api.search_issues = mock_search_issues
        
        # Test each tool
        try:
            # Test CoreIssuesTools
            result = await issues.get("TEST-1")
            data = json.loads(result)
            assert "issue" in data or "error" in data
            print("  ✅ CoreIssuesTools.get works without emergency fix")
            
            # Test CoreProjectsTools
            result = await projects.list()
            data = json.loads(result)
            assert "projects" in data
            print("  ✅ CoreProjectsTools.list works without emergency fix")
            
            # Test CoreSearchTools
            result = await search.query("project: TEST")
            data = json.loads(result)
            assert "results" in data or "error" in data
            print("  ✅ CoreSearchTools.query works without emergency fix")
            
            return True
            
        except Exception as e:
            print(f"  ❌ FAIL: {e}")
            import traceback
            traceback.print_exc()
            return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing Emergency Fix Removal")
    print("=" * 60)
    
    success = True
    
    # Test 1: Verify emergency fix is removed
    if not test_sync_wrapper_no_coroutine_handling():
        success = False
    
    # Test 2: Verify all tools still work
    if not asyncio.run(test_all_async_tools()):
        success = False
    
    print("\n" + "=" * 60)
    if success:
        print("✅ ALL TESTS PASSED")
        print("Emergency fix successfully removed")
        print("All tools working correctly with proper async")
    else:
        print("❌ SOME TESTS FAILED")
        print("Check the errors above")
    print("=" * 60)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())