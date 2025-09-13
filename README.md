# YouTrack MCP

A Model Context Protocol (MCP) server that provides access to YouTrack functionality through a streamlined 12-tool interface, built with a modern modular architecture for enhanced maintainability and scalability.

## 🚀 Core Tool Surface

The YouTrack MCP provides 12 core tools organized into 6 functional areas, implementing a minimal but powerful interface for YouTrack operations.

### **🔍 Search Tools**

#### `search.query`
Execute explicit YouTrack Query Language (YQL) searches.
```python
search.query(query="project: DEMO #Unresolved", limit=10, sort_by="created", sort_order="desc")
```
- **Parameters**: `query` (YQL string), `limit` (max results), `sort_by`, `sort_order`
- **Returns**: JSON with search results and metadata

#### `search.autosearch`
Translate natural language queries to YQL with confidence scoring.
```python
search.autosearch(natural_language_query="bugs assigned to me this week", project_context="DEMO")
```
- **Parameters**: `natural_language_query`, `project_context` (optional)
- **Returns**: YQL query, confidence score, search results, and translation notes

### **📋 Issues Tools**

#### `issues.get`
Rich issue read with optional expansions.
```python
issues.get(issue_id="DEMO-123", include=["customFields", "comments", "attachments", "links"])
```
- **Parameters**: `issue_id`, `include` (list of expansions)
- **Returns**: Full issue data with requested expansions

#### `issues.create`
Schema-aware issue creation with custom field support.
```python
issues.create(
    project="DEMO",
    summary="Bug report",
    description="Details...",
    custom_fields={"Type": "Bug", "Priority": "High"}
)
```
- **Parameters**: `project`, `summary`, `description` (optional), `custom_fields` (dict)
- **Returns**: Created issue data

#### `issues.patch`
Primary writer for issue updates with schema-aware coercion.
```python
# Using fields format (converted internally to ops)
issues.patch(issue_id="DEMO-123", fields={"summary": "New title", "Priority": "Critical"})

# Using ops format for advanced operations
issues.patch(issue_id="DEMO-123", ops=[
    {"op": "set", "path": "/fields/State", "value": "Fixed"},
    {"op": "set", "path": "/fields/Priority", "value": "High"}
])
```
- **Parameters**: `issue_id`, `fields` (dict) OR `ops` (list of operations)
- **Returns**: Updated issue data with operation results

### **🏗️ Projects Tools**

#### `projects.list`
Discover accessible projects.
```python
projects.list(include_archived=False)
```
- **Parameters**: `include_archived` (boolean)
- **Returns**: List of accessible projects

#### `projects.get`
Project details with optional expansions.
```python
projects.get(project_id="DEMO", include=["customFields", "schema", "issues"])
```
- **Parameters**: `project_id`, `include` (list of expansions)
- **Returns**: Full project data with requested expansions

#### `projects.schema`
Get project schema with custom fields and validation rules.
```python
projects.schema(project_id="DEMO")
```
- **Parameters**: `project_id`
- **Returns**: Custom field schemas, required/optional fields, usage guide

#### `projects.patch`
Project property updates with typed operations.
```python
projects.patch(project_id="DEMO", ops=[
    {"op": "set", "field": "name", "value": "New Name"},
    {"op": "set", "field": "description", "value": "Updated description"}
])
```
- **Parameters**: `project_id`, `ops` (list of operations)
- **Returns**: Updated project data

#### `projects.create`
Create new projects.
```python
projects.create(name="Demo Project", short_name="DEMO", lead_id="admin")
```
- **Parameters**: `name`, `short_name`, `lead_id`
- **Returns**: Created project data

### **👥 Users Tools**

#### `users.search`
Resolve users by name or login.
```python
users.search(query="admin", limit=10)
```
- **Parameters**: `query` (search term), `limit` (max results)
- **Returns**: List of matching users

### **🤖 AI Tools**

#### `ai.plan`
LLM-powered intent planning and analysis.
```python
ai.plan(intent="Create a bug report for login issues", context={"project": "DEMO"})
```
- **Parameters**: `intent` (natural language description), `context` (optional dict)
- **Returns**: Execution plan with suggested tools and explanations

### **📁 Resources Tools**

#### `resources.read`
Secured URI proxy for YouTrack resources and help documentation.
```python
# Read YouTrack resources
resources.read(uri="youtrack://issues/DEMO-123")
resources.read(uri="youtrack://projects/DEMO")
resources.read(uri="youtrack://users/admin")

# Access help documentation
resources.read(uri="help://issues.get")
```
- **Parameters**: `uri` (youtrack:// or help:// format)
- **Returns**: Resource content or help documentation

## 🚀 Quick Reference - Common Operations

### **🎯 State Transitions**
```python
# Update issue state using typed operations
issues.patch(issue_id="DEMO-123", ops=[{"op": "set", "field": "State", "value": "In Progress"}])
issues.patch(issue_id="PROJECT-456", ops=[{"op": "set", "field": "State", "value": "Fixed"}])
```

### **🚨 Priority Updates**
```python
# Update priority using typed operations
issues.patch(issue_id="DEMO-123", ops=[{"op": "set", "field": "Priority", "value": "Critical"}])
issues.patch(issue_id="PROJECT-456", ops=[{"op": "set", "field": "Priority", "value": "Major"}])
```

### **👤 Assignment Updates**
```python
# Update assignee using typed operations
issues.patch(issue_id="DEMO-123", ops=[{"op": "set", "field": "Assignee", "value": "admin"}])
issues.patch(issue_id="PROJECT-456", ops=[{"op": "set", "field": "Assignee", "value": "john.doe"}])
```

### **⏱️ Time Estimation**
```python
# Update estimation using typed operations
issues.patch(issue_id="DEMO-123", ops=[{"op": "set", "field": "Estimation", "value": "4h"}])
issues.patch(issue_id="PROJECT-456", ops=[{"op": "set", "field": "Estimation", "value": "2d"}])
```

### **⚡ Complete Workflows**
```python
# Triage workflow
issues.patch(issue_id="DEMO-123", ops=[
    {"op": "set", "field": "Type", "value": "Bug"},
    {"op": "set", "field": "Priority", "value": "Critical"},
    {"op": "set", "field": "Assignee", "value": "admin"},
    {"op": "set", "field": "Estimation", "value": "4h"},
    {"op": "set", "field": "State", "value": "In Progress"}
])

# Feature development workflow
projects.create(name="New Feature Project", short_name="FEATURE", lead_id="admin")
issues.create(project="FEATURE", summary="Implement dark mode", description="Add dark theme support")
issues.patch(issue_id="FEATURE-1", ops=[
    {"op": "set", "field": "Priority", "value": "Normal"},
    {"op": "set", "field": "Assignee", "value": "developer"}
])
```

### **🔍 Finding Issues**
```python
# YQL search
search.query(query="project: DEMO #Unresolved")

# Natural language search
search.autosearch(natural_language_query="bugs assigned to me this week")

# Get specific issue with expansions
issues.get(issue_id="DEMO-123", include=["customFields", "comments", "attachments"])
```

### **📋 Creating Issues**
```python
issues.create(
    project="DEMO",
    summary="Bug in login system",
    description="Users cannot log in with special characters"
)
```

### **📁 Resource Access**
```python
# Access issues
resources.read(uri="youtrack://issues/DEMO-123")

# Access projects
resources.read(uri="youtrack://projects/DEMO")

# Access users
resources.read(uri="youtrack://users/admin")

# Get help documentation
resources.read(uri="help://issues.get")
```

---

## Installation

[![Docker Build and Push](https://github.com/tonyzorin/youtrack-mcp/actions/workflows/docker-build.yml/badge.svg)](https://github.com/tonyzorin/youtrack-mcp/actions/workflows/docker-build.yml)

This project provides a Model Context Protocol (MCP) server for YouTrack, enabling seamless integration with Claude Desktop and other MCP clients.

## Quick Start

### Using Docker (Recommended)

Choose from multiple registries:

#### Docker Hub (Primary)
```bash
# Use the latest stable release
docker run --rm \
  -e YOUTRACK_URL="https://your-instance.youtrack.cloud" \
  -e YOUTRACK_API_TOKEN="your-token" \
  tonyzorin/youtrack-mcp:latest

# Or use the latest development build
docker run --rm \
  -e YOUTRACK_URL="https://your-instance.youtrack.cloud" \
  -e YOUTRACK_API_TOKEN="your-token" \
  tonyzorin/youtrack-mcp:1.1.2_wip
```

#### GitHub Container Registry (New)
```bash
# Use the latest stable release
docker run --rm \
  -e YOUTRACK_URL="https://your-instance.youtrack.cloud" \
  -e YOUTRACK_API_TOKEN="your-token" \
  ghcr.io/tonyzorin/youtrack-mcp:latest

# Or use the latest development build
docker run --rm \
  -e YOUTRACK_URL="https://your-instance.youtrack.cloud" \
  -e YOUTRACK_API_TOKEN="your-token" \
  ghcr.io/tonyzorin/youtrack-mcp:1.1.2_wip
```

### Available Docker Tags

Both registries provide identical tags:

- `latest` - Latest stable release (currently 1.1.2)
- `1.1.2` - Specific version tags  
- `1.1.2_wip` - Work-in-progress builds from main branch
- `pr-<number>` - Pull request builds for testing

*Note: Images are now published to both Docker Hub and GitHub Container Registry simultaneously.*

### Using npm Package

Choose from multiple registries:

#### npmjs.org (Primary)
```bash
# Install globally
npm install -g youtrack-mcp-tonyzorin

# Or use with npx (no installation required)
npx youtrack-mcp-tonyzorin
```

#### GitHub Packages (New)
```bash
# Configure GitHub registry
npm config set @tonyzorin:registry https://npm.pkg.github.com

# Install globally
npm install -g @tonyzorin/youtrack-mcp

# Or use with npx
npx @tonyzorin/youtrack-mcp
```

## Features

- **Issue Management**: Create, read, update, and delete YouTrack issues
- **Project Management**: Access project information and custom fields
- **Search Capabilities**: Advanced search with filters and custom fields
- **User Management**: Retrieve user information and permissions
- **Attachment Support**: Download and process issue attachments (up to 10MB)
- **Multi-Platform Support**: ARM64/Apple Silicon and AMD64 architecture support
- **Comprehensive API**: Full YouTrack REST API integration

## 🏗️ Architecture

The YouTrack MCP server features a modern, modular architecture designed for enhanced maintainability and scalability. See **[Architecture Documentation](docs/ARCHITECTURE.md)** for comprehensive details about the modular design, testing coverage, and development benefits.

## Development

This project maintains high code quality with comprehensive testing and CI/CD automation:

### Code Quality Metrics
- **Test Coverage**: 41% overall (continuously improving)
- **Modular Architecture**: 8 focused modules with 120+ unit tests
- **CI/CD Pipeline**: Automated testing and Docker builds
- **Quality Assurance**: Automated testing on every commit

### Development Resources

- **[Architecture Documentation](docs/ARCHITECTURE.md)**: Comprehensive modular architecture overview
- **[Automation Scripts Guide](automations/README.md)**: Build, test, and deployment automation
- **[Release Process](automations/RELEASE_INSTRUCTIONS.md)**: Version management and publishing
- **[Testing Guide](tests/README.md)**: Comprehensive testing documentation
- **[Refactoring Tracker](REFACTORING_TRACKER.md)**: Details of the modular architecture refactoring

## Configuration

### Environment Variables

- `YOUTRACK_URL`: Your YouTrack instance URL
- `YOUTRACK_API_TOKEN`: Your YouTrack API token
- `YOUTRACK_VERIFY_SSL`: SSL verification (default: true)

### Example Configuration

```bash
export YOUTRACK_URL="https://prodcamp.youtrack.cloud/"
export YOUTRACK_API_TOKEN="perm-YWRtaW4=.NDMtMg==.JgbpvnDbEu7RSWwAJT6Ab3iXgQyPwu"
export YOUTRACK_VERIFY_SSL="true"
```

## Documentation

### Architecture & Development
- [Architecture Documentation](docs/ARCHITECTURE.md) - Comprehensive modular architecture overview
- [Refactoring Tracker](REFACTORING_TRACKER.md) - Modular architecture implementation details
- [Development Workflow & Release Process](automations/RELEASE_INSTRUCTIONS.md)
- [Docker Tagging Strategy](automations/DOCKER_TAGGING.md)
- [Testing Guide](tests/README.md)
- [Automation Scripts](automations/README.md)

### API Integration
- [YouTrack API Concepts](docs/third-party/youtrack-api-concepts.md)
- [Authentication Guide](docs/third-party/youtrack-authentication.md)
- [Query Language Reference](docs/third-party/youtrack-query-language.md)
- [Custom Fields Guide](docs/third-party/youtrack-custom-fields.md)

## Support

For issues and questions:
1. Check the [Issues](https://github.com/tonyzorin/youtrack-mcp/issues) page
2. Review the documentation
3. Submit a new issue with detailed information
4. Contact directly: [t.me/tonyzorin](https://t.me/tonyzorin)

---

*Latest update: Modular architecture refactoring with 120+ unit tests and enhanced maintainability.*

## Version 1.17.2 Released

🎉 **LATEST RELEASE** - Enhanced Stability and Performance
- ✅ **Modular Architecture**: 8 focused modules with 120+ unit tests
- ✅ **Async Migration Complete**: Full httpx.AsyncClient implementation
- ✅ **MCP Compliance**: Full MCP protocol compliance with Claude Code CLI
- ✅ **Enhanced Error Handling**: LLM-optimized error responses with educational context
- ✅ **Custom Fields Support**: Complete CRUD operations for all field types
- ✅ **Activity Tracking**: User activity search and analysis capabilities
- ✅ **Performance Optimization**: Multi-layer caching and rate limiting
- ✅ **Security Hardening**: Token management and input validation

### Architecture Highlights
- **8 Focused Modules**: Clean separation of concerns with single-responsibility design
- **120+ Unit Tests**: Comprehensive test coverage across all modules
- **Async-First**: Full async/await implementation with httpx.AsyncClient
- **LLM-Optimized**: Error messages designed to help AI models learn and improve
- **Multi-Registry Support**: Docker Hub, GitHub Container Registry, npm registries

### Core Features
- **Issue Management**: Complete CRUD operations with custom fields support
- **Project Management**: Schema-aware operations with field validation
- **Search Capabilities**: YQL queries with natural language translation
- **User Management**: Activity tracking and permission management
- **Resource Access**: MCP resources for documentation and configuration
- **AI Integration**: Planning tools and intelligent error handling
