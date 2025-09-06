# YouTrack MCP Server Project Overview

## Purpose
YouTrack MCP server provides Model Context Protocol (MCP) integration for JetBrains YouTrack, enabling seamless interaction with YouTrack's issue tracking, project management, and user management features through natural language commands.

## Tech Stack
- **Language**: Python 3.8+
- **Framework**: MCP SDK (Model Context Protocol)
- **API Client**: Custom YouTrack REST API client
- **Architecture**: Modular tool-based design with separate API and tool layers

## Code Structure
- `youtrack_mcp/api/`: REST API client implementations
- `youtrack_mcp/tools/`: MCP tool implementations organized by functionality
- `youtrack_mcp/`: Core server and configuration files

## Current Tool Surface Analysis
**Total Tools**: ~60+ tools across multiple modules
- **Issues**: 25+ tools (CRUD, custom fields, linking, attachments, comments)
- **Search**: 3 tools (advanced search, custom field search, filter search)
- **Projects**: 12 tools (project management, custom fields, subsystems)
- **Users**: 4 tools (user lookup and permissions)
- **AI**: 4 tools (natural language processing)
- **Resources**: 15+ tools (MCP resource protocol implementation)

## Key Problems Identified
1. **Context Bloat**: Too many tools with long docstrings
2. **Inconsistent Design**: Mixed naming conventions and parameter handling
3. **No Safety Measures**: Missing validation and error handling
4. **Complex Parameter Handling**: Inconsistent parameter formats
5. **No Schema Validation**: Missing type safety and validation

## Development Commands
- **Testing**: `pytest` (41% coverage currently)
- **Linting**: Standard Python linting tools
- **Building**: Docker-based build system
- **CI/CD**: GitHub Actions with automated testing

## Testing Strategy
- Unit tests for individual components
- Integration tests for API interactions
- End-to-end tests for full workflows
- Docker-based testing environment

## Quality Metrics
- Test Coverage: 41% (target: improve to 80%+)
- Code Quality: PEP8/PEP20 compliance
- Documentation: Inline docstrings and README
- CI/CD: Automated testing and Docker builds