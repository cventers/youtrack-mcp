# YouTrack MCP

A Model Context Protocol (MCP) server that provides access to YouTrack functionality through a streamlined 12-tool interface, built with a modern modular architecture for enhanced maintainability and scalability.

## 🚀 Core Tool Surface

The YouTrack MCP provides 12 core tools organized into 6 functional areas:

### **🔍 Search Tools**
```python
# Execute YouTrack Query Language (YQL)
search.query(query="project: DEMO #Unresolved", limit=10)

# Natural language to YQL translation with confidence scoring
search.autosearch(natural_language_query="bugs assigned to me this week")
```

### **📋 Issues Tools** (Modular Architecture)
```python
# Get issue with optional expansions
issues.get(issue_id="DEMO-123", include=["customFields", "comments"])

# Create new issue
issues.create(project="DEMO", summary="Bug report", description="Details...")

# Update issue with typed operations
issues.patch(issue_id="DEMO-123", ops=[{"op": "set", "field": "state", "value": "Fixed"}])

# Modular operations available:
# - Custom fields management (validation, batch updates)
# - Dedicated updates (state, priority, assignee, type, estimation)
# - Issue linking and dependencies
# - Workflow diagnostics and help
# - Attachment and comment operations
```

### **🏗️ Projects Tools**
```python
# List accessible projects
projects.list(include_archived=False)

# Get project details
projects.get(project_id="DEMO", include=["customFields"])

# Update project properties
projects.patch(project_id="DEMO", ops=[{"op": "set", "field": "name", "value": "New Name"}])

# Create new project
projects.create(name="Demo Project", short_name="DEMO", lead_id="admin")
```

### **👥 Users Tools**
```python
# Search users by name or login
users.search(query="admin", limit=10)
```

### **🤖 AI Tools**
```python
# Plan user intent actions
ai.plan(intent="Create a bug report for login issues", context={"project": "DEMO"})
```

### **📁 Resources Tools**
```python
# Read YouTrack resources by URI
resources.read(uri="youtrack://issues/DEMO-123")

# Access help documentation
resources.read(uri="help://issues.get")
```

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
