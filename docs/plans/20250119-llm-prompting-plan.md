# LLM Prompting Enhancement Plan with Structured Output Support

**Version**: 2.0
**Date**: 2025-01-19
**Status**: SUPERSEDED (See: 20250120-llm-prompting-refinement-plan.md)

## Executive Summary

This plan enhances the LLM prompting system for YouTrack MCP by replacing the current basic implementation with a production-ready structured output system. The new system uses OpenAI's response_format API with three selectable modes (json_schema, json_object, inline) to enforce JSON schemas, with configurable retries and exponential backoff.

## Current State Analysis

**Note**: This plan implements a complete replacement of the existing prompting system without backward compatibility. All existing integrations will need to adapt to the new structured JSON response format.

### Identified Issues

1. **No Schema Enforcement**: Current system doesn't use OpenAI's response_format capabilities
2. **No Retry Logic**: Failed responses aren't automatically retried with repair hints
3. **Inconsistent Validation**: No Pydantic-based validation of LLM outputs
4. **Limited Error Recovery**: No exponential backoff or structured error types

## Proposed Enhancements

### 1. Replace Existing Implementation with Structured Output System

#### Core Architecture Changes

**Update existing files in `youtrack_mcp/ai/`:**

```python
# youtrack_mcp/ai/errors.py (NEW FILE)
class StructuredOutputError(Exception):
    """Structured output validation or generation failure."""
    
    def __init__(
        self,
        fields: dict | list,      # Failed fields/constraints
        message: str,              # Human-readable error
        last_raw: str | None,      # Last raw response
        attempt_count: int,        # Number of attempts made
        request_id: str | None     # OpenAI request ID
    ):
        self.fields = fields
        self.message = message
        self.last_raw = last_raw
        self.attempt_count = attempt_count
        self.request_id = request_id

class ProviderError(Exception):
    """Provider API error."""
    
    def __init__(
        self,
        message: str,
        request_id: str | None,
        status_code: int | None
    ):
        self.message = message
        self.request_id = request_id
        self.status_code = status_code
```

#### Three Output Modes

**Update `youtrack_mcp/ai/openai_client.py` to support three modes:**

```python
from enum import Enum
from typing import TypeVar, Type
from pydantic import BaseModel
import asyncio
from openai import OpenAI

class OutputMode(str, Enum):
    JSON_SCHEMA = "json_schema"  # Strict server-side enforcement - JSON always required
    JSON_OBJECT = "json_object"  # Provider JSON + local validation - JSON always required
    INLINE = "inline"            # Schema in prompt - JSON always required

T = TypeVar('T', bound=BaseModel)

class OpenAIClient:
    """Enhanced OpenAI client with structured output support."""

    def __init__(
        self,
        api_key: str,
        mode: OutputMode = OutputMode.JSON_SCHEMA,
        max_retries: int = 3,
        initial_backoff: float = 1.0,
        backoff_multiplier: float = 2.0
    ):
        self.client = OpenAI(api_key=api_key)
        self.mode = mode
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff
        self.backoff_multiplier = backoff_multiplier

    async def complete_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system: str | None = None,
        max_tokens: int = 800
    ) -> T:
        """Generate structured output with mode-based enforcement.

        JSON is always required and validated, enforcement method varies by OutputMode:
        - JSON_SCHEMA: OpenAI enforces both JSON format and schema server-side
        - JSON_OBJECT: OpenAI enforces JSON format, we validate schema locally
        - INLINE: We extract JSON and validate schema locally, retry if either fails

        Note: max_tokens applies to the response/completion only, not the input.
        The total token usage = input_tokens (prompt + system + schema) + response_tokens (max_tokens).
        With structured outputs, prompts can be longer due to embedded schemas.
        """

        if self.mode == OutputMode.JSON_SCHEMA:
            return await self._json_schema_mode(prompt, response_model, system, max_tokens)
        elif self.mode == OutputMode.JSON_OBJECT:
            return await self._json_object_mode(prompt, response_model, system, max_tokens)
        else:  # INLINE
            return await self._inline_mode(prompt, response_model, system, max_tokens)
    
    async def _json_schema_mode(self, prompt: str, model: Type[T], system: str, max_tokens: int) -> T:
        """Use OpenAI's strict json_schema enforcement."""
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system or "Output only the JSON object."},
                {"role": "user", "content": prompt}
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": model.__name__,
                    "strict": True,
                    "schema": model.model_json_schema()
                }
            },
            max_tokens=max_tokens
        )

        # Log warning if approaching or exceeding token limits
        if hasattr(response, 'usage'):
            if response.usage.total_tokens > 4000:
                logger.warning(f"High token usage: {response.usage.total_tokens} total tokens")
            if response.usage.completion_tokens >= max_tokens * 0.95:
                logger.warning(f"Response near max_tokens limit: {response.usage.completion_tokens}/{max_tokens}")

        return model.model_validate_json(response.choices[0].message.content)

    async def _json_object_mode(self, prompt: str, model: Type[T], system: str, max_tokens: int) -> T:
        """Use json_object with local validation and retries."""
        for attempt in range(self.max_retries):
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system or f"Return JSON matching: {model.model_json_schema()}"},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                max_tokens=max_tokens
            )
            
            try:
                return model.model_validate_json(response.choices[0].message.content)
            except ValidationError as e:
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.initial_backoff * (self.backoff_multiplier ** attempt))
                    prompt += f"

Fix these validation errors: {e.errors()}"
                else:
                    raise StructuredOutputError(
                        fields=e.errors(),
                        message="Validation failed after retries",
                        last_raw=response.choices[0].message.content,
                        attempt_count=attempt + 1,
                        request_id=response.id
                    )
    
    async def _inline_mode(self, prompt: str, model: Type[T], system: str, max_tokens: int) -> T:
        """Include schema in prompt with validation and retries."""
        schema_str = self._compact_schema(model)
        enhanced_prompt = f"{prompt}

Output JSON matching: {schema_str}"

        for attempt in range(self.max_retries):
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system or "Output valid JSON only."},
                    {"role": "user", "content": enhanced_prompt}
                ],
                max_tokens=max_tokens
            )
            
            content = response.choices[0].message.content
            try:
                # Extract JSON from response (required)
                import json
                json_content = None

                # Try to extract from markdown code block
                if "```json" in content:
                    json_content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    json_content = content.split("```")[1].split("```")[0].strip()
                else:
                    # Try to find JSON object in text
                    json_start = content.find('{')
                    json_end = content.rfind('}')
                    if json_start != -1 and json_end != -1:
                        json_content = content[json_start:json_end + 1]

                if not json_content:
                    raise json.JSONDecodeError("No JSON found in response", content, 0)

                data = json.loads(json_content)
                return model.model_validate(data)
            except (json.JSONDecodeError, ValidationError) as e:
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.initial_backoff * (self.backoff_multiplier ** attempt))
                    enhanced_prompt += f"

IMPORTANT: You MUST return valid JSON. Fix: {str(e)}"
                else:
                    raise StructuredOutputError(
                        fields=str(e),
                        message="Failed to extract or validate JSON after retries",
                        last_raw=content,
                        attempt_count=attempt + 1,
                        request_id=response.id
                    )
```

#### Pydantic Models for Responses

**File**: `youtrack_mcp/ai/models.py` (NEW FILE)

```python
from pydantic import BaseModel, Field
from typing import List, Dict, Optional

class YQLTranslationResponse(BaseModel):
    """YQL translation response model."""
    yql_query: str = Field(..., description="Generated YQL query")
    confidence: float = Field(..., ge=0, le=1, description="Confidence score")
    reasoning: str = Field(..., description="Translation reasoning")
    detected_entities: Dict[str, List[str]] = Field(default_factory=dict)
    alternative_queries: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

class ErrorEnhancementResponse(BaseModel):
    """Error enhancement response model."""
    error_category: str = Field(..., pattern="^(authentication|syntax|not_found|permission|validation|server)$")
    enhanced_explanation: str
    root_cause: str
    immediate_fix: str
    example_correction: Optional[Dict[str, str]] = None
    prevention_tips: List[str] = Field(default_factory=list)
    confidence: float = Field(..., ge=0, le=1)
    requires_admin: bool = False
    estimated_fix_time: str = Field(..., pattern="^(immediate|minutes|hours|needs_investigation)$")

class IntentAnalysisResponse(BaseModel):
    """Intent analysis response model."""
    intent: str
    intent_category: str = Field(..., pattern="^(create|read|update|delete|search|bulk|analysis)$")
    confidence: float = Field(..., ge=0, le=1)
    detected_entities: Dict[str, List[str]] = Field(default_factory=dict)
    requires_confirmation: bool = True
    plan: List[Dict] = Field(..., min_items=1)
    warnings: List[str] = Field(default_factory=list)
    estimated_complexity: str = Field(..., pattern="^(low|medium|high)$")


```

### 2. Update AIService to Use Structured Output

**File**: `youtrack_mcp/ai/service.py` (UPDATE EXISTING)

```python
from typing import Dict, Any, Optional
from .openai_client import OpenAIClient, OutputMode
from .models import YQLTranslationResponse, ErrorEnhancementResponse, IntentAnalysisResponse
from .errors import StructuredOutputError, ProviderError

class AIService:
    """Enhanced AI service with structured output support."""
    
    def __init__(self, openai_client: Optional[OpenAIClient] = None):
        """Initialize with optional OpenAI client."""
        self.openai_client = openai_client
    
    async def translate_nl_to_yql(
        self, 
        natural_query: str, 
        project_context: Optional[str] = None
    ) -> YQLTranslationResponse:
        """Translate natural language to YQL with structured output."""
        if not self.openai_client:
            raise RuntimeError("OpenAI client required for translation")
        
        prompt = f"Convert to YQL: '{natural_query}'"
        if project_context:
            prompt += f"\nProject context: {project_context}"
        
        return await self.openai_client.complete_structured(
            prompt=prompt,
            response_model=YQLTranslationResponse,
            system="You are a YouTrack Query Language expert. Convert natural language to YQL."
        )
    
    async def enhance_error_message(
        self,
        error: str,
        context: Dict[str, Any]
    ) -> ErrorEnhancementResponse:
        """Enhance error messages with structured output."""
        if not self.openai_client:
            raise RuntimeError("OpenAI client required for error enhancement")
        
        prompt = f"Error: {error}\nContext: {context}"
        
        return await self.openai_client.complete_structured(
            prompt=prompt,
            response_model=ErrorEnhancementResponse,
            system="You are a YouTrack API expert. Analyze and enhance error messages."
        )
    
    async def analyze_intent(
        self,
        intent: str,
        context: Dict[str, Any]
    ) -> IntentAnalysisResponse:
        """Analyze user intent with structured output."""
        if not self.openai_client:
            raise RuntimeError("OpenAI client required for intent analysis")
        
        prompt = f"Analyze intent: {intent}\nContext: {context}"
        
        return await self.openai_client.complete_structured(
            prompt=prompt,
            response_model=IntentAnalysisResponse,
            system="You are a YouTrack automation expert. Analyze intent and create execution plans."
        )
```



### 2. Implementation Enhancements

#### 2.1 Response Validation and Retry Logic

**File**: `youtrack_mcp/ai/response_validator.py`

```python
"""
Response validation and retry logic for LLM outputs.
"""

import json
import logging
from typing import Any, Dict, Optional, Callable
from jsonschema import validate, ValidationError
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ValidationConfig:
    """Configuration for response validation."""
    max_retries: int = 3
    require_confidence: bool = True
    min_confidence: float = 0.5
    schema: Optional[Dict[str, Any]] = None
    # Note: JSON requirement is controlled by OutputMode, not this config


class ResponseValidator:
    """Validates and retries LLM responses."""
    
    # JSON Schema for YQL Translation Response
    YQL_RESPONSE_SCHEMA = {
        "type": "object",
        "required": ["yql_query", "confidence", "reasoning"],
        "properties": {
            "yql_query": {"type": "string", "minLength": 1},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "reasoning": {"type": "string"},
            "detected_entities": {"type": "object"},
            "alternative_queries": {"type": "array", "items": {"type": "string"}},
            "warnings": {"type": "array", "items": {"type": "string"}}
        }
    }
    
    # JSON Schema for Error Enhancement Response
    ERROR_RESPONSE_SCHEMA = {
        "type": "object",
        "required": ["error_category", "enhanced_explanation", "immediate_fix", "confidence"],
        "properties": {
            "error_category": {
                "type": "string",
                "enum": ["authentication", "syntax", "not_found", "permission", "validation", "server"]
            },
            "enhanced_explanation": {"type": "string"},
            "root_cause": {"type": "string"},
            "immediate_fix": {"type": "string"},
            "example_correction": {
                "type": "object",
                "properties": {
                    "wrong": {"type": "string"},
                    "correct": {"type": "string"},
                    "explanation": {"type": "string"}
                }
            },
            "prevention_tips": {"type": "array", "items": {"type": "string"}},
            "related_documentation": {"type": "array", "items": {"type": "string"}},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "requires_admin": {"type": "boolean"},
            "estimated_fix_time": {
                "type": "string",
                "enum": ["immediate", "minutes", "hours", "needs_investigation"]
            }
        }
    }
    
    # JSON Schema for Intent Analysis Response
    INTENT_RESPONSE_SCHEMA = {
        "type": "object",
        "required": ["intent", "intent_category", "confidence", "plan"],
        "properties": {
            "intent": {"type": "string"},
            "intent_category": {
                "type": "string",
                "enum": ["create", "read", "update", "delete", "search", "bulk", "analysis"]
            },
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "detected_entities": {"type": "object"},
            "requires_confirmation": {"type": "boolean"},
            "validation_required": {"type": "object"},
            "plan": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["step", "tool", "description", "parameters"],
                    "properties": {
                        "step": {"type": "integer"},
                        "tool": {"type": "string"},
                        "description": {"type": "string"},
                        "parameters": {"type": "object"},
                        "expected_result": {"type": "string"},
                        "error_handling": {"type": "string"}
                    }
                }
            },
            "alternative_interpretations": {"type": "array", "items": {"type": "string"}},
            "warnings": {"type": "array", "items": {"type": "string"}},
            "estimated_complexity": {
                "type": "string",
                "enum": ["low", "medium", "high"]
            },
            "estimated_api_calls": {"type": "integer"},
            "rollback_plan": {"type": "object"}
        }
    }
    
    @staticmethod
    def extract_json(response: str) -> Optional[Dict[str, Any]]:
        """
        Extract JSON from LLM response.
        
        Handles responses that may include markdown code blocks or extra text.
        """
        # Try direct parsing first
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass
        
        # Try to extract from markdown code block
        import re
        json_pattern = r'```json\s*(.*?)\s*```'
        match = re.search(json_pattern, response, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Try to find JSON object in text
        json_start = response.find('{')
        json_end = response.rfind('}')
        if json_start != -1 and json_end != -1:
            try:
                return json.loads(response[json_start:json_end + 1])
            except json.JSONDecodeError:
                pass
        
        return None
    
    @staticmethod
    def validate_response(
        response: str,
        config: ValidationConfig,
        output_mode: OutputMode
    ) -> tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Validate LLM response against configuration.

        Returns:
            Tuple of (is_valid, parsed_response, error_message)
        """
        # JSON is always required regardless of output mode
        parsed = ResponseValidator.extract_json(response)
        if parsed is None:
            return False, None, "Failed to extract valid JSON from response"
        
        # Validate against schema if provided
        if config.schema:
            try:
                validate(instance=parsed, schema=config.schema)
            except ValidationError as e:
                return False, parsed, f"Schema validation failed: {e.message}"
        
        # Check confidence if required
        if config.require_confidence:
            confidence = parsed.get("confidence")
            if confidence is None:
                return False, parsed, "Missing required 'confidence' field"
            if confidence < config.min_confidence:
                return False, parsed, f"Confidence {confidence} below minimum {config.min_confidence}"
        
        return True, parsed, None
    
    @staticmethod
    async def retry_with_validation(
        llm_func: Callable,
        prompt: str,
        config: ValidationConfig,
        output_mode: OutputMode,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Retry LLM call with validation.

        Args:
            llm_func: LLM completion function
            prompt: User prompt
            config: Validation configuration
            output_mode: Output mode controlling JSON requirement
            system_prompt: Optional system prompt
            **kwargs: Additional arguments for LLM function

        Returns:
            Validated response dictionary

        Raises:
            RuntimeError: If all retries fail
        """
        last_error = None

        for attempt in range(config.max_retries):
            try:
                # Add retry context to prompt if not first attempt
                if attempt > 0:
                    if output_mode in (OutputMode.JSON_SCHEMA, OutputMode.JSON_OBJECT):
                        retry_prompt = f"{prompt}\n\nPrevious attempt failed: {last_error}\nPlease ensure response is valid JSON matching the required schema."
                    else:
                        retry_prompt = f"{prompt}\n\nPrevious attempt failed: {last_error}\nPlease correct the issue and try again."
                else:
                    retry_prompt = prompt

                # Call LLM
                response = await llm_func(
                    prompt=retry_prompt,
                    system=system_prompt,
                    **kwargs
                )

                # Validate response
                is_valid, parsed, error_msg = ResponseValidator.validate_response(
                    response,
                    config,
                    output_mode
                )
                
                if is_valid:
                    logger.info(f"Response validated successfully on attempt {attempt + 1}")
                    return parsed
                
                last_error = error_msg
                logger.warning(f"Validation failed on attempt {attempt + 1}: {error_msg}")
                
            except Exception as e:
                last_error = str(e)
                logger.error(f"LLM call failed on attempt {attempt + 1}: {e}")
        
        raise RuntimeError(
            f"Failed to get valid response after {config.max_retries} attempts. "
            f"Last error: {last_error}"
        )
```

#### 2.2 Configuration Management

**File**: `youtrack_mcp/config.py` (additions)

```python
class LLMConfig(BaseSettings):
    """LLM-specific configuration for enhanced prompting."""

    model_config = ConfigDict(
        env_prefix="LLM_",
        case_sensitive=False,
    )

    # Output mode configuration (tristate)
    output_mode: OutputMode = Field(
        OutputMode.JSON_SCHEMA,
        description="Output mode: json_schema (strict), json_object (validated), inline (flexible)"
    )

    # Retry configuration
    max_retries: int = Field(3, ge=0, le=10, description="Maximum retry attempts for LLM calls")
    min_confidence: float = Field(0.6, ge=0.0, le=1.0, description="Minimum confidence threshold")

    # Token limits nested by operation type (for response/completion only, not input)
    max_tokens: dict = Field(
        default={
            "yql": 500,      # Response tokens for YQL translation
            "error": 800,    # Response tokens for error enhancement
            "intent": 1500   # Response tokens for intent analysis
        },
        description="Max tokens for LLM response per operation type (does not include input tokens)"
    )

    # Cache settings
    cache_ttl: int = Field(3600, ge=60, description="Cache TTL in seconds (default 1 hour)")

    # Validation settings (only apply to inline mode)
    extract_json_from_markdown: bool = Field(True, description="Try to extract JSON from markdown blocks")

# Add to Settings class
class Settings(BaseSettings):
    # ... existing nested configurations ...
    llm: LLMConfig = Field(default_factory=LLMConfig)
```

### 3. Testing Strategy

#### 3.1 Prompt Testing Framework

**File**: `tests/prompts/test_prompt_responses.py`

```python
"""
Test framework for validating prompt responses.
"""

import pytest
import json
from youtrack_mcp.ai.response_validator import ResponseValidator, ValidationConfig

class TestPromptResponses:
    """Test prompt response validation."""
    
    @pytest.mark.parametrize("query,expected_yql", [
        ("my open issues in demo", "project: demo assignee: me state: Open"),
        ("critical bugs last week", "type: Bug priority: Critical created: {minus 7d} .. *"),
        ("unassigned tasks", "assignee: Unassigned type: Task"),
    ])
    def test_yql_translation_examples(self, query, expected_yql):
        """Test YQL translation with known examples."""
        # This would test against actual LLM or mock responses
        pass
    
    @pytest.mark.parametrize("response,should_validate", [
        ('{"yql_query": "test", "confidence": 0.8, "reasoning": "test"}', True),
        ('{"yql_query": "", "confidence": 0.8, "reasoning": "test"}', False),
        ('{"confidence": 0.8, "reasoning": "test"}', False),
        ('not json at all', False),
    ])
    def test_response_validation(self, response, should_validate):
        """Test response validation logic."""
        config = ValidationConfig(
            schema=ResponseValidator.YQL_RESPONSE_SCHEMA
        )
        is_valid, _, _ = ResponseValidator.validate_response(response, config)
        assert is_valid == should_validate
```

### 4. Implementation Checklist

#### Phase 1: Core Infrastructure

- [ ] Create `youtrack_mcp/ai/errors.py` with StructuredOutputError and ProviderError
- [ ] Create `youtrack_mcp/ai/models.py` with Pydantic response models
- [ ] Update `youtrack_mcp/ai/openai_client.py` to support three output modes

#### Phase 2: Update Existing Services

- [ ] Update `youtrack_mcp/ai/service.py` to use structured outputs
  - Replace string-based responses with Pydantic models
  - Use complete_structured method from OpenAIClient
  - Handle StructuredOutputError appropriately
  
- [ ] Remove old validation logic from `youtrack_mcp/ai/`
  - Delete response_validator.py if it exists
  - Remove template_loader.py as schemas define structure

#### Phase 3: Testing

- [ ] Create unit tests for each output mode
  - Test json_schema mode with strict validation
  - Test json_object mode with retries
  - Test inline mode with schema in prompt
  
- [ ] Integration tests with mock OpenAI responses
  - Test validation failures and retries
  - Test exponential backoff behavior
  - Test all three response models

#### Phase 4: Configuration

- [ ] Add LLMConfig to `youtrack_mcp/config.py`
  - output_mode setting (json_schema|json_object|inline)
  - max_retries, initial_backoff, backoff_multiplier
  - Model and temperature settings
  
- [ ] Update `.env.example` with new variables
  - Document LLM_OUTPUT_MODE options
  - Provide recommended retry settings

#### Phase 5: Documentation

- [ ] Update API documentation
  - Document new structured response formats
  - Explain mode selection criteria
  - Include migration guide from old system

### 5. Success Metrics

1. **Accuracy Improvement**
   - Target: 90%+ accuracy on common queries
   - Measure: Test suite pass rate

2. **Confidence Scoring**
   - Target: 85%+ of responses with confidence > 0.7
   - Measure: Average confidence scores

3. **Retry Success Rate**
   - Target: 95%+ success within 3 retries
   - Measure: Retry statistics

4. **Response Time**
   - Target: < 2 seconds average
   - Measure: API response times

5. **Error Reduction**
   - Target: 50% reduction in malformed responses
   - Measure: Validation failure rate

### 6. Risk Mitigation

1. **Increased Token Usage**
   - Risk: Enhanced prompts use more tokens
   - Mitigation: Implement token counting and limits
   - Fallback: Use condensed prompts for simple queries

2. **Breaking Changes**
   - Risk: Existing integrations will need updates
   - Mitigation: Clear migration documentation
   - Approach: Clean replacement of all prompts and validation

3. **LLM Variability**
   - Risk: Different LLMs respond differently
   - Mitigation: Test with multiple models
   - Fallback: Model-specific prompt variants

### 7. Enhanced Prompts

#### 7.1 YQL Translation Prompts

**System Prompt:**
```
You are an expert YouTrack Query Language (YQL) assistant. Your role is to translate natural language requests into precise YQL queries.

Key capabilities:
- Deep understanding of YQL syntax, operators, and field references
- Knowledge of all YouTrack entities (issues, projects, users, custom fields)
- Ability to handle complex date ranges and relative time expressions
- Understanding of field type-specific query patterns

Always provide accurate, optimized queries that follow YouTrack best practices.
```

**User Prompt Template:**
```
Task: Convert the following natural language query to YQL.

Natural Query: {natural_query}
{%- if project_context %}
Project Context: {project_context}
{%- endif %}
{%- if available_custom_fields %}
Available Custom Fields: {available_custom_fields}
{%- endif %}

Requirements:
- Generate the most accurate YQL query for the request
- Use proper syntax for multi-word values (curly braces)
- Apply correct date formats and operators
- Consider the project context if provided
```

#### 7.2 Error Enhancement Prompts

**System Prompt:**
```
You are an expert YouTrack API troubleshooting assistant specializing in error diagnosis and resolution.

Your expertise includes:
- Deep knowledge of YouTrack API error patterns and codes
- Understanding of common integration pitfalls
- Ability to provide actionable fixes with examples
- Educational approach to help users learn from mistakes

Focus on practical solutions and prevention strategies.
```

**User Prompt Template:**
```
Analyze and enhance this YouTrack error for better understanding:

Error: {error_message}
Context:
- Operation: {operation}
- Endpoint: {endpoint}
{%- if request_data %}
- Request Data: {request_data}
{%- endif %}
{%- if http_status %}
- HTTP Status: {http_status}
{%- endif %}

Provide:
1. Root cause analysis
2. Immediate fix with example
3. Prevention strategy
4. Related documentation references
```

#### 7.3 Intent Analysis Prompts

**System Prompt:**
```
You are an expert YouTrack automation assistant that analyzes user intent and creates detailed execution plans.

Core competencies:
- Understanding complex multi-step operations
- Risk assessment and validation requirements
- Knowledge of YouTrack permissions and constraints
- Ability to decompose tasks into atomic operations

Always provide safe, idempotent plans with proper error handling.
```

**User Prompt Template:**
```
Analyze the user's intent and create an execution plan:

Intent: {user_intent}
Context:
{%- if current_project %}
- Project: {current_project}
{%- endif %}
{%- if user_permissions %}
- User Permissions: {user_permissions}
{%- endif %}
{%- if available_resources %}
- Available Resources: {available_resources}
{%- endif %}

Generate a detailed plan including:
1. Step-by-step operations
2. Required validations
3. Potential risks and mitigations
4. Rollback strategy if needed
```

### 8. Appendices

#### A. Example Enhanced Responses

##### YQL Translation Example
```json
{
  "yql_query": "project: DEMO assignee: me state: Open created: {minus 7d} .. *",
  "confidence": 0.95,
  "reasoning": "User wants their open issues in DEMO project from last week. Used 'me' for personal assignment, Open state filter, and relative date range.",
  "detected_entities": {
    "projects": ["DEMO"],
    "users": ["me"],
    "states": ["Open"],
    "dates": ["last 7 days"],
    "custom_fields": []
  },
  "alternative_queries": [
    "project: DEMO for: me #Unresolved created: {minus 7d} .. *"
  ],
  "warnings": []
}
```

##### Error Enhancement Example
```json
{
  "error_category": "syntax",
  "enhanced_explanation": "The YQL query has invalid syntax. Multi-word state values must be enclosed in curly braces.",
  "root_cause": "Missing curly braces around 'In Progress'",
  "immediate_fix": "Change 'state: In Progress' to 'state: {In Progress}'",
  "example_correction": {
    "wrong": "state: In Progress",
    "correct": "state: {In Progress}",
    "explanation": "YouTrack requires curly braces around values containing spaces"
  },
  "prevention_tips": [
    "Always use {} for multi-word values",
    "Test queries in YouTrack UI first",
    "Use the query builder for complex filters"
  ],
  "related_documentation": [
    "YQL Syntax Guide: Special Characters",
    "API Query Documentation"
  ],
  "confidence": 0.98,
  "requires_admin": false,
  "estimated_fix_time": "immediate"
}
```

### 8. References

1. YouTrack Query Language Documentation
2. OpenAI JSON Mode Best Practices
3. JSON Schema Validation Standards
4. Prompt Engineering Guidelines