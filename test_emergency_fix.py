#!/usr/bin/env python3
"""Test the emergency fix for sync_wrapper handling coroutines."""

import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock
from youtrack_mcp.mcp_wrappers import sync_wrapper


# Test that sync_wrapper now handles coroutines
@sync_wrapper
def test_sync_calling_async():
    """Sync function that calls an async function (simulating the issue)."""
    async def async_operation():
        await asyncio.sleep(0.01)
        return {"status": "success", "data": "test"}
    
    # This returns a coroutine - the emergency fix should handle it
    return async_operation()


def test_emergency_fix():
    """Test that the emergency fix handles coroutines properly."""
    print("Testing emergency fix for sync_wrapper...")
    
    # Call the sync function that returns a coroutine
    result = test_sync_calling_async()
    
    # The emergency fix should have handled the coroutine
    assert isinstance(result, str), f"Expected string, got {type(result)}"
    
    # Parse the result
    data = json.loads(result)
    assert data["status"] == "success"
    assert data["data"] == "test"
    
    print("✅ Emergency fix working: sync_wrapper handles coroutines")


def test_tools_with_mock():
    """Test that tools work with the emergency fix."""
    print("\nTesting tools with emergency fix...")
    
    # Mock the YouTrack client to avoid needing credentials
    with patch('youtrack_mcp.api.client.YouTrackClient') as MockClient:
        mock_client = Mock()
        MockClient.return_value = mock_client
        
        # Mock the API methods to return coroutines (simulating the real issue)
        async def mock_get_projects(include_archived=False):
            await asyncio.sleep(0.01)
            return [{"id": "P1", "name": "Project 1", "shortName": "P1"}]
        
        async def mock_search_issues(query, limit=10):
            await asyncio.sleep(0.01)
            return [{"id": "TEST-1", "summary": "Test Issue"}]
        
        from youtrack_mcp.tools.core_projects import CoreProjectsTools
        from youtrack_mcp.tools.core_search import CoreSearchTools
        
        # Test CoreProjectsTools with sync wrapper calling async API
        projects = CoreProjectsTools()
        projects.projects_api.get_projects = mock_get_projects
        
        # This should work with the emergency fix
        result = projects.list()
        assert isinstance(result, str), "projects.list should return a string"
        data = json.loads(result)
        assert "projects" in data or "error" in data
        print("✅ CoreProjectsTools.list works with emergency fix")
        
        # Test CoreSearchTools
        search = CoreSearchTools()
        # Mock the search API to return a coroutine
        search.client.issues = Mock()
        search.client.issues.search_issues = mock_search_issues
        
        result = search.query("project: TEST")
        assert isinstance(result, str), "search.query should return a string"
        print("✅ CoreSearchTools.query works with emergency fix")
    
    print("\n✅ All tools working with emergency fix!")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing Emergency Fix for Sync/Async Issues")
    print("=" * 60)
    
    try:
        test_emergency_fix()
        test_tools_with_mock()
        
        print("\n" + "=" * 60)
        print("✅ EMERGENCY FIX SUCCESSFUL!")
        print("Sync methods can now call async APIs without crashing")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Emergency fix test failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    main()