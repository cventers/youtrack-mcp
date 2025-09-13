# AI Architecture

## Overview

The YouTrack MCP server implements a simplified AI architecture with strict mode switching and no hybrid logic. The architecture consists of three layers:

```
MCP Tools Layer (youtrack_mcp/tools/*)
    ↓
AIService (youtrack_mcp/ai/service.py)
    ↓
OpenAIClient (youtrack_mcp/ai/openai_client.py)
```

## Components

### MCP Tools Layer
- **AIPlanningTools** (`youtrack_mcp/tools/ai_planning_tools.py`): Minimal planning-only tools
- **AITools** (`youtrack_mcp/tools/ai/ai_tools.py`): Rich AI tools for translation and enhancement

### AIService
Core business logic with mode switching:
- **off**: Returns structured disabled responses
- **rule**: Uses rule-based processing only (deterministic)
- **llm**: Uses LLM adapter only (no rule fallback)

### OpenAIClient
Minimal OpenAI SDK adapter supporting configurable backends via `base_url`.

## Mode Configuration

Set `YOUTRACK_AI_MODE` environment variable:

- `off`: Disable AI features
- `rule`: Rule-based processing (default)
- `llm`: LLM-powered processing

## Error Patterns

Rule-based error enhancement uses patterns from `data/error_patterns.yaml`:

```yaml
patterns:
  - id: "auth_token_invalid"
    match: "regex|^Invalid token.*$"
    scope: "authentication"
    classification:
      category: "authentication_error"
      severity: "high"
    explanation: "The provided authentication token is invalid or expired."
    remediation_steps:
      - "Verify your YouTrack token in configuration."
      - "Regenerate token if expired."
```

## Usage Examples

### Rule Mode (Default)
```python
from youtrack_mcp.ai.service import AIService

service = AIService(mode="rule")
result = service.translate_nl_to_yql("bugs assigned to me")
# Returns deterministic YQL: "assignee: me state: Open"
```

### LLM Mode
```python
service = AIService(mode="llm", openai_client=OpenAIClient())
result = service.translate_nl_to_yql("bugs assigned to me")
# Uses OpenAI API for translation
```

### Off Mode
```python
service = AIService(mode="off")
result = service.translate_nl_to_yql("bugs assigned to me")
# Returns disabled response with guidance
```