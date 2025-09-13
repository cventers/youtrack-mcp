# Plan: Simplify AI Architecture - 2025-09-13

## Objectives
- Simplify the AI stack by removing activity analysis features and hybrid logic paths.
- Consolidate AI business logic into a single AIService module with strict mode switching (off/rule/llm).
- Replace custom HTTP LLM client with a minimal OpenAI SDK adapter supporting configurable backends.
- Resolve AITools naming collision without adding new MCP tools.
- Extract error patterns into a canonical YAML file for deterministic rule-based processing.
- Maintain backward compatibility for existing MCP tool interfaces while refactoring internals.

## Target Architecture
```
MCP Tools Layer (youtrack_mcp/tools/*)
    ↓
AIService (youtrack_mcp/ai/service.py)
    ↓
OpenAIClient (youtrack_mcp/ai/openai_client.py)
```

- **MCP Tools Layer**: Thin wrapper tools (ai_tools.py, ai_planning_tools.py) that delegate to AIService.
- **AIService**: Core business logic for NL→YQL translation and error enhancement with mode switching.
- **OpenAIClient**: Minimal OpenAI SDK adapter for LLM calls, supporting base_url overrides.

## File-by-File Change Map

### Adds
- `youtrack_mcp/ai/__init__.py` - Package init for ai module.
- `youtrack_mcp/ai/service.py` - New AIService class consolidating logic from ai_processor.py.
- `youtrack_mcp/ai/openai_client.py` - New OpenAIClient class replacing llm_client.py.
- `data/error_patterns.yaml` - Canonical rule library at repo root.
- `local/config.yaml` - Example config with YOUTRACK_AI_MODE and OPENAI_* variables.
- `local/.env.example` - Environment variable examples.
- `docs/ai-architecture.md` - Final architecture diagram and usage examples.
- `docs/configuration.md` - Environment variables, defaults, and configuration guide.
- `tests/unit/test_ai_service.py` - Unit tests for AIService (rule mode, llm mode, off mode).
- `tests/unit/test_openai_client.py` - Unit tests for OpenAIClient adapter.

### Deletes
- `youtrack_mcp/tools/ai/llm_client.py` - Replaced by ai/openai_client.py.
- All activity analysis code paths in ai_processor.py (to be removed during refactor).
- Any hybrid fallback logic in ai_processor.py.

### Renames
- `youtrack_mcp/tools/ai_tools.py` → `youtrack_mcp/tools/ai_planning_tools.py` (class AIPlanningTools).
- Class in `youtrack_mcp/tools/ai/ai_tools.py` remains AITools but updated to use AIService.

### Edits
- `youtrack_mcp/tools/ai/ai_processor.py` - Move logic to service.py, then delete file.
- `youtrack_mcp/tools/ai/ai_tools.py` - Update to call AIService instead of ai_processor.
- `youtrack_mcp/mcp_server.py` - Update imports to use AIPlanningTools and AITools explicitly.
- `youtrack_mcp/tools/loader.py` - Update imports to avoid shadowing.
- `youtrack_mcp/config.py` - Add YOUTRACK_AI_MODE and OPENAI_* config handling.
- `tests/unit/test_ai_tools.py` - Update to test new structure.
- `tests/unit/test_ai_processor.py` - Rename to test_ai_service.py or integrate into new tests.
- `pyproject.toml` - Add openai SDK dependency (>=1.x).
- `requirements.txt` - Update with openai SDK.

## Environment/Config Notes
- **YOUTRACK_AI_MODE**: Enum {off, rule, llm}. Default: rule. Controls AI behavior.
  - off: Disable AI features, return structured "disabled" responses.
  - rule: Use rule-based processing only (deterministic, no LLM calls).
  - llm: Use LLM adapter only (no rule fallback).
- **OPENAI_API_KEY**: Required for llm mode. Secure token storage.
- **OPENAI_BASE_URL**: Optional. Defaults to OpenAI API; override for compatible backends (e.g., local servers).
- **OPENAI_MODEL**: Optional. Default: gpt-4o-mini. Model for completions.
- **OPENAI_TEMPERATURE**: Optional. Default: 0.7. Controls response randomness.
- **OPENAI_TIMEOUT**: Optional. Default: 30 seconds. Request timeout.
- Config loaded via local/config.yaml or environment variables. No hybrid mode support.

## Schema for data/error_patterns.yaml
Located at repo root. YAML structure:

```yaml
version: "1.0"
updated_at: "2025-09-13T00:00:00Z"
patterns:
  - id: "auth_token_invalid"
    match: "regex|^Invalid token.*$"
    scope: "authentication"
    examples:
      - "Invalid token provided"
      - "Token expired or malformed"
    classification:
      category: "authentication_error"
      severity: "high"
    explanation: "The provided authentication token is invalid or expired."
    remediation_steps:
      - "Verify your YouTrack token in configuration."
      - "Regenerate token if expired."
      - "Check token permissions for the requested operation."
    developer_notes: "Common during initial setup or token rotation."
    test_vectors:
      - input: "Invalid token provided"
        expected_output: "Authentication failed: Invalid token. Verify your YouTrack token..."
  - id: "project_not_found"
    match: "exact|Project 'DEMO' not found"
    scope: "projects"
    examples:
      - "Project 'DEMO' not found"
    classification:
      category: "resource_error"
      severity: "medium"
    explanation: "The specified project does not exist."
    remediation_steps:
      - "Check project shortName spelling."
      - "Verify project exists in YouTrack."
      - "Use projects.list tool to see available projects."
    developer_notes: "Exact match for specific error messages."
    test_vectors:
      - input: "Project 'DEMO' not found"
        expected_output: "Project not found: DEMO. Check project shortName..."
```

- **version**: String, semantic version.
- **updated_at**: ISO 8601 timestamp.
- **patterns**: List of pattern objects.
  - **id**: Unique string identifier.
  - **match**: "regex|<pattern>" or "exact|<text>" for matching.
  - **scope**: Module/component (e.g., "authentication", "projects").
  - **examples**: List of raw error snippets.
  - **classification**: Object with category (string) and severity (low/medium/high).
  - **explanation**: User-facing description.
  - **remediation_steps**: Ordered list of strings.
  - **developer_notes**: Optional string for internal notes.
  - **test_vectors**: List of input→expected_output for testing.

AIService loads and validates this YAML at startup; fails fast with clear message if invalid.

## Test Plan

### Rule-Based Error Enhancement
- **Pattern Specificity**: Test regex vs exact matches; ensure precedence (first match wins).
- **Deterministic Outputs**: Verify identical inputs produce identical outputs; no randomness.
- **Confidence/Priority**: Test severity-based ordering; high-severity patterns override low.
- **Exact Outputs**: Match test_vectors in error_patterns.yaml; validate explanation and remediation rendering.

### NL→YQL Behavior
- **Rule Mode**: Expect deterministic YQL generation based on predefined patterns; no LLM calls; test common queries (e.g., "bugs assigned to me" → "assignee: me state: Open").
- **LLM Mode**: Test OpenAIClient integration; mock SDK for responses; validate prompt construction and result parsing.
- **Off Mode**: Return structured disabled response with guidance.

### OpenAIClient Adapter Behavior
- **Base URL Override**: Test with mock base_url; ensure requests go to custom endpoint.
- **Timeouts/Errors**: Simulate network failures; verify robust error handling (retries, clear messages).
- **Mock SDK**: Use unittest.mock to patch openai SDK; test complete() method with various parameters.

## Rollback Plan + Risk List
- **Rollback**: Revert branch feat/simplify-ai-arch; restore original ai_processor.py and llm_client.py; remove new files.
- **Risks**:
  - Vendor differences: OpenAI-compatible servers may have API variations; test with multiple backends.
  - Dependency issues: OpenAI SDK version conflicts; pin to >=1.x.
  - Performance: LLM mode may introduce latency; monitor timeouts.
  - Config errors: Invalid YAML or missing env vars; add validation with clear errors.

## Acceptance Criteria + Checklist
- [ ] AITools naming collision resolved; no shadowing in imports.
- [ ] Rule mode works without API keys; passes all rule-based tests.
- [ ] LLM mode uses OpenAI SDK with base_url; no rule fallback.
- [ ] data/error_patterns.yaml exists, valid, and loaded by AIService.
- [ ] Activity analysis code removed entirely.
- [ ] No hybrid logic paths.
- [ ] MCP tool interfaces stable; no new tools added.
- [ ] Config examples in local/; docs updated.
- [ ] All tests pass; CI green.
- [ ] Architecture matches ASCII diagram.