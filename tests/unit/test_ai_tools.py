"""
Unit tests for AI planning tools module.

Tests the ai.plan method which provides intent analysis and planning.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from youtrack_mcp.tools.ai_tools import AITools


class TestAITools:
    """Test cases for AI planning tools."""

    @pytest.fixture
    def ai_tools(self):
        """Create AI tools instance with mocked dependencies."""
        with patch('youtrack_mcp.ai.registry.ai_registry') as mock_registry:
            # Mock the AI service
            mock_ai_service = MagicMock()
            mock_ai_service.analyze_intent = AsyncMock()
            mock_error_handler = MagicMock()

            mock_registry.ai_service = mock_ai_service
            mock_registry.error_handler = mock_error_handler

            tools = AITools()
            tools._mock_ai_service = mock_ai_service  # Store for test access
            return tools

    @pytest.mark.asyncio
    async def test_plan_create_issue_intent(self, ai_tools):
        """Test planning for issue creation intent."""
        intent = "Create a bug report for login issues"
        context = {"project": "DEMO"}

        # Mock the AI service response
        ai_tools._mock_ai_service.analyze_intent.return_value = {
            "intent": intent,
            "context": context,
            "requires_confirmation": True,
            "plan": [
                {
                    "step": 1,
                    "action": "Create issue",
                    "details": "Create a new bug report in project DEMO"
                }
            ],
            "suggested_tools": ["issues.create"],
            "explanations": ["Create a new issue for the bug report"]
        }

        result = await ai_tools.plan(intent, context)

        assert result["intent"] == intent
        assert result["context"] == context
        assert result["requires_confirmation"] is True
        assert len(result["plan"]) > 0
        assert "issues.create" in result["suggested_tools"]

    @pytest.mark.asyncio
    async def test_plan_search_intent(self, ai_tools):
        """Test planning for search intent."""
        intent = "Find all open bugs assigned to me"

        # Mock the AI service response
        ai_tools._mock_ai_service.analyze_intent.return_value = {
            "intent": intent,
            "context": {},
            "requires_confirmation": False,
            "plan": [
                {
                    "step": 1,
                    "action": "Search issues",
                    "details": "Search for open bugs assigned to current user"
                }
            ],
            "suggested_tools": ["search.query"],
            "explanations": ["Execute search query to find matching issues"]
        }

        result = await ai_tools.plan(intent)

        assert result["intent"] == intent
        assert "search.query" in result["suggested_tools"]
        assert result["requires_confirmation"] is False

    @pytest.mark.asyncio
    async def test_plan_update_intent(self, ai_tools):
        """Test planning for update intent."""
        intent = "Close all issues in sprint 2024.1"
        context = {"project": "PROJ"}

        # Mock the AI service response
        ai_tools._mock_ai_service.analyze_intent.return_value = {
            "intent": intent,
            "context": context,
            "requires_confirmation": True,
            "plan": [
                {
                    "step": 1,
                    "action": "Find issues",
                    "details": "Search for issues in sprint 2024.1"
                },
                {
                    "step": 2,
                    "action": "Update issues",
                    "details": "Set state to closed for each issue"
                }
            ],
            "suggested_tools": ["search.query", "issues.patch"],
            "explanations": [
                "First search for issues in the sprint",
                "Then update each issue to closed state"
            ]
        }

        result = await ai_tools.plan(intent, context)

        assert result["intent"] == intent
        assert result["context"] == context
        assert result["requires_confirmation"] is True
        assert len(result["plan"]) == 2
        assert "search.query" in result["suggested_tools"]
        assert "issues.patch" in result["suggested_tools"]

    @pytest.mark.asyncio
    async def test_plan_with_llm_success(self, ai_tools):
        """Test successful LLM analysis."""
        intent = "Generate weekly status report"

        # Mock successful LLM response
        expected_response = {
            "intent": intent,
            "context": {},
            "requires_confirmation": False,
            "plan": [
                {
                    "step": 1,
                    "action": "Gather data",
                    "details": "Collect issue statistics for the week"
                }
            ],
            "suggested_tools": ["search.query"],
            "explanations": ["Query issues for weekly statistics"]
        }
        ai_tools._mock_ai_service.analyze_intent.return_value = expected_response

        result = await ai_tools.plan(intent)

        assert result == expected_response
        ai_tools._mock_ai_service.analyze_intent.assert_called_once_with(intent, {})

    @pytest.mark.asyncio
    async def test_plan_with_llm_error_fallback(self, ai_tools):
        """Test fallback to rule-based analysis when LLM fails."""
        intent = "Create a new task"

        # Mock LLM failure
        ai_tools._mock_ai_service.analyze_intent.side_effect = Exception("LLM unavailable")

        result = await ai_tools.plan(intent)

        # Should get a fallback response
        assert result["intent"] == intent
        assert result["requires_confirmation"] is True
        assert len(result["plan"]) > 0
        # Fallback should recognize "create" intent
        assert any("create" in tool.lower() for tool in result["suggested_tools"])

    @pytest.mark.asyncio
    async def test_plan_with_exception_handling(self, ai_tools):
        """Test exception handling in planning."""
        intent = "Do something complex"

        # Mock an exception
        ai_tools._mock_ai_service.analyze_intent.side_effect = ValueError("Invalid input")

        result = await ai_tools.plan(intent)

        # Should return a safe fallback
        assert result["intent"] == intent
        assert result["requires_confirmation"] is True
        assert "error" not in result  # Should handle error gracefully

    @pytest.mark.asyncio
    async def test_plan_empty_context(self, ai_tools):
        """Test planning with empty context."""
        intent = "List my issues"

        # Mock response
        ai_tools._mock_ai_service.analyze_intent.return_value = {
            "intent": intent,
            "context": {},
            "requires_confirmation": False,
            "plan": [{"step": 1, "action": "Search", "details": "Find user's issues"}],
            "suggested_tools": ["search.query"],
            "explanations": ["Search for issues assigned to current user"]
        }

        result = await ai_tools.plan(intent)

        assert result["intent"] == intent
        assert result["context"] == {}
        ai_tools._mock_ai_service.analyze_intent.assert_called_once_with(intent, {})

    def test_get_tool_definitions(self):
        """Test getting tool definitions."""
        # This is now a standalone function, not a method
        from youtrack_mcp.tools.ai_tools import get_tool_definitions

        tools = get_tool_definitions()

        assert len(tools) == 1
        assert tools[0]["name"] == "ai_plan"
        assert "intent" in tools[0]["input_schema"]["properties"]
        assert "context" in tools[0]["input_schema"]["properties"]