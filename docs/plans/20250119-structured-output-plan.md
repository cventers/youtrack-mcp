# Structured Output Library Implementation Plan

**Version**: 2.0  
**Date**: 2025-01-19  
**Status**: DRAFT

## Executive Summary

Build a production-ready Python library for enforcing structured JSON responses from LLMs using the OpenAI SDK. The library supports three selectable modes (`json_schema`, `json_object`, `inline`) via a single configuration knob, with configurable retries and exponential backoff.

## Requirements

- **Stack**: Python 3.11+, OpenAI SDK, Pydantic v2, pytest
- **Network**: OpenAI SDK only (no Groq/Fireworks)
- **Interface**: Clean, production-ready with solid logging
- **Retries**: Configurable with exponential backoff
- **Validation**: Pydantic model-based

## Architecture

### Core Components

```
youtrack_mcp/ai/structured/
├── __init__.py           # Public API exports
├── client.py             # StructuredOutputClient main class
├── modes.py              # Mode implementations (json_schema, json_object, inline)
├── errors.py             # Error types (StructuredOutputError, ProviderError)
├── retry.py              # Retry logic with exponential backoff
├── schema_utils.py       # Pydantic to JSON Schema conversion
└── prompts.py            # Mode-specific prompt generation
```

### Mode Implementations

#### 1. `json_schema` Mode (First-class Enforcement)

```python
class JsonSchemaMode:
    """OpenAI response_format with json_schema and strict=true."""
    
    def prepare_request(self, model: type[BaseModel]) -> dict:
        return {
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": model.__name__,
                    "strict": True,
                    "schema": model.model_json_schema()
                }
            }
        }
    
    def handle_response(self, response: dict, model: type[BaseModel]) -> BaseModel:
        # API enforces schema - just parse
        # Raise StructuredOutputError if API returns validation error
        pass
```

#### 2. `json_object` Mode (Provider JSON + Local Validation)

```python
class JsonObjectMode:
    """OpenAI json_object with local Pydantic validation + retries."""
    
    def prepare_request(self, model: type[BaseModel]) -> dict:
        return {
            "response_format": {"type": "json_object"}
        }
    
    def handle_response(self, response: dict, model: type[BaseModel]) -> BaseModel:
        # Parse JSON and validate with Pydantic
        # On failure: retry with repair instruction
        pass
```

#### 3. `inline` Mode (Schema in Prompt)

```python
class InlineMode:
    """Schema embedded in prompt with local validation + retries."""
    
    def prepare_prompt(self, model: type[BaseModel]) -> str:
        # Generate compact schema spec
        return f"Output JSON matching: {self.compact_schema(model)}"
    
    def handle_response(self, response: str, model: type[BaseModel]) -> BaseModel:
        # Try JSON parse, validate, retry with repair hints
        pass
```

### Error Types

```python
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

### Retry Strategy

```python
@dataclass
class RetryConfig:
    """Exponential backoff retry configuration."""
    max_retries: int = 3
    initial_backoff_seconds: float = 1.0
    backoff_multiplier: float = 2.0
    max_backoff_seconds: float = 60.0
    
class RetryHandler:
    """Handles retries with exponential backoff."""
    
    async def execute_with_retry(
        self,
        func: Callable,
        validation_func: Callable,
        repair_prompt_func: Callable
    ) -> Any:
        # Implement exponential backoff retry logic
        pass
```

### Main Client Interface

```python
from enum import Enum
from typing import TypeVar, Type
from pydantic import BaseModel

class OutputMode(str, Enum):
    JSON_SCHEMA = "json_schema"
    JSON_OBJECT = "json_object" 
    INLINE = "inline"

T = TypeVar('T', bound=BaseModel)

class StructuredOutputClient:
    """Client for structured LLM outputs with mode selection."""
    
    def __init__(
        self,
        api_key: str,
        mode: OutputMode = OutputMode.JSON_SCHEMA,
        retry_config: RetryConfig | None = None,
        model: str = "gpt-4o-mini",
        temperature: float = 0.3
    ):
        self.client = OpenAI(api_key=api_key)
        self.mode = mode
        self.retry_config = retry_config or RetryConfig()
        self.model = model
        self.temperature = temperature
    
    async def generate(
        self,
        prompt: str,
        response_model: Type[T],
        system_prompt: str | None = None
    ) -> T:
        """
        Generate structured output matching response_model.
        
        Args:
            prompt: User prompt
            response_model: Pydantic model class
            system_prompt: Optional system prompt (mode-aware defaults)
            
        Returns:
            Instance of response_model
            
        Raises:
            StructuredOutputError: Validation/generation failure
            ProviderError: API errors
        """
        # Dispatch to mode handler
        handler = self._get_mode_handler()
        return await handler.generate(prompt, response_model, system_prompt)
```

## Implementation Checklist

### Phase 1: Core Infrastructure

- [ ] Create `youtrack_mcp/ai/structured/` package structure
- [ ] Implement `errors.py` with StructuredOutputError and ProviderError
- [ ] Implement `retry.py` with RetryConfig and RetryHandler
- [ ] Implement `schema_utils.py` for Pydantic → JSON Schema conversion
  - Use `model.model_json_schema()` for full schema
  - Create compact schema generator for inline mode

### Phase 2: Mode Implementations

- [ ] Implement `modes.py` base class `OutputModeHandler`
  - Abstract methods: `prepare_request`, `handle_response`
  - Common validation and retry logic

- [ ] Implement `JsonSchemaMode` class
  - Use response_format with json_schema + strict=true
  - Parse response directly to Pydantic model
  - Handle API validation errors → StructuredOutputError

- [ ] Implement `JsonObjectMode` class  
  - Use response_format with json_object
  - Local Pydantic validation
  - Retry with repair instructions on failure

- [ ] Implement `InlineMode` class
  - Generate compact schema in prompt
  - Parse JSON from text response
  - Light re-ask for non-JSON before retry counting

### Phase 3: Prompt Engineering

- [ ] Implement `prompts.py` for mode-specific prompts
  - json_schema: Minimal - "Output only the JSON object."
  - json_object: Include schema + "Return JSON matching this schema:"
  - inline: Compact declarative spec in prompt

- [ ] Create repair prompt generators
  - Extract failed constraints from Pydantic ValidationError
  - Generate concise repair instructions
  - Append to system prompt on retry

### Phase 4: Main Client

- [ ] Implement `StructuredOutputClient` in `client.py`
  - Mode selection via enum
  - Dispatch to appropriate handler
  - Unified error handling

- [ ] Add comprehensive logging
  - Request/response logging (debug level)
  - Retry attempts and reasons
  - Performance metrics

- [ ] Create public API in `__init__.py`
  - Export Client, Errors, RetryConfig
  - Type exports for generic usage

### Phase 5: Testing

- [ ] Unit tests for each mode handler
  - Mock OpenAI responses
  - Test validation pass/fail
  - Test retry behavior

- [ ] Integration tests with real API (optional flag)
  - Test all three modes
  - Test various model complexities
  - Test error scenarios

- [ ] Create example CLI tool
  - Mode selection via --mode flag
  - Example Pydantic models
  - Demonstrate all three modes

### Phase 6: Documentation

- [ ] Write comprehensive docstrings
- [ ] Create README with usage examples
- [ ] Document mode selection criteria
- [ ] Performance comparison between modes

## Example Usage

```python
from youtrack_mcp.ai.structured import StructuredOutputClient, OutputMode, RetryConfig
from pydantic import BaseModel, Field

class TaskPlan(BaseModel):
    """A structured task plan."""
    title: str = Field(..., description="Task title")
    steps: list[str] = Field(..., min_items=1)
    priority: int = Field(..., ge=1, le=5)
    estimated_hours: float = Field(..., gt=0)

# Initialize client
client = StructuredOutputClient(
    api_key="sk-...",
    mode=OutputMode.JSON_SCHEMA,  # or JSON_OBJECT, INLINE
    retry_config=RetryConfig(max_retries=3)
)

# Generate structured output
result = await client.generate(
    prompt="Create a plan for implementing a REST API",
    response_model=TaskPlan
)

print(f"Title: {result.title}")
print(f"Steps: {result.steps}")
```

## Mode Selection Guide

| Mode | Use When | Pros | Cons |
|------|----------|------|------|
| `json_schema` | Provider supports strict schemas | No retries needed, guaranteed structure | Limited provider support |
| `json_object` | Provider guarantees valid JSON | Balance of reliability and compatibility | Requires local validation |
| `inline` | Maximum compatibility | Works with any provider | Most retry-prone |

## Configuration

```python
# youtrack_mcp/config.py additions
class StructuredOutputConfig(BaseSettings):
    """Configuration for structured output library."""
    
    model_config = ConfigDict(
        env_prefix="STRUCTURED_",
        case_sensitive=False,
    )
    
    mode: OutputMode = Field(OutputMode.JSON_SCHEMA, description="Output mode")
    max_retries: int = Field(3, ge=0, le=10)
    initial_backoff: float = Field(1.0, gt=0)
    backoff_multiplier: float = Field(2.0, gt=1)
    max_backoff: float = Field(60.0, gt=0)
    timeout_seconds: int = Field(30, gt=0)
    
    # Model settings
    model: str = Field("gpt-4o-mini")
    temperature: float = Field(0.3, ge=0, le=2)
    max_tokens: int = Field(2000, gt=0)
```

## Success Metrics

1. **Reliability**: 95%+ success rate in json_schema mode
2. **Retry Efficiency**: <2 average retries in json_object mode
3. **Compatibility**: Works with all OpenAI models
4. **Performance**: <2s overhead for validation/retry
5. **Test Coverage**: >90% code coverage

## Risk Mitigation

1. **Rate Limiting**: Exponential backoff prevents API throttling
2. **Token Usage**: Compact schemas minimize prompt tokens
3. **Error Recovery**: Detailed errors enable debugging
4. **Mode Fallback**: Can switch modes based on provider capabilities