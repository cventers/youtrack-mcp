"""
AI Service for YouTrack MCP Server.

Provides unified AI functionality:
- Error enhancement: Always rule-based processing
- NL to YQL translation: LLM-powered processing only
"""

import json
import logging
import re
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from cachetools import TTLCache

from .openai_client import OpenAIClient

logger = logging.getLogger(__name__)


@dataclass
class QueryTranslationResult:
    """Result of natural language to YQL translation."""
    yql_query: str
    confidence: float
    reasoning: str
    original_input: str
    detected_entities: Dict[str, Any]
    suggestions: List[str]


@dataclass
class ErrorEnhancementResult:
    """Result of AI-enhanced error processing."""
    enhanced_explanation: str
    fix_suggestion: str
    example_correction: str
    learning_tip: str
    confidence: float


class AIService:
    """
    Unified AI service.

    Error enhancement is always rule-based.
    NL to YQL translation requires LLM for ai.plan and search autosearch.
    """

    def __init__(self, openai_client: Optional[OpenAIClient] = None):
        """
        Initialize AI service.

        Args:
            openai_client: Optional OpenAIClient instance for NL to YQL
        """
        self.openai_client = openai_client

        # Caches
        self.query_cache = TTLCache(maxsize=1000, ttl=3600)  # 1 hour
        self.error_cache = TTLCache(maxsize=500, ttl=1800)   # 30 minutes

        # Load error patterns
        self.error_patterns = self._load_error_patterns()

        logger.info("AIService initialized (error enhancement: rule-based, NL to YQL: LLM required)")

    def _load_error_patterns(self) -> List[Dict[str, Any]]:
        """Load error patterns from YAML file."""
        patterns_file = Path(__file__).parent.parent.parent / "data" / "error_patterns.yaml"

        try:
            with open(patterns_file, 'r') as f:
                data = yaml.safe_load(f)

            if not isinstance(data, dict) or 'patterns' not in data:
                raise ValueError("Invalid patterns file structure")

            patterns = data['patterns']
            if not isinstance(patterns, list):
                raise ValueError("Patterns must be a list")

            # Validate each pattern
            for pattern in patterns:
                required_keys = ['id', 'match', 'scope', 'classification', 'explanation', 'remediation_steps']
                for key in required_keys:
                    if key not in pattern:
                        raise ValueError(f"Pattern {pattern.get('id', 'unknown')} missing required key: {key}")

            logger.info(f"Loaded {len(patterns)} error patterns")
            return patterns

        except Exception as e:
            logger.error(f"Failed to load error patterns: {e}")
            raise RuntimeError(f"Cannot load error patterns: {e}")

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

    def enhance_error_message(self, error: Union[Exception, str], context: Dict[str, Any]) -> ErrorEnhancementResult:
        """
        Enhance error message using rule-based processing (always).

        Args:
            error: Error exception or string
            context: Operation context

        Returns:
            Enhanced error result
        """
        return self._rule_enhance_error(error, context)



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

    def _rule_enhance_error(self, error: Union[Exception, str], context: Dict[str, Any]) -> ErrorEnhancementResult:
        """Rule-based error enhancement."""
        error_str = str(error).lower()

        # Find matching pattern
        for pattern in self.error_patterns:
            match_type, match_value = pattern['match'].split('|', 1)

            if match_type == 'regex':
                if re.search(match_value, error_str, re.IGNORECASE):
                    return self._build_error_result_from_pattern(pattern, error, context)
            elif match_type == 'exact':
                if match_value.lower() in error_str:
                    return self._build_error_result_from_pattern(pattern, error, context)

        # Default fallback
        return ErrorEnhancementResult(
            enhanced_explanation=f"Operation failed: {str(error)}",
            fix_suggestion="Please check your input parameters and try again",
            example_correction="",
            learning_tip="Review the error message for specific details",
            confidence=0.5
        )

    def _build_error_result_from_pattern(self, pattern: Dict[str, Any], error: Union[Exception, str], context: Dict[str, Any]) -> ErrorEnhancementResult:
        """Build error result from pattern."""
        explanation = pattern['explanation']
        remediation = pattern['remediation_steps'][0] if pattern['remediation_steps'] else "Check documentation"

        # Generate example correction if possible
        example_correction = ""
        if 'query' in context and pattern['scope'] == 'queries':
            example_correction = self._generate_example_correction(context['query'], pattern['id'])

        return ErrorEnhancementResult(
            enhanced_explanation=explanation,
            fix_suggestion=remediation,
            example_correction=example_correction,
            learning_tip=f"Learn more about {pattern['scope']} in YouTrack documentation",
            confidence=0.8
        )

    def _generate_example_correction(self, original_query: str, pattern_id: str) -> str:
        """Generate example correction based on pattern."""
        if pattern_id == 'syntax_error':
            return original_query.replace('=', ':').replace('"', '{').replace('"', '}')
        elif pattern_id == 'field_unknown':
            corrected = re.sub(r'\bassignee\b', 'assignee', original_query, flags=re.IGNORECASE)
            corrected = re.sub(r'\bstatus\b', 'state', corrected, flags=re.IGNORECASE)
            return corrected
        elif pattern_id == 'date_invalid':
            return re.sub(r'\d{1,2}/\d{1,2}/\d{4}', '2025-01-18', original_query)
        return original_query

    def _llm_enhance_error(self, error: Union[Exception, str], context: Dict[str, Any]) -> ErrorEnhancementResult:
        """LLM-powered error enhancement."""
        if not self.openai_client:
            raise RuntimeError("OpenAI client required for LLM mode")

        cache_key = f"llm_error:{hash(str(error))}{hash(str(context))}"
        if cache_key in self.error_cache:
            return self.error_cache[cache_key]

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
                self.error_cache[cache_key] = result
                return result

            raise RuntimeError("LLM enhancement failed")

        except Exception as e:
            logger.error(f"LLM enhancement error: {e}")
            raise RuntimeError("LLM enhancement unavailable")