# AI module package

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class QueryTranslationResult:
    """Result of natural language to YQL translation."""
    yql_query: str
    confidence: float
    reasoning: str
    original_input: str
    detected_entities: Dict[str, Any]
    suggestions: List[str]