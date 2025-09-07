# 🏗️ YouTrack MCP Architecture

This document provides a comprehensive overview of the YouTrack MCP server's modern modular architecture.

## Modular Design

The YouTrack MCP server features a modern, modular architecture that enhances maintainability, testability, and code organization. The core `issues` module has been refactored from a monolithic 1,797-line file into 8 focused modules:

```
youtrack_mcp/tools/issues/
├── __init__.py                 # Package initialization and unified interface
├── basic_operations.py         # Core CRUD operations (get, create, update, search)
├── custom_fields.py            # Custom field management and validation
├── dedicated_updates.py        # Specialized update functions (state, priority, assignee)
├── linking.py                  # Issue relationships and dependencies
├── diagnostics.py              # Workflow analysis and help systems
├── attachments.py              # File and raw data operations
├── comments.py                 # Comment retrieval and management
└── utilities.py                # Infrastructure and tool definitions
```

## Architecture Benefits

- **🔧 Maintainability**: Each module has a single responsibility, making code easier to understand and modify
- **🧪 Testability**: Focused modules enable comprehensive unit testing (120+ tests across all modules)
- **📈 Scalability**: Clear separation of concerns allows for independent module development
- **🔄 Backward Compatibility**: Existing API interfaces remain unchanged
- **📚 Documentation**: Improved code organization with comprehensive docstrings

## Module Responsibilities

| Module | Functions | Purpose |
|--------|-----------|---------|
| `basic_operations` | 5 functions | Core CRUD operations for issues |
| `custom_fields` | 5 functions | Custom field management and validation |
| `dedicated_updates` | 5 functions | Specialized field updates with enhanced error handling |
| `linking` | 7 functions | Issue relationships and dependency management |
| `diagnostics` | 2 functions | Workflow analysis and interactive help |
| `attachments` | 2 functions | File operations and raw data access |
| `comments` | 6 functions | Comment retrieval and management |
| `utilities` | 2 functions | Infrastructure and tool consolidation |

## Testing Coverage

The modular architecture enables comprehensive testing:
- **120 unit tests** across all 8 modules
- **Test categories**: Success scenarios, error handling, validation, integration
- **Coverage areas**: API error handling, workflow restrictions, parameter validation
- **Test organization**: One test file per module for focused testing

## Integration

The modular components are integrated through a unified `IssueTools` class that:
- Maintains backward compatibility with existing code
- Provides a clean delegation interface
- Consolidates tool definitions from all modules
- Enables seamless upgrades and maintenance

## Codebase Organization

The codebase is organized into logical modules:

```
youtrack_mcp/
├── api/                    # YouTrack API client implementations
│   ├── client.py          # Base HTTP client with authentication
│   ├── issues.py          # Issue operations (CRUD, search, linking)
│   ├── projects.py        # Project management operations
│   ├── search.py          # Search and query operations
│   └── users.py           # User management operations
├── tools/                 # MCP tool implementations
│   ├── issues/            # Modular issue management (8 modules)
│   ├── core_issues.py     # Core issue operations
│   ├── core_projects.py   # Project management
│   ├── core_search.py     # Search functionality
│   └── core_users.py      # User management
├── config.py              # Configuration management
├── utils.py               # Utility functions
└── mcp_server.py         # MCP server implementation
```

## Development Resources

For more information about the architecture and development:

- **[Refactoring Tracker](REFACTORING_TRACKER.md)**: Complete details of the modular architecture refactoring
- **[Testing Guide](tests/README.md)**: Comprehensive testing documentation
- **[Automation Scripts](automations/README.md)**: Build, test, and deployment automation

---

*This architecture provides a solid foundation for maintainable, testable, and scalable MCP server development.*