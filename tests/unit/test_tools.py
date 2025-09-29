"""
Unit tests for tool loading.
"""

import pytest
from unittest.mock import Mock, patch


class TestToolLoading:
    """Test tool loading."""

    @pytest.fixture
    def mock_youtrack_client(self):
        """Create mock YouTrack client."""
        with patch("youtrack_mcp.api.client.YouTrackClient") as mock_class:
            mock_instance = Mock()
            mock_instance.aclose = Mock()
            mock_instance.get = Mock()
            mock_instance.post = Mock()
            mock_class.return_value = mock_instance

            yield {
                "client": mock_instance,
                "mock_close": mock_instance.aclose,
                "mock_get": mock_instance.get,
                "mock_post": mock_instance.post,
            }

    @pytest.mark.unit
    def test_tool_loading_basic(self, mock_youtrack_client):
        """Test basic tool loading."""
        # Tools are now loaded via FastMCP decorators in server_fastmcp.py
        # This test verifies the tools can be imported
        from youtrack_mcp.tools.issues_tools import IssuesTools
        from youtrack_mcp.tools.projects_tools import ProjectsTools
        from youtrack_mcp.tools.users_tools import UsersTools
        from youtrack_mcp.tools.search_tools import SearchTools

        # Verify classes can be instantiated
        issues = IssuesTools()
        projects = ProjectsTools()
        users = UsersTools()

        assert issues is not None
        assert projects is not None
        assert users is not None

    @pytest.mark.unit
    def test_tool_definitions_integration(self, mock_youtrack_client):
        """Test that tool definitions are properly integrated."""
        from youtrack_mcp.tools.issues_tools import IssuesTools
        from youtrack_mcp.tools.projects_tools import ProjectsTools
        from youtrack_mcp.tools.users_tools import UsersTools

        # Create instances
        issues = IssuesTools()
        projects = ProjectsTools()
        users = UsersTools()

        # Check that tools have expected methods
        assert hasattr(issues, 'get')
        assert hasattr(issues, 'create')
        assert hasattr(issues, 'patch')

        assert hasattr(projects, 'list')
        assert hasattr(projects, 'get')

        assert hasattr(users, 'search')

    @pytest.mark.unit
    def test_tool_initialization(self):
        """Test tool initialization without dependencies."""
        # Import tool classes
        from youtrack_mcp.tools.issues_tools import IssuesTools
        from youtrack_mcp.tools.projects_tools import ProjectsTools
        from youtrack_mcp.tools.users_tools import UsersTools
        from youtrack_mcp.tools.search_tools import SearchTools

        # Mock the YouTrackClient to avoid actual connection
        with patch("youtrack_mcp.tools.issues_tools.YouTrackClient") as mock_client:
            with patch("youtrack_mcp.tools.projects_tools.YouTrackClient") as mock_client2:
                with patch("youtrack_mcp.tools.users_tools.YouTrackClient") as mock_client3:
                    with patch("youtrack_mcp.tools.search_tools.YouTrackClient") as mock_client4:
                        # Create instances
                        issues = IssuesTools()
                        projects = ProjectsTools()
                        users = UsersTools()
                        search = SearchTools(ai_tools=None)

                        # Verify instances are created
                        assert issues.client is not None
                        assert projects.client is not None
                        assert users.client is not None
                        assert search.client is not None

    @pytest.mark.unit
    def test_search_tools_with_ai(self):
        """Test SearchTools with AI tools dependency."""
        from youtrack_mcp.tools.search_tools import SearchTools
        from youtrack_mcp.tools.ai_tools import AITools

        # Mock dependencies
        with patch("youtrack_mcp.tools.search_tools.YouTrackClient"):
            with patch("youtrack_mcp.ai.registry.ai_registry") as mock_registry:
                mock_registry.ai_service = Mock()
                mock_registry.error_handler = Mock()

                # Create AI tools
                ai_tools = AITools()

                # Create search tools with AI
                search = SearchTools(ai_tools=ai_tools)

                assert search.ai_tools is not None
                assert search.ai_tools == ai_tools