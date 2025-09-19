"""
Pydantic models for structured LLM responses.

Defines response schemas for YQL translation, error enhancement, and intent analysis.
"""

from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field, field_validator


class YQLTranslationResponse(BaseModel):
    """YQL translation response model."""

    yql_query: str = Field(..., description="Generated YQL query", min_length=1)
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    reasoning: str = Field(..., description="Translation reasoning")
    detected_entities: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Detected entities (projects, users, states, etc.)"
    )
    alternative_queries: List[str] = Field(
        default_factory=list,
        description="Alternative YQL queries that might match the intent"
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Warnings about query interpretation or potential issues"
    )

    @field_validator('yql_query')
    @classmethod
    def validate_yql_query(cls, v: str) -> str:
        """Validate YQL query has basic structure."""
        v = v.strip()
        if not v:
            raise ValueError("YQL query cannot be empty")
        # Basic check for YQL structure (should contain ':' or be a simple search)
        if ':' not in v and not v.startswith('#') and not v.startswith('{'):
            # Allow simple text searches without ':' operator
            pass
        return v


class ErrorEnhancementResponse(BaseModel):
    """Error enhancement response model."""

    error_category: Literal[
        "authentication", "syntax", "not_found",
        "permission", "validation", "server"
    ] = Field(..., description="Error category")
    enhanced_explanation: str = Field(..., description="Clear explanation of the error")
    root_cause: str = Field(..., description="Root cause analysis")
    immediate_fix: str = Field(..., description="Immediate fix suggestion")
    example_correction: Optional[Dict[str, str]] = Field(
        None,
        description="Example showing wrong and correct usage"
    )
    prevention_tips: List[str] = Field(
        default_factory=list,
        description="Tips to prevent this error in the future"
    )
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    requires_admin: bool = Field(
        False,
        description="Whether admin privileges are needed for the fix"
    )
    estimated_fix_time: Literal[
        "immediate", "minutes", "hours", "needs_investigation"
    ] = Field(..., description="Estimated time to fix")

    @field_validator('example_correction')
    @classmethod
    def validate_example(cls, v: Optional[Dict[str, str]]) -> Optional[Dict[str, str]]:
        """Validate example correction structure."""
        if v is not None:
            required_keys = {"wrong", "correct"}
            if not required_keys.issubset(v.keys()):
                raise ValueError(f"example_correction must contain keys: {required_keys}")
        return v


class IntentPlanStep(BaseModel):
    """Single step in an intent execution plan."""

    step: int = Field(..., ge=1, description="Step number")
    tool: str = Field(..., description="Tool to use")
    description: str = Field(..., description="Step description")
    parameters: Dict = Field(..., description="Tool parameters")
    expected_result: str = Field(..., description="Expected result")
    error_handling: str = Field(
        "stop",
        description="Error handling strategy (stop, skip, retry)"
    )


class IntentAnalysisResponse(BaseModel):
    """Intent analysis response model."""

    intent: str = Field(..., description="Clarified intent")
    intent_category: Literal[
        "create", "read", "update", "delete",
        "search", "bulk", "analysis"
    ] = Field(..., description="Intent category")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    detected_entities: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Detected entities in the intent"
    )
    requires_confirmation: bool = Field(
        True,
        description="Whether user confirmation is needed"
    )
    plan: List[IntentPlanStep] = Field(
        ...,
        min_length=1,
        description="Execution plan steps"
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Warnings about the operation"
    )
    estimated_complexity: Literal["low", "medium", "high"] = Field(
        ...,
        description="Estimated operation complexity"
    )
    alternative_interpretations: List[str] = Field(
        default_factory=list,
        description="Alternative ways to interpret the intent"
    )
    rollback_plan: Optional[Dict] = Field(
        None,
        description="Rollback plan if operation fails"
    )

    @field_validator('plan')
    @classmethod
    def validate_plan(cls, v: List[IntentPlanStep]) -> List[IntentPlanStep]:
        """Validate plan has sequential steps."""
        if not v:
            raise ValueError("Plan must contain at least one step")

        # Check step numbers are sequential
        step_numbers = [step.step for step in v]
        expected = list(range(1, len(v) + 1))
        if step_numbers != expected:
            raise ValueError(f"Plan steps must be sequential from 1 to {len(v)}")

        return v


# Re-export for backward compatibility
__all__ = [
    'YQLTranslationResponse',
    'ErrorEnhancementResponse',
    'IntentAnalysisResponse',
    'IntentPlanStep'
]