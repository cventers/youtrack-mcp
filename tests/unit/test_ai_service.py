"""
Tests for AIService.
"""

import pytest
from unittest.mock import Mock, patch
from youtrack_mcp.ai.service import AIService, ErrorEnhancementResult
from youtrack_mcp.ai import QueryTranslationResult


class TestAIService:
    """Test AIService functionality."""

    def test_init_without_client(self):
        """Test initialization without OpenAI client."""
        service = AIService()
        assert service.openai_client is None

    def test_init_with_client(self):
        """Test initialization with OpenAI client."""
        mock_client = Mock()
        service = AIService(openai_client=mock_client)
        assert service.openai_client == mock_client

    @patch('youtrack_mcp.utils.ErrorHandler._load_error_patterns')
    def test_load_error_patterns(self, mock_load_patterns):
        """Test loading error patterns."""
        # Mock the _load_error_patterns method to return test patterns
        mock_load_patterns.return_value = [
            {
                'id': 'test',
                'match': 'exact|test error',
                'scope': 'test',
                'classification': {
                    'category': 'test_error',
                    'severity': 'low'
                },
                'explanation': 'Test error',
                'remediation_steps': ['Fix test']
            }
        ]

        service = AIService()
        patterns = service.error_patterns
        assert len(patterns) == 1
        assert patterns[0]['id'] == 'test'

    def test_translate_nl_to_yql_without_client(self):
        """Test NL to YQL without OpenAI client."""
        service = AIService()
        result = service.translate_nl_to_yql("test query")

        assert isinstance(result, QueryTranslationResult)
        assert result.yql_query == ""
        assert result.confidence == 0.0
        assert "not configured" in result.reasoning

    def test_translate_nl_to_yql_with_client(self):
        """Test NL to YQL with OpenAI client."""
        mock_client = Mock()
        mock_client.complete.return_value = {
            "content": "assignee: me",
            "usage": {"total_tokens": 10},
            "confidence": 0.8
        }

        service = AIService(openai_client=mock_client)
        result = service.translate_nl_to_yql("bugs assigned to me")

        assert isinstance(result, QueryTranslationResult)
        assert result.yql_query == "assignee: me"
        assert result.confidence == 0.8
        assert result.reasoning == "LLM translation"
        mock_client.complete.assert_called_once()

    def test_enhance_error_message_rule_based(self):
        """Test error enhancement (always rule-based)."""
        service = AIService()
        result = service.enhance_error_message("Invalid token provided", {})

        assert isinstance(result, ErrorEnhancementResult)
        assert "authentication" in result.enhanced_explanation.lower()
        assert result.confidence == 0.8