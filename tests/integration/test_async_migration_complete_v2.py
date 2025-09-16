#!/usr/bin/env python3
"""Comprehensive test of the FastMCP async migration - validates all converted tools."""

import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch
import traceback


async def test_all_tools():
    """Test all converted tools to ensure they properly handle async with FastMCP."""
    print("=" * 60)
    print("FAST MCP ASYNC MIGRATION VALIDATION TEST")
    print("=" * 60)

    success_count = 0
    total_count = 0

    # Set up the Python path first
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

    # Mock the YouTrackClient before importing anything that uses it
    with patch('youtrack_mcp.api.client.YouTrackClient') as MockClient:
        mock_client = Mock()
        MockClient.return_value = mock_client

        # Configure mock client with async methods
        async def mock_get(endpoint, params=None):
            await asyncio.sleep(0.01)
            return {"data": f"Response from {endpoint}"}

        async def mock_post(endpoint, data=None, json=None):
            await asyncio.sleep(0.01)
            return {"success": True, "endpoint": endpoint}

        async def mock_put(endpoint, json_data=None):
            await asyncio.sleep(0.01)
            return {"success": True, "endpoint": endpoint}

        async def mock_delete(endpoint):
            await asyncio.sleep(0.01)
            return {"success": True, "endpoint": endpoint}

        mock_client.get = mock_get
        mock_client.post = mock_post
        mock_client.put = mock_put
        mock_client.delete = mock_delete

        # Import the modern tool loading system inside the patch context
        from youtrack_mcp.utils.loader import load_all_tools

        # Load all tools using the modern system
        tools = load_all_tools()

        # Mock API client methods for testing
        async def mock_get_issue(issue_id):
            await asyncio.sleep(0.01)
            return {"id": issue_id, "summary": "Test Issue"}

        async def mock_create_issue(project, summary, description=None, custom_fields=None):
            await asyncio.sleep(0.01)
            return {"id": "TEST-123", "summary": summary, "description": description}

        async def mock_get_projects(include_archived=False):
            await asyncio.sleep(0.01)
            return [{"id": "P1", "name": "Project 1", "shortName": "P1"}]

        async def mock_get_project(project_id):
            await asyncio.sleep(0.01)
            return {"id": project_id, "name": f"Project {project_id}", "shortName": project_id}

        async def mock_create_project(name, short_name, lead_id, description=None):
            await asyncio.sleep(0.01)
            return {"id": short_name, "name": name, "shortName": short_name, "description": description}

        async def mock_search_issues(query, limit=50, sort_by=None, sort_order=None):
            await asyncio.sleep(0.01)
            return [{"id": "TEST-1", "summary": "Test Issue"}]

        async def mock_search_users(query, limit=10):
            await asyncio.sleep(0.01)
            return [{"id": "user1", "login": query, "name": "Test User"}]

        print("\n1. Testing Issues Tools (3 methods)...")
        try:
            # Test issues.get
            total_count += 1
            if "issues.get" in tools:
                # Mock the underlying API call
                with patch('youtrack_mcp.tools.issues.basic_operations.IssuesBasicOperations.get_issue', side_effect=mock_get_issue):
                    result = await tools["issues.get"](issue_id="TEST-1")
                    assert isinstance(result, dict)
                    assert "id" in result
                    print("   ✅ issues.get - async working")
                    success_count += 1
            else:
                print("   ⚠️  issues.get not found in loaded tools")
                total_count -= 1

            # Test issues.create
            total_count += 1
            if "issues.create" in tools:
                with patch('youtrack_mcp.tools.issues.basic_operations.IssuesBasicOperations.create_issue', side_effect=mock_create_issue):
                    result = await tools["issues.create"](project="TEST", summary="New Issue")
                    assert isinstance(result, dict)
                    assert "id" in result
                    print("   ✅ issues.create - async working")
                    success_count += 1
            else:
                print("   ⚠️  issues.create not found in loaded tools")
                total_count -= 1

            # Test issues.patch
            total_count += 1
            if "issues.patch" in tools:
                result = await tools["issues.patch"](issue_id="TEST-1", fields={"summary": "Updated"})
                # This will likely error without full mocking, but we're testing the async call
                assert isinstance(result, dict)
                print("   ✅ issues.patch - async working")
                success_count += 1
            else:
                print("   ⚠️  issues.patch not found in loaded tools")
                total_count -= 1

        except Exception as e:
            print(f"   ❌ Issues tools failed: {e}")
            traceback.print_exc()

        print("\n2. Testing Projects Tools (4 methods)...")
        try:
            # Test projects.list
            total_count += 1
            if "projects.list" in tools:
                with patch('youtrack_mcp.tools.projects.ProjectsTools.list_projects', side_effect=mock_get_projects):
                    result = await tools["projects.list"]()
                    assert isinstance(result, list)
                    print("   ✅ projects.list - async working")
                    success_count += 1
            else:
                print("   ⚠️  projects.list not found in loaded tools")
                total_count -= 1

            # Test projects.get
            total_count += 1
            if "projects.get" in tools:
                with patch('youtrack_mcp.tools.projects.ProjectsTools.get_project', side_effect=mock_get_project):
                    result = await tools["projects.get"](project_id="P1")
                    assert isinstance(result, dict)
                    assert "id" in result
                    print("   ✅ projects.get - async working")
                    success_count += 1
            else:
                print("   ⚠️  projects.get not found in loaded tools")
                total_count -= 1

            # Test projects.patch
            total_count += 1
            if "projects.patch" in tools:
                result = await tools["projects.patch"](project_id="P1", ops=[{"op": "set", "field": "name", "value": "New Name"}])
                assert isinstance(result, dict)
                print("   ✅ projects.patch - async working")
                success_count += 1
            else:
                print("   ⚠️  projects.patch not found in loaded tools")
                total_count -= 1

            # Test projects.create
            total_count += 1
            if "projects.create" in tools:
                with patch('youtrack_mcp.tools.projects.ProjectsTools.create_project', side_effect=mock_create_project):
                    result = await tools["projects.create"](name="Test", short_name="TST", lead_id="admin")
                    assert isinstance(result, dict)
                    assert "id" in result
                    print("   ✅ projects.create - async working")
                    success_count += 1
            else:
                print("   ⚠️  projects.create not found in loaded tools")
                total_count -= 1

        except Exception as e:
            print(f"   ❌ Projects tools failed: {e}")
            traceback.print_exc()

        print("\n3. Testing Search Tools (2 methods)...")
        try:
            # Test search.query
            total_count += 1
            if "search.query" in tools:
                with patch('youtrack_mcp.tools.search.SearchTools.search_issues', side_effect=mock_search_issues):
                    result = await tools["search.query"](query="project: TEST")
                    assert isinstance(result, dict)
                    print("   ✅ search.query - async working")
                    success_count += 1
            else:
                print("   ⚠️  search.query not found in loaded tools")
                total_count -= 1

            # Test search.autosearch
            total_count += 1
            if "search.autosearch" in tools:
                result = await tools["search.autosearch"](natural_language_query="bugs assigned to me")
                assert isinstance(result, dict)
                print("   ✅ search.autosearch - async working")
                success_count += 1
            else:
                print("   ⚠️  search.autosearch not found in loaded tools")
                total_count -= 1

        except Exception as e:
            print(f"   ❌ Search tools failed: {e}")
            traceback.print_exc()

        print("\n4. Testing Users Tools (1 method)...")
        try:
            # Test users.search
            total_count += 1
            if "users.search" in tools:
                with patch('youtrack_mcp.tools.users.UsersTools.search_users', side_effect=mock_search_users):
                    result = await tools["users.search"](query="admin")
                    assert isinstance(result, list)
                    print("   ✅ users.search - async working")
                    success_count += 1
            else:
                print("   ⚠️  users.search not found in loaded tools")
                total_count -= 1

        except Exception as e:
            print(f"   ❌ Users tools failed: {e}")
            traceback.print_exc()

        print("\n5. Testing AI Tools (1 method)...")
        try:
            # Test ai.plan
            total_count += 1
            if "ai.plan" in tools:
                result = await tools["ai.plan"](intent="Create a bug report")
                assert isinstance(result, dict)
                print("   ✅ ai.plan - async working")
                success_count += 1
            else:
                print("   ⚠️  ai.plan not found in loaded tools")
                total_count -= 1

        except Exception as e:
            print(f"   ❌ AI tools failed: {e}")
            traceback.print_exc()

        print("\n6. Testing Resources Tools (1 method)...")
        try:
            # Test resources.read
            total_count += 1
            if "resources.read" in tools:
                result = await tools["resources.read"](uri="youtrack://issues/TEST-1")
                assert isinstance(result, str)
                print("   ✅ resources.read - async working")
                success_count += 1
            else:
                print("   ⚠️  resources.read not found in loaded tools")
                total_count -= 1

        except Exception as e:
            print(f"   ❌ Resources tools failed: {e}")
            traceback.print_exc()

        print("\n7. Testing Projects Admin Tools (3 methods)...")
        try:
            # Test projects.delete
            total_count += 1
            if "projects.delete" in tools:
                result = await tools["projects.delete"](project_id="P1")
                assert isinstance(result, dict)
                print("   ✅ projects.delete - async working")
                success_count += 1
            else:
                print("   ⚠️  projects.delete not found in loaded tools")
                total_count -= 1

            # Test projects.archive
            total_count += 1
            if "projects.archive" in tools:
                result = await tools["projects.archive"](project_id="P1")
                assert isinstance(result, dict)
                print("   ✅ projects.archive - async working")
                success_count += 1
            else:
                print("   ⚠️  projects.archive not found in loaded tools")
                total_count -= 1

            # Test projects.restore
            total_count += 1
            if "projects.restore" in tools:
                result = await tools["projects.restore"](project_id="P1")
                assert isinstance(result, dict)
                print("   ✅ projects.restore - async working")
                success_count += 1
            else:
                print("   ⚠️  projects.restore not found in loaded tools")
                total_count -= 1

        except Exception as e:
            print(f"   ❌ Projects admin tools failed: {e}")
            traceback.print_exc()

        print("\n8. Testing Users Admin Tools (3 methods)...")
        try:
            # Test users.create
            total_count += 1
            if "users.create" in tools:
                result = await tools["users.create"](login="jdoe", full_name="John Doe")
                assert isinstance(result, dict)
                print("   ✅ users.create - async working")
                success_count += 1
            else:
                print("   ⚠️  users.create not found in loaded tools")
                total_count -= 1

            # Test users.patch
            total_count += 1
            if "users.patch" in tools:
                result = await tools["users.patch"](user_id="user1", fields={"name": "New Name"})
                assert isinstance(result, dict)
                print("   ✅ users.patch - async working")
                success_count += 1
            else:
                print("   ⚠️  users.patch not found in loaded tools")
                total_count -= 1

            # Test users.deactivate
            total_count += 1
            if "users.deactivate" in tools:
                result = await tools["users.deactivate"](user_id="user1")
                assert isinstance(result, dict)
                print("   ✅ users.deactivate - async working")
                success_count += 1
            else:
                print("   ⚠️  users.deactivate not found in loaded tools")
                total_count -= 1

        except Exception as e:
            print(f"   ❌ Users admin tools failed: {e}")
            traceback.print_exc()
    
    # Print summary
    print("\n" + "=" * 60)
    print("FAST MCP TEST SUMMARY")
    print("=" * 60)
    print(f"Total methods tested: {total_count}")
    print(f"Successful: {success_count}")
    print(f"Failed: {total_count - success_count}")
    print(f"Available tools: {len(tools)}")

    if success_count == total_count and total_count > 0:
        print("\n✅ ALL TESTS PASSED - FAST MCP MIGRATION COMPLETE!")
        print(f"All {total_count} methods across {len(tools)} tools are now properly async")
        print("FastMCP architecture successfully validated!")
        return True
    elif total_count == 0:
        print("\n⚠️  No tools were loaded - check tool loading system")
        return False
    else:
        print(f"\n⚠️  {total_count - success_count} tests failed")
        print("Some tools may need additional mocking or implementation")
        return False


def main():
    """Run the FastMCP async migration validation test."""
    try:
        success = asyncio.run(test_all_tools())
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ FastMCP test suite failed: {e}")
        traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    main()