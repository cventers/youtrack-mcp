"""
AI Service for YouTrack MCP Server.

Provides LLM-powered natural language to YQL translation.
"""

import json
import logging
from typing import Any, Dict, Optional, Union
from cachetools import TTLCache

from .openai_client import OpenAIClient
from ..utils import ErrorEnhancementResult, ErrorHandler
from . import QueryTranslationResult

logger = logging.getLogger(__name__)


class AIService:
    """
    Unified AI service.

    Error enhancement is always rule-based.
    NL to YQL translation requires LLM for ai.plan and search autosearch.
    """

    def __init__(self, openai_client: Optional[OpenAIClient] = None, error_handler: Optional[ErrorHandler] = None):
        """
        Initialize AI service.

        Args:
            openai_client: Optional OpenAIClient instance for NL to YQL
            error_handler: Optional ErrorHandler instance (will create if not provided)
        """
        self.openai_client = openai_client

        # Caches
        self.query_cache = TTLCache(maxsize=1000, ttl=3600)  # 1 hour

        # Error handler for rule-based error enhancement
        self.error_handler = error_handler or ErrorHandler()

        logger.info("AIService initialized (NL to YQL: LLM required)")

    @property
    def error_patterns(self):
        """Access error patterns from the error handler."""
        return self.error_handler.error_patterns

    def enhance_error_message(self, error: Union[Exception, str], context: Dict[str, Any]) -> ErrorEnhancementResult:
        """
        Enhance error message using rule-based processing.

        Args:
            error: Error exception or string
            context: Operation context

        Returns:
            Enhanced error result
        """
        return self.error_handler.enhance_error(error, context)

    def translate_nl_to_yql(self, natural_query: str, project_context: Optional[str] = None) -> QueryTranslationResult:
        """
        Translate natural language to YQL using LLM.

        Args:
            natural_query: Natural language query
            project_context: Optional project context

        Returns:
            Translation result
        """
        if not self.openai_client:
            return QueryTranslationResult(
                yql_query="",
                confidence=0.0,
                reasoning="LLM client not configured for natural language queries",
                original_input=natural_query,
                detected_entities={},
                suggestions=["Configure OpenAI client for ai.plan and search autosearch"]
            )

        return self._llm_translate_nl_to_yql(natural_query, project_context)





    def _llm_translate_nl_to_yql(self, natural_query: str, project_context: Optional[str]) -> QueryTranslationResult:
        """LLM-powered NL to YQL translation."""
        if not self.openai_client:
            raise RuntimeError("OpenAI client required for LLM mode")

        cache_key = f"llm_query:{hash(natural_query)}{hash(str(project_context))}"
        if cache_key in self.query_cache:
            return self.query_cache[cache_key]

        try:
            system_prompt = """You are a YouTrack Query Language (YQL) expert. Convert natural language queries to YQL.

YQL syntax examples:
- project: ProjectName
- assignee: me, assignee: Unassigned
- state: Open, state: {In Progress}
- priority: Critical, priority: High
- created: -7d .. *, created: 2025-01-01 .. 2025-01-31
- {Custom Field}: Value

Return only the YQL query, no explanations."""

            prompt = f"Convert this natural language query to YouTrack YQL: '{natural_query}'"
            if project_context:
                prompt += f"\nProject context: {project_context}"

            response = self.openai_client.complete(
                prompt=prompt,
                system=system_prompt,
                max_tokens=200,
                temperature=0.3
            )

            if response and response.get('content'):
                yql_query = response['content'].strip()
                if ':' in yql_query and not yql_query.startswith('I '):
                    result = QueryTranslationResult(
                        yql_query=yql_query,
                        confidence=response.get('confidence', 0.8),
                        reasoning="LLM translation",
                        original_input=natural_query,
                        detected_entities={"llm_generated": True},
                        suggestions=[f"Generated with {response.get('confidence', 0.8):.1f} confidence"]
                    )
                    self.query_cache[cache_key] = result
                    return result

            raise RuntimeError("LLM translation failed")

        except Exception as e:
            logger.error(f"LLM translation error: {e}")
            raise RuntimeError("LLM translation unavailable")

    def _llm_enhance_error(self, error: Union[Exception, str], context: Dict[str, Any]) -> ErrorEnhancementResult:
        """LLM-powered error enhancement."""
        if not self.openai_client:
            raise RuntimeError("OpenAI client required for LLM mode")

        try:
            system_prompt = """You are a YouTrack API expert helping users understand and fix errors.
Provide:
1. Enhanced explanation of what went wrong
2. Specific fix suggestion
3. Example correction
4. Learning tip for future queries

Be concise and practical."""

            prompt = f"""Error: {str(error)}
Context: {json.dumps(context, indent=2)}

Please enhance this error with helpful explanations and fix suggestions."""

            response = self.openai_client.complete(
                prompt=prompt,
                system=system_prompt,
                max_tokens=500,
                temperature=0.3
            )

            if response and response.get('content'):
                content = response['content'].strip()
                lines = content.split('\n')

                result = ErrorEnhancementResult(
                    enhanced_explanation=lines[0] if lines else content,
                    fix_suggestion=lines[1] if len(lines) > 1 else "Check the error message for specific details",
                    example_correction=lines[2] if len(lines) > 2 else "",
                    learning_tip=lines[3] if len(lines) > 3 else "Review YouTrack Query Language documentation",
                    confidence=response.get('confidence', 0.8)
                )
                return result

            raise RuntimeError("LLM enhancement failed")

        except Exception as e:
            logger.error(f"LLM enhancement error: {e}")
            raise RuntimeError("LLM enhancement unavailable")

    def _llm_analyze_intent(self, intent: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Use LLM to analyze intent and create execution plan."""
        if not self.openai_client:
            raise RuntimeError("OpenAI client required for LLM mode")

        try:
            system_prompt = """You are a YouTrack expert assistant. Analyze user intent and create a detailed execution plan.

Available tools:
- issues.create: Create new issues
- issues.get: Read issue details
- issues.patch: Update existing issues
- issues.delete: Delete issues
- search.autosearch: Natural language search for issues
- projects.list: List all projects
- projects.get: Get project details
- users.search: Search for users

Return a JSON plan with:
- intent: Original user intent
- context: Provided context
- requires_confirmation: Always true for safety
- plan: Array of action objects with tool, description, and parameters
- explanations: Array of human-readable explanations
- suggested_tools: Array of recommended tool names
- estimated_complexity: "low", "medium", or "high"

Be specific about which tools to use and what parameters they need."""

            prompt = f"""Analyze this user intent and create an execution plan: "{intent}"

Context: {json.dumps(context, indent=2)}

Return only valid JSON matching the specified format."""

            response = self.openai_client.complete(
                prompt=prompt,
                system=system_prompt,
                max_tokens=1000,
                temperature=0.3
            )

            if response and response.get('content'):
                content = response['content'].strip()
                # Try to parse as JSON
                try:
                    plan_data = json.loads(content)
                    # Ensure required fields
                    plan_data.setdefault('intent', intent)
                    plan_data.setdefault('context', context)
                    plan_data.setdefault('requires_confirmation', True)
                    plan_data.setdefault('plan', [])
                    plan_data.setdefault('explanations', [])
                    plan_data.setdefault('suggested_tools', [])
                    plan_data.setdefault('estimated_complexity', 'medium')
                    return plan_data
                except json.JSONDecodeError:
                    # If LLM didn't return valid JSON, create a basic plan
                    return {
                        'intent': intent,
                        'context': context,
                        'requires_confirmation': True,
                        'plan': [{'action': 'manual_review', 'description': 'LLM response parsing failed'}],
                        'explanations': [f'LLM analysis: {content[:200]}...'],
                        'suggested_tools': [],
                        'estimated_complexity': 'medium'
                    }

            raise RuntimeError("LLM analysis failed")

        except Exception as e:
            logger.error(f"LLM intent analysis error: {e}")
            raise RuntimeError("LLM intent analysis unavailable")