# AI module package

from dataclasses import dataclass
from typing import Any, Dict, List

from .template_manager import TemplateManager
from .llm_client import LLMClient
from .errors import StructuredOutputError, ProviderError
from .models import (
    YQLTranslationResponse,
    ErrorEnhancementResponse,
    IntentAnalysisResponse,
    IntentPlanStep
)


@dataclass
class QueryTranslationResult:
    """Result of natural language to YQL translation."""
    yql_query: str
    confidence: float
    reasoning: str
    original_input: str
    detected_entities: Dict[str, Any]
    suggestions: List[str]


__all__ = [
    "QueryTranslationResult",
    "TemplateManager",
    "LLMClient",
    "StructuredOutputError",
    "ProviderError",
    "YQLTranslationResponse",
    "ErrorEnhancementResponse",
    "IntentAnalysisResponse",
    "IntentPlanStep"
]