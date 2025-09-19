# AI module package

from dataclasses import dataclass
from typing import Any, Dict, List

from .template_loader import PromptTemplateLoader, get_template_loader
from .openai_client import OutputMode
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
    "PromptTemplateLoader",
    "get_template_loader",
    "OutputMode",
    "StructuredOutputError",
    "ProviderError",
    "YQLTranslationResponse",
    "ErrorEnhancementResponse",
    "IntentAnalysisResponse",
    "IntentPlanStep"
]