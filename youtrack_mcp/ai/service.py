"""
AI Service for YouTrack MCP Server.

Provides LLM-powered natural language to YQL translation with structured outputs.
"""

import asyncio
import json
import logging
from typing import Any, Dict, Optional, Union
from cachetools import TTLCache

from .openai_client import OpenAIClient, OutputMode
from .errors import StructuredOutputError, ProviderError
from .models import (
    YQLTranslationResponse,
    ErrorEnhancementResponse,
    IntentAnalysisResponse,
    IntentPlanStep
)
from ..utils import ErrorEnhancementResult, ErrorHandler
from . import QueryTranslationResult
from .template_loader import get_template_loader

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

        # Template loader for prompt management
        self.template_loader = get_template_loader()

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

    async def translate_nl_to_yql(self, natural_query: str, project_context: Optional[str] = None) -> QueryTranslationResult:
        """
        Translate natural language to YQL using LLM with structured output.

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

        return await self._llm_translate_nl_to_yql(natural_query, project_context)

    def translate_nl_to_yql_sync(self, natural_query: str, project_context: Optional[str] = None) -> QueryTranslationResult:
        """
        Synchronous wrapper for translate_nl_to_yql (backward compatibility).
        """
        return asyncio.run(self.translate_nl_to_yql(natural_query, project_context))





    async def _llm_translate_nl_to_yql(self, natural_query: str, project_context: Optional[str]) -> QueryTranslationResult:
        """LLM-powered NL to YQL translation with structured output."""
        if not self.openai_client:
            raise RuntimeError("OpenAI client required for LLM mode")

        cache_key = f"llm_query:{hash(natural_query)}{hash(str(project_context))}"
        if cache_key in self.query_cache:
            return self.query_cache[cache_key]

        try:
            # Load prompts from templates
            system_prompt = """You are an expert YouTrack Query Language (YQL) assistant. Your role is to translate natural language requests into precise YQL queries.

Key capabilities:
- Deep understanding of YQL syntax, operators, and field references
- Knowledge of all YouTrack entities (issues, projects, users, custom fields)
- Ability to handle complex date ranges and relative time expressions
- Understanding of field type-specific query patterns

Always provide accurate, optimized queries that follow YouTrack best practices."""

            prompt = f"""Task: Convert the following natural language query to YQL.

Natural Query: {natural_query}"""
            if project_context:
                prompt += f"\nProject Context: {project_context}"

            prompt += """

Requirements:
- Generate the most accurate YQL query for the request
- Use proper syntax for multi-word values (curly braces)
- Apply correct date formats and operators
- Consider the project context if provided"""

            # Use structured output
            response = await self.openai_client.complete_structured(
                prompt=prompt,
                response_model=YQLTranslationResponse,
                system=system_prompt,
                max_tokens=500,
                temperature=0.3
            )

            # Convert to QueryTranslationResult for backward compatibility
            result = QueryTranslationResult(
                yql_query=response.yql_query,
                confidence=response.confidence,
                reasoning=response.reasoning,
                original_input=natural_query,
                detected_entities=response.detected_entities,
                suggestions=response.alternative_queries or response.warnings
            )

            self.query_cache[cache_key] = result
            return result

        except StructuredOutputError as e:
            logger.error(f"Structured output error in YQL translation: {e.to_dict()}")
            raise RuntimeError(f"YQL translation failed: {e.message}")
        except ProviderError as e:
            logger.error(f"Provider error in YQL translation: {e.to_dict()}")
            raise RuntimeError(f"LLM provider error: {e.message}")
        except Exception as e:
            logger.error(f"Unexpected error in YQL translation: {e}")
            raise RuntimeError("LLM translation unavailable")

    def _llm_enhance_error(self, error: Union[Exception, str], context: Dict[str, Any]) -> ErrorEnhancementResult:
        """LLM-powered error enhancement."""
        if not self.openai_client:
            raise RuntimeError("OpenAI client required for LLM mode")

        try:
            # Load prompts from templates
            system_prompt = self.template_loader.get_system_prompt("error_enhancement")
            prompt = self.template_loader.get_user_prompt(
                "error_user_prompt",
                error=str(error),
                context=context
            )

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

    async def analyze_intent(self, intent: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze user intent with structured output."""
        if not self.openai_client:
            raise RuntimeError("OpenAI client required for intent analysis")

        try:
            system_prompt = """You are an expert YouTrack automation assistant that analyzes user intent and creates detailed execution plans.

Core competencies:
- Understanding complex multi-step operations
- Risk assessment and validation requirements
- Knowledge of YouTrack permissions and constraints
- Ability to decompose tasks into atomic operations

Always provide safe, idempotent plans with proper error handling."""

            prompt = f"""Analyze the user's intent and create an execution plan:

Intent: {intent}
Context:"""
            if context.get('current_project'):
                prompt += f"\n- Project: {context['current_project']}"
            if context.get('user_permissions'):
                prompt += f"\n- User Permissions: {context['user_permissions']}"
            if context.get('available_resources'):
                prompt += f"\n- Available Resources: {context['available_resources']}"

            prompt += """

Generate a detailed plan including:
1. Step-by-step operations
2. Required validations
3. Potential risks and mitigations
4. Rollback strategy if needed"""

            # Use structured output
            response = await self.openai_client.complete_structured(
                prompt=prompt,
                response_model=IntentAnalysisResponse,
                system=system_prompt,
                max_tokens=1500,
                temperature=0.3
            )

            # Convert to dictionary format for backward compatibility
            plan_dicts = [
                {
                    'step': step.step,
                    'tool': step.tool,
                    'description': step.description,
                    'parameters': step.parameters,
                    'expected_result': step.expected_result,
                    'error_handling': step.error_handling
                }
                for step in response.plan
            ]

            result = {
                'intent': response.intent,
                'intent_category': response.intent_category,
                'confidence': response.confidence,
                'detected_entities': response.detected_entities,
                'requires_confirmation': response.requires_confirmation,
                'plan': plan_dicts,
                'warnings': response.warnings,
                'estimated_complexity': response.estimated_complexity,
                'alternative_interpretations': response.alternative_interpretations,
                'rollback_plan': response.rollback_plan,
                # Backward compatibility fields
                'context': context,
                'explanations': response.warnings,
                'suggested_tools': [step.tool for step in response.plan[:3]]
            }

            return result

        except StructuredOutputError as e:
            logger.error(f"Structured output error in intent analysis: {e.to_dict()}")
            raise RuntimeError(f"Intent analysis failed: {e.message}")
        except ProviderError as e:
            logger.error(f"Provider error in intent analysis: {e.to_dict()}")
            raise RuntimeError(f"LLM provider error: {e.message}")
        except Exception as e:
            logger.error(f"Unexpected error in intent analysis: {e}")
            raise RuntimeError("LLM intent analysis unavailable")

    def _llm_analyze_intent(self, intent: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronous wrapper for analyze_intent (backward compatibility)."""
        return asyncio.run(self.analyze_intent(intent, context))