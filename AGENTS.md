# YouTrack MCP Server - AI Agent Documentation

This document provides guidance for AI agents working on the YouTrack MCP (Model Context Protocol) server implementation.

## Project Structure

### Core Implementation
- **`main.py`** - FastMCP server implementation with all MCP tools
- **`youtrack_mcp/`** - Core library modules
  - **`api/`** - YouTrack API client implementations
    - `client.py` - Base HTTP client with authentication
    - `issues.py` - Issue operations (CRUD, search, linking)
    - `projects.py` - Project management operations
    - `users.py` - User management operations
  - **`tools/`** - MCP tool implementations (modular architecture)
    - **`issues/`** - Modular issue management (8 focused modules)
      - `basic_operations.py` - Core CRUD operations
      - `custom_fields.py` - Custom field management
      - `dedicated_updates.py` - Specialized updates
      - `linking.py` - Issue relationships
      - `diagnostics.py` - Workflow analysis
      - `attachments.py` - File operations
      - `comments.py` - Comment management
      - `utilities.py` - Infrastructure functions
    - `core_issues.py` - Core issue operations
    - `core_projects.py` - Project management
    - `core_search.py` - Search functionality
    - `core_users.py` - User management
  - **`config.py`** - Configuration management
  - **`utils.py`** - Utility functions (date conversion, field resolution)

### Documentation

#### `docs/` Directory
Contains comprehensive project documentation:

- **`TODO.md`** - Detailed implementation roadmap with 5 phases
  - Phase 1: Critical async fixes (httpx.AsyncClient, MCP compliance)
  - Phase 2: Claude CLI compatibility (handshake, logging, timeout)
  - Phase 3: Exception handling and MCP Resources
  - Phase 4: Custom fields and activity tracking
  - Phase 5: Performance optimization and testing
- **`REFACTORING_TRACKER.md`** - Complete documentation of the modular architecture refactoring
  - 8 focused modules replacing monolithic 1,797-line file
  - 120+ unit tests with comprehensive coverage
  - Backward compatibility maintained

#### `docs/third-party/` Directory  
Contains extracted official documentation from YouTrack APIs:

- **`youtrack-api-concepts.md`** - Core API patterns, authentication, URL structure
- **`youtrack-authentication.md`** - Token-based auth, OAuth 2.0, security best practices
- **`youtrack-api-url-structure.md`** - Endpoint patterns, URL construction
- **`youtrack-getting-started.md`** - Getting started guide, development tools
- **`youtrack-query-language.md`** - Complete YQL syntax reference with examples
- **`youtrack-custom-fields.md`** - All custom field types, API endpoints, value structures  
- **`youtrack-commands-api.md`** - Bulk operations, command syntax, practical examples
- **`youtrack-error-handling.md`** - HTTP status codes, error patterns, troubleshooting

The **`docs/third-party.md`** file serves as an index to all extracted documentation with extraction status and coverage notes.

## Key Implementation Concepts

### Authentication
- **Preferred**: Permanent token authorization (simpler, more secure)
- **Alternative**: OAuth 2.0 (for client-side applications)
- **Security**: Environment variable token storage, HTTPS required

### YouTrack Query Language (YQL)
- **Syntax**: `attribute: value` pairs with logical operators
- **Special Characters**: `{}` for multi-word values, `..` for ranges, `*` wildcards
- **Date Formats**: `YYYY-MM-DD`, relative dates like `{minus 7d}`, `{Last week}`
- **Field References**: Built-in fields and `{Custom Field Name}` syntax

### Custom Fields
- **Entity Hierarchy**: CustomField → ProjectCustomField → IssueCustomField
- **Types**: Enum, User, Group, Date, Text, Numeric, Build/Version, State
- **Value Resolution**: Field values need resolution to human-readable text

### Commands API
- **Purpose**: Bulk operations on multiple issues simultaneously
- **Syntax**: Similar to UI commands (`for john.doe Priority High`)
- **Features**: Silent mode, comments, visibility groups
- **Performance**: Much faster than individual API calls

## Current Implementation Status

### ✅ Working Features
- All basic MCP tools (get_issue, create_issue, search_issues, etc.)
- Project management (get_projects, create_project, update_project)
- User management (get_users, search_users)
- Issue linking and dependencies
- Commands API integration for bulk operations
- Custom field handling with value resolution



## Development Environment Setup

### Python Environment Management with uv

This project uses `uv` for fast Python package management and virtual environment handling.

#### Initial Setup
```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment (already done)
uv venv .venv

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
uv pip install -e .
```

#### Daily Development Workflow
```bash
# Activate virtual environment
source .venv/bin/activate

# Install new dependencies
uv add package-name

# Run tests
uv run pytest

# Run the application
uv run python main.py

# Update dependencies
uv lock --upgrade
```

#### uv Commands Reference
- `uv venv .venv` - Create virtual environment
- `uv pip install -e .` - Install project in editable mode
- `uv add package-name` - Add new dependency
- `uv remove package-name` - Remove dependency
- `uv run command` - Run command in virtual environment
- `uv lock` - Update lock file
- `uv lock --upgrade` - Upgrade all dependencies

#### Virtual Environment Notes
- **Always activate** `.venv` before working: `source .venv/bin/activate`
- **Never commit** `.venv/` directory (it's in .gitignore)
- **Use uv run** for all Python commands to ensure proper environment
- **Dependencies** are managed via `pyproject.toml` and `uv.lock`

## Development Guidelines

### Error Handling Philosophy
- **Preserve YouTrack errors**: Return original API errors with added educational context
- **LLM-friendly**: Include explanations, examples, and "learn from this" guidance
- **Specific exceptions**: Replace generic `except Exception` with specific error types

### Performance Considerations
- **Async Operations**: Use httpx.AsyncClient for all HTTP requests
- **Caching Strategy**: Multi-layer caching (in-process, Redis, background jobs)
- **Rate Limiting**: Respect YouTrack API limits, implement exponential backoff

### Security Best Practices
- **Token Management**: Lazy loading, secure storage, never log tokens
- **Input Validation**: Validate all user inputs before API calls
- **Permission Handling**: Check user permissions, handle 403 errors gracefully

## Testing Strategy

### MCP Compliance
- **Required**: `pip install mcp[test]` and `pytest -k mcp_contracts`
- **Purpose**: Ensure handshake/capability message compatibility
- **Critical**: For Claude Code CLI auto-resume functionality

### Multi-Model Testing
- **Providers**: Test with Anthropic, OpenAI, Google, Mistral
- **Focus**: Tool-call formatting, parameter validation, JSON schema compliance
- **Mock API**: Use `respx` for YouTrack API mocking in CI

## Common Patterns

### API Client Usage
```python
# Use the existing client instances
issues = self.client.issues.search_issues(query="project: MyProject")
projects = self.client.projects.get_projects()
```

### Error Response Format
```python
return {
    "error": "Operation failed",
    "youtrack_error": str(original_error),
    "explanation": "What went wrong and why",
    "recommendation": "How to fix it in the future",
    "learn_from_this": "Key lessons for LLM"
}
```

### Query Construction
```python
# Date ranges
query = f"created: {start_date} .. {end_date}"

# Multi-field search
query = f"project: {project} state: Open assignee: {user}"

# Custom fields
query = f"{{Priority}}: High {{Component}}: Backend"
```

## Resources for Development

### Official Documentation
- All extracted documentation in `docs/third-party/`
- YouTrack Developer Portal: https://www.jetbrains.com/help/youtrack/devportal/
- MCP SDK Documentation (FastMCP library handles protocol details)

### Key Implementation Files
- Review existing `main.py` for MCP tool patterns
- Study `youtrack_mcp/api/` modules for API interaction patterns
- Check `TODO.md` for upcoming implementation requirements

## ✅ **COMPLETED: Modular Architecture Refactoring**

### Refactoring Results
- **Status:** 100% complete - monolithic 1,797-line file transformed into 8 focused modules
- **Modules Created:** basic_operations, custom_fields, dedicated_updates, linking, diagnostics, attachments, comments, utilities
- **Test Coverage:** 120+ unit tests with comprehensive validation across all modules
- **Code Reduction:** 90% smaller main interface file through modular delegation
- **Backward Compatibility:** Fully maintained - existing code continues to work unchanged

### Architecture Benefits
- **Maintainability:** Clear separation of concerns with single-responsibility modules
- **Testability:** Focused modules enable comprehensive unit testing
- **Scalability:** Independent module development and deployment
- **Documentation:** Improved code organization with comprehensive docstrings

## Agent-Specific Notes

When working on this codebase:
1. **Consult REFACTORING_TRACKER.md** - Complete documentation of the modular architecture
2. **Consult TODO.md first** - It contains detailed implementation guidance
3. **Use extracted documentation** - `docs/third-party/` has comprehensive API reference
4. **Follow existing patterns** - Study current implementations before adding new features
5. **Test MCP compliance** - Ensure tools work with Claude Code CLI
6. **Focus on LLM usability** - Error messages should help LLMs learn and improve

The project prioritizes practical YouTrack integration over theoretical MCP protocol details, with emphasis on error handling that helps LLMs provide better user experiences. The modular architecture enhances maintainability while preserving all existing functionality.

## Tool Calling Standards (POST-REFACTOR)

### Canonical Invocation Format
**ALL tool calls MUST use the strict JSON object format:**

```json
{
  "tool_name": "issues.get",
  "arguments": {
    "issue_id": "DEMO-123",
    "include": ["customFields", "comments"]
  }
}
```

### Key Requirements
1. **Single arguments object**: All parameters go in the `arguments` object
2. **No positional arguments**: Everything is a named parameter
3. **Strict validation**: JSON Schema validation with `additionalProperties: false`
4. **No automatic repair**: Invalid calls return clear validation errors
5. **Exact parameter names**: Use schema-defined names (no fuzzy matching)

### Migration from Legacy Format
**OLD (deprecated):**
```python
# Flexible args/kwargs with repair
result = issues.get("DEMO-123", include=["customFields"])
result = issues.create(project="DEMO", summary="Bug")
```

**NEW (required):**
```python
# Strict JSON schema
result = call_tool({
    "tool_name": "issues.get",
    "arguments": {
        "issue_id": "DEMO-123",
        "include": ["customFields"]
    }
})
```

### Available Tools and Schemas
- `issues.get` - Rich issue read with expansions
- `issues.create` - Schema-aware issue creation
- `issues.patch` - Update with fields{} or ops[] (oneOf validation)
- `projects.list` - List projects with pagination
- `projects.get` - Project details with include expansions
- `projects.schema` - Get project custom field schema
- `projects.patch` - Update project fields
- `projects.create` - Create new project
- `users.search` - Search users by name/login
- `search.query` - Execute YQL queries
- `search.autosearch` - Natural language to YQL translation
- `ai.plan` - Generate operation plans
- `resources.read` - Read MCP resources

### Error Handling
- **Schema validation errors**: Clear messages indicating exactly what's wrong
- **Missing required fields**: Specific field names listed
- **Invalid enums**: Allowed values provided
- **Extra properties**: Rejected with `additionalProperties: false`

### Environment Flags

- Default: Strict validation only (legacy router disabled)

### Benefits
- **Predictable**: Same input always produces same behavior
- **Debuggable**: Clear validation errors, no silent repairs
- **Portable**: Works with any MCP client without custom logic
- **Maintainable**: No complex repair logic to maintain
- **Token-efficient**: Smaller schemas, less context usage

## Tool Design Philosophy (READ ME BEFORE PROPOSING TOOLS)

**We optimize for a *small, stable* default tool surface.** Tools are expensive tokens in MCP: names, schemas, and descriptions all consume context. Fewer, more expressive tools → better models, fewer errors.

### DO
- **Use the default pack (12 tools)** unless capability flags explicitly enable more.
- **Make reads rich via `include[]`**, not by inventing new read tools. Example: `issues.get(include=["comments","attachments","links","work_items","history","activities","time_tracking"])` and `projects.get(include=["schema","versions","builds","subsystems"])`.
- **Make all writes go through `issues.patch`** using a **typed subpath grammar**:
  - `/fields/<FieldName>` for custom/system fields (schema-aware enum/state/user/period coercion).
  - `/comments`, `/attachments`, `/links`, `/work_items` add/replace/remove.
- **Expose planning, not auto-exec**: `ai.plan` returns change plans; human/agent must call `issues.patch` explicitly.

### DON’T
- **DON’T add narrow, single-purpose tools** (e.g., `projects.custom_fields`, `issues.update_custom_fields`, `comments.update_comment`).
- **DON’T put long tutorials in tool descriptions**. Keep descriptions short; put examples in `help://...` resources.
- **DON’T use fuzzy project/field matching**. Resolve exact `shortName`/`name`; return candidates on ambiguity.

### When you think we “need a new tool”
1. Can this be an **`include[]` expansion** on an existing read tool? → Use that.
2. Can this be an **`ops[]` or `fields{}`** pattern on `issues.patch`? → Use that.
3. Is it administrative and rarely used? → Put it in a **capability-gated pack** (off by default).
4. Still convinced? Propose the change with:
   - A before/after **token budget** for serialized tool schemas,
   - Test deltas and failure modes.

**Agents MUST match this architecture** when proposing tool changes. PRs that add narrow tools without exhausting the options above will be rejected.

