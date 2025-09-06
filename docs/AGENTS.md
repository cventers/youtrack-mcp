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

### 🔄 TODO Implementation Priorities
1. **Phase 1** (Critical): httpx.AsyncClient migration, MCP compliance tests
2. **Phase 3** (High): LLM-optimized error handling, MCP Resources
3. **Phase 4** (High): User activity tracking, date/time conversion utilities

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

## Agent-Specific Notes

When working on this codebase:
1. **Consult TODO.md first** - It contains detailed implementation guidance
2. **Use extracted documentation** - `docs/third-party/` has comprehensive API reference
3. **Follow existing patterns** - Study current implementations before adding new features
4. **Test MCP compliance** - Ensure tools work with Claude Code CLI
5. **Focus on LLM usability** - Error messages should help LLMs learn and improve

The project prioritizes practical YouTrack integration over theoretical MCP protocol details, with emphasis on error handling that helps LLMs provide better user experiences.