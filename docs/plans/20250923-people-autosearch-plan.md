# People Autosearch Enhancement Plan
**Date:** 2025-09-23
**Status:** Proposed
**AI Agent:** Use Serena MCP tools for codebase search, MorphLLM for edits

## Executive Summary
Enhance the `search.autosearch` tool to resolve display names to YouTrack logins via optional LLM-driven tool calls to `users.search`, maintaining backward compatibility and the existing Instructor pattern.

## Implementation Checklist

### Phase 1: Discovery & Analysis
- [ ] Use Serena MCP to locate `search.autosearch` implementation in `youtrack_mcp/tools/search_tools.py`
- [ ] Identify the exact LLM helper function that performs natural language to YQL translation
- [ ] Locate existing `users.search` implementation for delegation
- [ ] Review current Instructor integration pattern for JSON parsing
- [ ] Document the exact import paths and function signatures
### Phase 2: System Prompt Updates
- [ ] Update the YQL translation prompt in the autosearch helper with these rules:
  ```
  CRITICAL YQL RULES:
  1. For people fields (reporter, assignee, updatedBy, etc.), ALWAYS output the YouTrack login (e.g., cventers), never full names
  2. If you encounter a display name (contains spaces) or email (contains @), call users_search ONCE to resolve to login
  ```
- [ ] Verify prompt changes preserve existing YQL generation capabilities

### Phase 3: LLM Tool Integration
- [ ] Modify the autosearch LLM helper to support tool calling:
  ```python
  # Tool schema for LLM runtime (not MCP)
  tools = [{
      "type": "function",
      "function": {
          "name": "users_search",
          "description": "Resolve a person name/email/login to YouTrack users and return candidates",
          "parameters": {
              "type": "object",
              "properties": {
                  "query": {"type": "string", "description": "Name, email, or login to search"},
                  "limit": {"type": "integer", "default": 5, "description": "Max results"}
              },
              "required": ["query"]
          }
      }
  }]
  ```
- [ ] Implement tool execution handler that delegates to server's `users.search`
- [ ] Add logic to handle tool call response and request final YQL JSON
- [ ] Maintain existing Instructor parsing with `AutoSearchYQLOut` model

### Phase 4: Backward Compatibility
- [ ] Ensure autosearch tool signature remains unchanged
- [ ] Verify return format includes `{"yql": yql}` plus existing results structure
- [ ] Add logging for YQL output and tool call usage (true/false)
- [ ] Test that existing autosearch calls without people references still work

### Phase 5: Test Implementation
- [ ] Create test file: `tests/test_autosearch_people_resolution.py`
- [ ] Implement test case 1: Display name resolution
  ```python
  async def test_autosearch_resolves_display_name():
      # Input: "tickets created by chase venters in projects OPS, PAY, SP"
      # Assert: Tool call made to users.search
      # Assert: Final YQL contains "reporter: cventers"
      # Assert: Project format is "project: OPS, PAY, SP"
  ```
- [ ] Implement test case 2: Direct login (no tool call)
  ```python
  async def test_autosearch_direct_login_no_tool_call():
      # Input: "created by cventers"
      # Assert: No tool call to users.search
      # Assert: YQL contains "reporter: cventers"
  ```
- [ ] Implement test case 3: Email resolution
  ```python
  async def test_autosearch_email_resolution():
      # Input: "assigned to someone@company.com"
      # Assert: Tool call made to users.search
      # Assert: YQL contains resolved login
  ```

### Phase 6: Implementation Details

#### File Changes Required
1. **`youtrack_mcp/tools/search_tools.py`**
   - [ ] Locate `autosearch` tool definition
   - [ ] Update system prompt with YQL rules
   - [ ] Modify LLM helper to expose `users_search` tool
   - [ ] Add tool execution handler

2. **LLM Helper Function Updates**
   - [ ] Add tool definitions to LiteLLM call
   - [ ] Handle tool call responses
   - [ ] Maintain Instructor JSON parsing flow
   - [ ] Add telemetry for tool usage

3. **Test Suite**
   - [ ] Create comprehensive test cases
   - [ ] Mock LLM and users.search responses
   - [ ] Verify YQL output correctness

### Phase 7: Validation & Delivery
- [ ] Run all existing tests to ensure no regression
- [ ] Execute new test cases with mock data
- [ ] Manual test with real YouTrack instance if available
- [ ] Document any edge cases discovered
- [ ] Update CLAUDE.md if new patterns introduced

## Technical Specifications

### LLM Tool Call Flow
```
1. User query: "tickets created by chase venters"
2. LLM receives query + tool definition for users_search
3. LLM calls: users_search(query="chase venters", limit=5)
4. Tool returns: [{"login": "cventers", "fullName": "Chase Venters", ...}]
5. LLM generates: {"yql": "reporter: cventers"}
6. Instructor parses to AutoSearchYQLOut model
7. Execute search.query with generated YQL
```

### Key Constraints
- NO changes to MCP tool signature
- Reuse existing LiteLLM and Instructor patterns
- Preserve all existing functionality

## AI Agent Instructions

**IMPORTANT:** Follow this plan step-by-step, checking off items as completed. Use Serena MCP tools (`mcp__serena__find_symbol`, `mcp__serena__read_file`) for codebase navigation and discovery. Use MorphLLM for actual code edits once you understand the structure.

Start with Phase 1 discovery using Serena tools to understand the codebase structure before making any changes. Document findings in comments as you progress through the checklist.
