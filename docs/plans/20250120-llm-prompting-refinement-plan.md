# LLM Prompting System Refinement Plan

**Version**: 3.0
**Date**: 2025-01-20
**Status**: APPROVED
**Supersedes**: 20250119-llm-prompting-plan.md (v2.0)

## Executive Summary

This refinement plan addresses fundamental architectural issues discovered in the v2.0 implementation. The system will be rebuilt using modern async patterns, litellm+instructor for provider-agnostic structured outputs, and Jinja2 templates for maintainable prompt management.

## Problems with Current Implementation (v2.0)

1. **Unnecessary Sync Wrappers**: FastMCP supports async natively, but we added sync wrappers creating nested event loops
2. **Backward Compatibility Debt**: Maintaining dual response formats adds complexity without benefit
3. **Hardcoded Prompts**: Inline prompts reduce maintainability and reusability
4. **Vendor Lock-in**: Direct OpenAI SDK usage limits provider flexibility
5. **Redundant Configuration**: Reimplemented features that litellm/instructor already provide

## Refinement Objectives

### 1. Drop Backward Compatibility
- **Remove**: `QueryTranslationResult` dataclass
- **Remove**: `ErrorEnhancementResult` dataclass
- **Remove**: Sync wrapper methods (`*_sync`, `_llm_*`)
- **Remove**: Field mapping/transformation code
- **Use**: Pydantic models directly throughout

### 2. Full Async Architecture
- **Convert**: All AI tool methods to async
- **Convert**: AIService methods to async-only
- **Remove**: `asyncio.run()` calls
- **Ensure**: Clean async call chain from MCP tools to LiteLLM/Instructor

### 3. Jinja2 Template System
- **Create**: Template directory structure
- **Migrate**: All prompts to Jinja2 templates
- **Support**: Mode-specific template variants
- **Enable**: Template composition and inheritance

### 4. LiteLLM + Instructor Integration
- **Replace**: OpenAI SDK with litellm
- **Add**: Instructor for structured outputs
- **Remove**: Custom retry logic (instructor handles it)
- **Remove**: Custom JSON extraction (instructor handles it)
- **Support**: Multiple providers (OpenAI, Anthropic, etc.)

### 5. Simplified Configuration
- **Remove**: `LLMConfig.output_mode` (instructor handles modes)
- **Remove**: `LLMConfig.extract_json_from_markdown`
- **Replace**: Custom retry parameters with instructor configurables
- **Keep**: Provider selection and API keys
- **Add**: Instructor retry configuration (max_retries, timeout, etc.)
- **Add**: LiteLLM conversation logging configuration

## Implementation Plan

### Phase 1: LiteLLM + Instructor Setup

#### 1.1 Dependencies
```toml
[project.dependencies]
litellm = ">=1.0.0"
instructor = ">=1.0.0"
# Remove direct openai dependency
```

#### 1.2 New Client Module (`youtrack_mcp/ai/llm_client.py`)
```python
import instructor
from litellm import acompletion
from typing import Type, TypeVar
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)

class LLMClient:
    def __init__(self, model: str = "gpt-4o-mini", **kwargs):
        self.model = model
        self.client = instructor.from_litellm(acompletion)

    async def complete_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system: str = None,
        **kwargs
    ) -> T:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        return await self.client.create(
            model=self.model,
            messages=messages,
            response_model=response_model,
            **kwargs
        )
```

### Phase 2: Template System

#### 2.1 Directory Structure
```
youtrack_mcp/ai/templates/
├── base.j2                 # Base template with common structure
├── yql/
│   ├── translation.j2      # YQL translation template
│   └── partials/
│       └── context.j2      # Reusable context snippet
├── error/
│   ├── enhancement.j2      # Error enhancement template
│   └── categories.j2       # Error category definitions
└── intent/
    ├── analysis.j2         # Intent analysis template
    └── plan_steps.j2       # Plan step formatting
```

#### 2.2 Template Example (`yql/translation.j2`)
```jinja2
{% extends "base.j2" %}

{% block system %}
You are an expert YouTrack Query Language (YQL) assistant specializing in query translation.

Core capabilities:
- Deep understanding of YQL syntax and operators
- Knowledge of YouTrack entities and custom fields
- Expertise in date ranges and relative time expressions
- Optimization of queries for performance
{% endblock %}

{% block user %}
Task: Convert natural language to precise YQL query.

Query: {{ natural_query }}
{% if project_context %}
Project Context: {{ project_context }}
{% include "yql/partials/context.j2" %}
{% endif %}

Requirements:
- Generate accurate YQL syntax
- Use {} for multi-word values
- Apply correct date formats
- Optimize for performance
{% endblock %}
```

#### 2.3 Template Loader Update
```python
class TemplateManager:
    def __init__(self, template_dir: Path):
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape()
        )

    def render(self, template_name: str, **context) -> dict:
        template = self.env.get_template(template_name)
        content = template.render(**context)
        # Parse rendered content into system/user messages
        return self._parse_messages(content)
```

### Phase 3: Async Conversion

#### 3.1 AI Tools (`youtrack_mcp/tools/ai/ai_tools.py`)
```python
class AITools:
    async def translate_to_yql(
        self,
        natural_language_query: str,
        project_context: Optional[str] = None
    ) -> YQLTranslationResponse:
        """Direct async method returning Pydantic model."""
        return await self.ai_service.translate_nl_to_yql(
            natural_language_query,
            project_context
        )
```

#### 3.2 AI Service (`youtrack_mcp/ai/service.py`)
```python
class AIService:
    async def translate_nl_to_yql(
        self,
        natural_query: str,
        project_context: Optional[str] = None
    ) -> YQLTranslationResponse:
        """Async-only method using templates."""

        # Render template
        messages = self.template_manager.render(
            "yql/translation.j2",
            natural_query=natural_query,
            project_context=project_context
        )

        # Get structured response
        return await self.llm_client.complete_structured(
            messages=messages,
            response_model=YQLTranslationResponse
        )
```

#### 3.3 Search Tools (`youtrack_mcp/tools/search_tools.py`)
```python
async def autosearch(self, query: str, context: str = None) -> dict:
    # Direct async call, no wrapper needed
    response = await self.ai_tools.translate_to_yql(query, context)

    # Use Pydantic model directly
    return {
        "yql": response.yql_query,
        "confidence": response.confidence,
        "results": await self._execute_query(response.yql_query)
    }
```

### Phase 4: Configuration Cleanup

#### 4.1 Simplified Config (`youtrack_mcp/config.py`)
```python
class LLMConfig(BaseSettings):
    """Simplified LLM configuration with instructor/litellm support."""

    model_config = ConfigDict(
        env_prefix="LLM_",
        case_sensitive=False,
    )

    # Provider configuration
    provider: str = Field("openai", description="LLM provider (openai, anthropic, etc.)")
    model: str = Field("gpt-4o-mini", description="Model name")

    # API configuration
    api_key: SecretStr = Field(..., description="API key for provider")
    api_base: Optional[str] = Field(None, description="Custom API endpoint")

    # Instructor retry configuration (hoisted from instructor)
    max_retries: int = Field(3, description="Max validation retries")
    retry_on_validation_error: bool = Field(True, description="Retry on validation errors")
    timeout: float = Field(60.0, description="Request timeout in seconds")
    temperature: float = Field(0.3, description="Temperature for responses")

    # LiteLLM conversation logging
    log_conversations: bool = Field(False, description="Enable conversation logging")
    log_level: str = Field("INFO", description="Logging level for LLM conversations")
    log_format: str = Field("json", description="Format for conversation logs (json/text)")
    redact_api_keys: bool = Field(True, description="Redact API keys from logs")

    # Template configuration
    template_dir: Path = Field("ai/templates", description="Template directory")
```

#### 4.2 Remove from Config
- `output_mode` - Instructor handles this automatically
- `json_schema`, `json_object`, `inline` modes - Not needed
- `extract_json_from_markdown` - Instructor handles extraction
- `initial_backoff`, `backoff_multiplier` - Replaced with instructor configurables

### Phase 5: Registry Update

#### 5.1 Simplified Registry (`youtrack_mcp/ai/registry.py`)
```python
class AIServiceRegistry:
    def _initialize_llm_client(self):
        """Initialize LiteLLM + Instructor client with logging."""
        settings = Settings()

        # Configure LiteLLM logging
        if settings.llm.log_conversations:
            import litellm
            litellm.success_callback = ["logger"]
            litellm.failure_callback = ["logger"]
            litellm.set_verbose = settings.llm.log_level == "DEBUG"

            # Configure our custom logger for conversations
            self._setup_conversation_logger(settings.llm)

        self._llm_client = LLMClient(
            model=f"{settings.llm.provider}/{settings.llm.model}",
            api_key=settings.llm.api_key.get_secret_value(),
            api_base=settings.llm.api_base,
            max_retries=settings.llm.max_retries,
            retry_on_validation_error=settings.llm.retry_on_validation_error,
            timeout=settings.llm.timeout,
            temperature=settings.llm.temperature
        )

    def _setup_conversation_logger(self, llm_config):
        """Setup conversation logging with configurable format."""
        import logging
        import json

        logger = logging.getLogger("llm.conversations")
        logger.setLevel(getattr(logging, llm_config.log_level))

        # Create formatter based on config
        if llm_config.log_format == "json":
            formatter = logging.Formatter(
                '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
                '"message": "%(message)s"}'
            )
        else:
            formatter = logging.Formatter(
                '%(asctime)s - LLM - %(levelname)s - %(message)s'
            )

        # Add handler if not present
        if not logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        # Hook into LiteLLM callbacks for conversation dumping
        def log_conversation(kwargs, response, start_time, end_time):
            """Log LLM conversation with configurable redaction."""
            conversation = {
                "model": kwargs.get("model"),
                "messages": kwargs.get("messages"),
                "response": response.model_dump() if hasattr(response, 'model_dump') else str(response),
                "duration": end_time - start_time
            }

            if llm_config.redact_api_keys:
                # Redact API keys from logged data
                conversation = self._redact_sensitive_data(conversation)

            if llm_config.log_format == "json":
                logger.info(json.dumps(conversation))
            else:
                logger.info(f"LLM Call: {conversation}")

        # Register callback with LiteLLM
        import litellm
        litellm.success_callback.append(log_conversation)
```

## Migration Strategy

### Step 1: Install Dependencies
```bash
uv remove openai
uv add litellm instructor
```

### Step 2: Parallel Implementation
1. Create new modules alongside existing ones
2. Implement litellm client
3. Create template system
4. Convert one tool at a time

### Step 3: Testing
1. Unit tests for each component
2. Integration tests with mock LLM
3. End-to-end tests with real API

### Step 4: Cutover
1. Update imports in main code
2. Remove old modules
3. Clean up configuration

## Benefits

### 1. Provider Flexibility
- Switch between OpenAI, Anthropic, Gemini, etc. with config change
- Use local models (Ollama, vLLM) for development
- Automatic fallback between providers

### 2. Maintainability
- Templates are easier to modify than code
- Prompts can be A/B tested
- Version control for prompt evolution

### 3. Performance
- No nested event loops
- Native async throughout
- Efficient retry handling by instructor

### 4. Simplicity
- Less custom code to maintain
- Standard patterns from instructor
- Cleaner configuration

## Success Metrics

1. **Code Reduction**: 50% less code in AI module
2. **Performance**: 30% faster response times (no nested loops)
3. **Flexibility**: Support 5+ LLM providers
4. **Maintainability**: All prompts in templates
5. **Reliability**: Instructor's battle-tested retry logic

## Risks and Mitigations

### Risk 1: Breaking Changes
- **Impact**: All AI-dependent tools need updates
- **Mitigation**: Update all tools in single PR

### Risk 2: Template Complexity
- **Impact**: Complex templates might be hard to debug
- **Mitigation**: Keep templates simple, use composition

### Risk 3: Instructor Learning Curve
- **Impact**: New patterns to learn
- **Mitigation**: Follow instructor documentation examples

## Timeline

- **Day 1**: Setup litellm + instructor, create base client
- **Day 2**: Implement template system
- **Day 3**: Convert all tools to async
- **Day 4**: Testing and debugging
- **Day 5**: Documentation and cleanup

## Decision

This refinement plan is **APPROVED** for immediate implementation. The benefits of a clean async architecture with provider-agnostic structured outputs outweigh the cost of dropping backward compatibility.

## References

- [Instructor Documentation](https://github.com/567-labs/instructor)
- [LiteLLM Documentation](https://docs.litellm.ai/docs/tutorials/instructor)
- [Jinja2 Template Documentation](https://jinja.palletsprojects.com/)
- [FastMCP Async Support](https://github.com/FastMCP/fastmcp)