"""
Golden tests for core AI PLAN operations.

Tests the intent planning and analysis functionality.
"""

import pytest
import json
from unittest.mock import Mock, patch
from youtrack_mcp.tools.core_ai import CoreAITools
from youtrack_mcp.utils import format_json_response


class TestCoreAIPlan:
    """Test cases for AI PLAN operations."""

    def setup_method(self):
        """Set up test fixtures."""
        self.tools = CoreAITools()
        self.tools.ai_tools = Mock()

    def test_plan_create_issue_intent(self):
        """Test planning for issue creation intent."""
        intent = "Create a bug report for login issues"
        context = {"project": "DEMO"}

        result = self.tools.plan(intent=intent, context=context)

        result_data = json.loads(result)
        assert result_data["intent"] == intent
        assert result_data["context"] == context
        assert result_data["requires_confirmation"] is True
        assert "plan" in result_data
        assert "explanations" in result_data
        assert "suggested_tools" in result_data
        assert "estimated_complexity" in result_data

        # Check that it suggests issues.create tool
        assert "issues.create" in result_data["suggested_tools"]

    def test_plan_search_issues_intent(self):
        """Test planning for issue search intent."""
        intent = "Find all unresolved bugs assigned to me"
        context = {"project": "DEMO"}

        result = self.tools.plan(intent=intent, context=context)

        result_data = json.loads(result)
        assert result_data["intent"] == intent
        assert result_data["context"] == context
        assert result_data["requires_confirmation"] is True

        # Check that it suggests search tools
        assert "search.autosearch" in result_data["suggested_tools"]

    def test_plan_update_issue_intent(self):
        """Test planning for issue update intent."""
        intent = "Update the priority of issue DEMO-123 to high"
        context = {"project": "DEMO"}

        result = self.tools.plan(intent=intent, context=context)

        result_data = json.loads(result)
        assert result_data["intent"] == intent
        assert result_data["context"] == context
        assert result_data["requires_confirmation"] is True

        # Check that it suggests issues.patch tool
        assert "issues.patch" in result_data["suggested_tools"]

    def test_plan_create_project_intent(self):
        """Test planning for project creation intent."""
        intent = "Create a new project for mobile app development"
        context = {}

        result = self.tools.plan(intent=intent, context=context)

        result_data = json.loads(result)
        assert result_data["intent"] == intent
        assert result_data["context"] == context
        assert result_data["requires_confirmation"] is True

        # Check that it suggests projects.create tool
        assert "projects.create" in result_data["suggested_tools"]
        # High complexity for project creation
        assert result_data["estimated_complexity"] == "high"

    def test_plan_user_search_intent(self):
        """Test planning for user search intent."""
        intent = "Find users with admin role"
        context = {}

        result = self.tools.plan(intent=intent, context=context)

        result_data = json.loads(result)
        assert result_data["intent"] == intent
        assert result_data["context"] == context
        assert result_data["requires_confirmation"] is True

        # Check that it suggests users.search tool
        assert "users.search" in result_data["suggested_tools"]

    def test_plan_without_context(self):
        """Test planning without context."""
        intent = "Show me all open issues"

        result = self.tools.plan(intent=intent)

        result_data = json.loads(result)
        assert result_data["intent"] == intent
        assert result_data["context"] == {}
        assert result_data["requires_confirmation"] is True

    def test_plan_empty_context(self):
        """Test planning with empty context."""
        intent = "List all projects"
        context = {}

        result = self.tools.plan(intent=intent, context=context)

        result_data = json.loads(result)
        assert result_data["intent"] == intent
        assert result_data["context"] == context
        assert result_data["requires_confirmation"] is True

    def test_plan_with_project_context(self):
        """Test planning with project context."""
        intent = "Find bugs in this project"
        context = {"project": "MOBILE"}

        result = self.tools.plan(intent=intent, context=context)

        result_data = json.loads(result)
        assert result_data["intent"] == intent
        assert result_data["context"] == context
        assert result_data["requires_confirmation"] is True

        # Should include project context in explanations
        explanations = " ".join(result_data["explanations"])
        assert "MOBILE" in explanations

    def test_plan_complex_intent(self):
        """Test planning for complex multi-step intent."""
        intent = "Create a new project, add some issues, and assign users to them"
        context = {}

        result = self.tools.plan(intent=intent, context=context)

        result_data = json.loads(result)
        assert result_data["intent"] == intent
        assert result_data["context"] == context
        assert result_data["requires_confirmation"] is True

        # Should suggest multiple tools
        suggested_tools = result_data["suggested_tools"]
        assert "projects.create" in suggested_tools
        assert "issues.create" in suggested_tools
        assert "users.search" in suggested_tools

    def test_plan_unknown_intent(self):
        """Test planning for unknown/unrecognized intent."""
        intent = "Do something completely unrelated to YouTrack"
        context = {}

        result = self.tools.plan(intent=intent, context=context)

        result_data = json.loads(result)
        assert result_data["intent"] == intent
        assert result_data["context"] == context
        assert result_data["requires_confirmation"] is True

        # Should fall back to general search
        assert "search.autosearch" in result_data["suggested_tools"]
        assert result_data["estimated_complexity"] == "low"

    def test_plan_error_handling(self):
        """Test error handling in plan method."""
        intent = "Test intent"
        context = {"project": "TEST"}

        # Mock the _analyze_intent method to raise an exception
        with patch.object(self.tools, '_analyze_intent', side_effect=Exception("Analysis failed")):
            result = self.tools.plan(intent=intent, context=context)

            result_data = json.loads(result)
            assert "error" in result_data
            assert "Analysis failed" in result_data["error"]
            assert result_data["error_type"] == "Exception"
            assert result_data["intent"] == intent
            assert result_data["requires_confirmation"] is True

    def test_plan_with_special_characters(self):
        """Test planning with special characters in intent."""
        intent = "Find issues with @mentions and #hashtags in description"
        context = {}

        result = self.tools.plan(intent=intent, context=context)

        result_data = json.loads(result)
        assert result_data["intent"] == intent
        assert result_data["context"] == context
        assert result_data["requires_confirmation"] is True

    def test_plan_long_intent(self):
        """Test planning with a very long intent description."""
        intent = "I need to create a comprehensive project management system that includes multiple teams, various issue types, custom fields for tracking different metrics, user roles and permissions, automated workflows, and integration with external tools for better productivity and collaboration across the organization."
        context = {"project": "ENTERPRISE"}

        result = self.tools.plan(intent=intent, context=context)

        result_data = json.loads(result)
        assert result_data["intent"] == intent
        assert result_data["context"] == context
        assert result_data["requires_confirmation"] is True

        # Should suggest multiple tools for complex intent
        suggested_tools = result_data["suggested_tools"]
        assert len(suggested_tools) > 1

    def test_plan_case_insensitive_matching(self):
        """Test that intent matching is case insensitive."""
        intent = "CREATE A NEW ISSUE FOR BUG REPORTING"
        context = {}

        result = self.tools.plan(intent=intent, context=context)

        result_data = json.loads(result)
        assert result_data["intent"] == intent
        assert result_data["context"] == context

        # Should still recognize "CREATE" and suggest issues.create
        assert "issues.create" in result_data["suggested_tools"]

    def test_plan_multiple_keywords(self):
        """Test planning with multiple keywords in intent."""
        intent = "Search and find all issues that are assigned to users in the development team"
        context = {}

        result = self.tools.plan(intent=intent, context=context)

        result_data = json.loads(result)
        assert result_data["intent"] == intent
        assert result_data["context"] == context

        # Should suggest both search and user tools
        suggested_tools = result_data["suggested_tools"]
        assert "search.autosearch" in suggested_tools
        assert "users.search" in suggested_tools

    def test_plan_minimal_intent(self):
        """Test planning with minimal intent text."""
        intent = "issues"
        context = {}

        result = self.tools.plan(intent=intent, context=context)

        result_data = json.loads(result)
        assert result_data["intent"] == intent
        assert result_data["context"] == context
        assert result_data["requires_confirmation"] is True

        # Should fall back to general search for minimal input
        assert "search.autosearch" in result_data["suggested_tools"]