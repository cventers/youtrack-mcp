"""
Tests for AIService.
"""

import pytest
from unittest.mock import Mock, patch
from youtrack_mcp.ai.service import AIService, QueryTranslationResult, ErrorEnhancementResult


class TestAIService:
    """Test AIService functionality."""

    def test_init_rule_mode(self):
        """Test initialization in rule mode."""
        service = AIService(mode="rule")
        assert service.mode == "rule"
        assert service.openai_client is None

    def test_init_llm_mode(self):
        """Test initialization in llm mode."""
        mock_client = Mock()
        service = AIService(mode="llm", openai_client=mock_client)
        assert service.mode == "llm"
        assert service.openai_client == mock_client

    def test_init_invalid_mode(self):
        """Test initialization with invalid mode."""
        with pytest.raises(ValueError, match="Invalid mode"):
            AIService(mode="invalid")

    @patch('youtrack_mcp.ai.service.Path')
    def test_load_error_patterns(self, mock_path):
        """Test loading error patterns."""
        mock_path.return_value.parent.parent.parent = Mock()
        mock_path.return_value.parent.parent.parent.__truediv__ = Mock(return_value=Mock())

        with patch('builtins.open') as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = """
version: "1.0"
patterns:
  - id: "test"
    match: "exact|test error"
    scope: "test"
    classification:
      category: "test_error"
      severity: "low"
    explanation: "Test error"
    remediation_steps:
      - "Fix test"
"""

            service = AIService(mode="rule")
            patterns = service.error_patterns
            assert len(patterns) == 1
            assert patterns[0]['id'] == 'test'

    def test_translate_nl_to_yql_off_mode(self):
        """Test NL to YQL in off mode."""
        service = AIService(mode="off")
        result = service.translate_nl_to_yql("test query")

        assert isinstance(result, QueryTranslationResult)
        assert result.yql_query == ""
        assert result.confidence == 0.0
        assert "disabled" in result.reasoning

    def test_translate_nl_to_yql_rule_mode(self):
        """Test NL to YQL in rule mode."""
        service = AIService(mode="rule")
        result = service.translate_nl_to_yql("bugs assigned to me")

        assert isinstance(result, QueryTranslationResult)
        assert "assignee: me" in result.yql_query
        assert result.confidence >= 0.0
        assert result.reasoning == "Rule-based translation"

    def test_translate_nl_to_yql_llm_mode(self):
        """Test NL to YQL in llm mode."""
        mock_client = Mock()
        mock_client.complete.return_value = {
            "content": "assignee: me",
            "usage": {"total_tokens": 10},
            "confidence": 0.8
        }

        service = AIService(mode="llm", openai_client=mock_client)
        result = service.translate_nl_to_yql("bugs assigned to me")

        assert isinstance(result, QueryTranslationResult)
        assert result.yql_query == "assignee: me"
        assert result.confidence == 0.8
        assert result.reasoning == "LLM translation"
        mock_client.complete.assert_called_once()

    def test_enhance_error_message_off_mode(self):
        """Test error enhancement in off mode."""
        service = AIService(mode="off")
        result = service.enhance_error_message("test error", {})

        assert isinstance(result, ErrorEnhancementResult)
        assert "disabled" in result.enhanced_explanation
        assert result.confidence == 0.0

    def test_enhance_error_message_rule_mode(self):
        """Test error enhancement in rule mode."""
        service = AIService(mode="rule")
        result = service.enhance_error_message("Invalid token provided", {})

        assert isinstance(result, ErrorEnhancementResult)
        assert "authentication" in result.enhanced_explanation.lower()
        assert result.confidence == 0.8

    def test_enhance_error_message_llm_mode(self):
        """Test error enhancement in llm mode."""
        mock_client = Mock()
        mock_client.complete.return_value = {
            "content": "Authentication failed\nCheck token\n\nNext steps",
            "usage": {"total_tokens": 20},
            "confidence": 0.9
        }

        service = AIService(mode="llm", openai_client=mock_client)
        result = service.enhance_error_message("Invalid token", {})

        assert isinstance(result, ErrorEnhancementResult)
        assert result.enhanced_explanation == "Authentication failed"
        assert result.fix_suggestion == "Check token"
        assert result.confidence == 0.9
        mock_client.complete.assert_called_once()