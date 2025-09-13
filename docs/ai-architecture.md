# AI Architecture

## Overview

The YouTrack MCP server implements a simplified AI architecture. Error enhancement is always rule-based. NL to YQL translation requires LLM for ai.plan and search autosearch. The architecture consists of three layers:

```
MCP Tools Layer (youtrack_mcp/tools/*)
    ↓
AIService (youtrack_mcp/ai/service.py)
    ↓
OpenAIClient (youtrack_mcp/ai/openai_client.py)
```

## Components

### MCP Tools Layer
- **AIPlanningTools** (`youtrack_mcp/tools/ai_planning_tools.py`): Planning tools requiring LLM
- **AITools** (`youtrack_mcp/tools/ai/ai_tools.py`): AI tools for translation and enhancement

### AIService
Core business logic:
- **Error Enhancement**: Always rule-based using patterns from `data/error_patterns.yaml`
- **NL to YQL Translation**: Requires OpenAI client for ai.plan and search autosearch

### OpenAIClient
Minimal OpenAI SDK adapter supporting configurable backends via `base_url`.

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
      - "Check token permissions for the requested operation."
```

## Usage Examples

### Error Enhancement (Always Rule-Based)
```python
from youtrack_mcp.ai.service import AIService

service = AIService()
result = service.enhance_error_message("Invalid token provided", {})
# Returns rule-based enhanced error with explanation and fix
```

### NL to YQL Translation (Requires LLM)
```python
service = AIService(openai_client=OpenAIClient())
result = service.translate_nl_to_yql("bugs assigned to me")
# Uses OpenAI API for translation
```

### Without LLM Client
```python
service = AIService()  # No openai_client
result = service.translate_nl_to_yql("bugs assigned to me")
# Returns message indicating LLM required
```