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
        with patch('youtrack_mcp.tools.ai_tools.AIToolsImpl') as mock_ai_tools:
            # Mock the AIToolsImpl instance
            mock_instance = MagicMock()
            mock_ai_tools.return_value = mock_instance

            tools = AITools()
            return tools

    @pytest.mark.asyncio
    async def test_plan_create_issue_intent(self, ai_tools):
        """Test planning for issue creation intent."""
        intent = "Create a bug report for login issues"
        context = {"project": "DEMO"}

        # Mock LLM analysis to fail, forcing rule-based fallback
        ai_tools.ai_tools.analyze_intent.side_effect = Exception("LLM unavailable")

        result = await ai_tools.plan(intent, context)
        result_data = json.loads(result)

        assert result_data["intent"] == intent
        assert result_data["context"] == context
        assert result_data["requires_confirmation"] is True
        assert len(result_data["plan"]) > 0
        assert "issues.create" in result_data["suggested_tools"]
        assert any("create" in explanation.lower() for explanation in result_data["explanations"])

    @pytest.mark.asyncio
    async def test_plan_search_intent(self, ai_tools):
        """Test planning for search intent."""
        intent = "Find all open bugs assigned to me"
        context = {}

        # Mock LLM analysis to fail, forcing rule-based fallback
        ai_tools.ai_tools.analyze_intent.side_effect = Exception("LLM unavailable")

        result = await ai_tools.plan(intent, context)
        result_data = json.loads(result)

        assert result_data["intent"] == intent
        assert result_data["requires_confirmation"] is True
        assert len(result_data["plan"]) > 0
        assert "search.autosearch" in result_data["suggested_tools"]
        assert any("search" in explanation.lower() for explanation in result_data["explanations"])

    @pytest.mark.asyncio
    async def test_plan_update_intent(self, ai_tools):
        """Test planning for issue update intent."""
        intent = "Update the status of issue DEMO-123 to fixed"
        context = {"issue_id": "DEMO-123"}

        # Mock LLM analysis to fail, forcing rule-based fallback
        ai_tools.ai_tools.analyze_intent.side_effect = Exception("LLM unavailable")

        result = await ai_tools.plan(intent, context)
        result_data = json.loads(result)

        assert result_data["intent"] == intent
        assert result_data["requires_confirmation"] is True
        assert len(result_data["plan"]) > 0
        assert "issues.patch" in result_data["suggested_tools"]
        assert any("update" in explanation.lower() for explanation in result_data["explanations"])

    @pytest.mark.asyncio
    async def test_plan_with_llm_success(self, ai_tools):
        """Test planning with successful LLM analysis."""
        intent = "Create a new feature request"
        context = {"project": "DEMO"}

        # Mock successful LLM response
        llm_response = {
            "intent": intent,
            "context": context,
            "requires_confirmation": True,
            "plan": [{"action": "create_feature", "tool": "issues.create", "description": "Create feature request"}],
            "explanations": ["LLM detected feature creation intent"],
            "suggested_tools": ["issues.create"],
            "estimated_complexity": "medium"
        }
        ai_tools.ai_tools.analyze_intent.return_value = json.dumps(llm_response)

        result = await ai_tools.plan(intent, context)
        result_data = json.loads(result)

        assert result_data["intent"] == intent
        assert result_data["context"] == context
        assert result_data["requires_confirmation"] is True
        assert len(result_data["plan"]) == 1
        assert result_data["plan"][0]["action"] == "create_feature"
        assert "issues.create" in result_data["suggested_tools"]

    @pytest.mark.asyncio
    async def test_plan_with_llm_error_fallback(self, ai_tools):
        """Test planning with LLM error that falls back to rule-based."""
        intent = "Create a bug report"
        context = {"project": "DEMO"}

        # Mock LLM analysis to return error
        ai_tools.ai_tools.analyze_intent.return_value = json.dumps({"error": "LLM service unavailable"})

        result = await ai_tools.plan(intent, context)
        result_data = json.loads(result)

        # Should fall back to rule-based analysis
        assert result_data["intent"] == intent
        assert result_data["requires_confirmation"] is True
        assert len(result_data["plan"]) > 0
        assert "issues.create" in result_data["suggested_tools"]

    @pytest.mark.asyncio
    async def test_plan_with_exception_handling(self, ai_tools):
        """Test planning with exception handling."""
        intent = "Invalid intent that causes errors"
        context = {}

        # Mock LLM analysis to raise exception
        ai_tools.ai_tools.analyze_intent.side_effect = RuntimeError("Test error")

        result = await ai_tools.plan(intent, context)
        result_data = json.loads(result)

        # Should return error response
        assert "error" in result_data
        assert result_data["error_type"] == "RuntimeError"
        assert result_data["intent"] == intent
        assert result_data["requires_confirmation"] is True

    @pytest.mark.asyncio
    async def test_plan_empty_context(self, ai_tools):
        """Test planning with empty context."""
        intent = "List all projects"
        context = None

        # Mock LLM analysis to fail, forcing rule-based fallback
        ai_tools.ai_tools.analyze_intent.side_effect = Exception("LLM unavailable")

        result = await ai_tools.plan(intent, context)
        result_data = json.loads(result)

        assert result_data["intent"] == intent
        assert result_data["context"] == {}
        assert result_data["requires_confirmation"] is True

    def test_get_tool_definitions(self, ai_tools):
        """Test getting tool definitions."""
        definitions = ai_tools.get_tool_definitions()

        assert isinstance(definitions, dict)
        assert "ai.plan" in definitions
        assert "description" in definitions["ai.plan"]
        assert "function" in definitions["ai.plan"]
        assert callable(definitions["ai.plan"]["function"])