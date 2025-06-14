# Third-Party Documentation Index

This directory contains cached copies and extracts from official YouTrack API documentation and related resources that are essential for building and maintaining the YouTrack MCP server.

## Documentation Sources

### YouTrack REST API Documentation
- **URL**: https://www.jetbrains.com/help/youtrack/devportal/youtrack-rest-api.html
- **Title**: YouTrack REST API Documentation
- **Summary**: Official JetBrains documentation for YouTrack REST API concepts, authentication, and endpoint reference
- **Status**: ✅ Extracted
- **Local Files**: 
  - [x] `youtrack-api-concepts.md` - Core API concepts and patterns
  - [x] `youtrack-authentication.md` - Authentication methods and token management
  - [x] `youtrack-api-url-structure.md` - URL structure and endpoint patterns
  - [x] `youtrack-getting-started.md` - Getting started guide and best practices
  - [x] `youtrack-query-language.md` - YouTrack Query Language (YQL) syntax
  - [x] `youtrack-custom-fields.md` - Custom field types and handling
  - [x] `youtrack-commands-api.md` - Commands API for bulk operations
  - [x] `youtrack-error-handling.md` - Error response patterns and handling

### YouTrack Command API Documentation
- **URL**: https://www.jetbrains.com/help/youtrack/devportal/api-usecase-commands.html
- **Title**: YouTrack Commands API
- **Summary**: Documentation for YouTrack's command-based operations for bulk updates and workflow automation
- **Status**: ✅ Extracted
- **Local Files**:
  - [x] `youtrack-commands-api.md` - Command syntax and execution with examples

### YouTrack Query Language Reference
- **URL**: https://www.jetbrains.com/help/youtrack/devportal/api-query-syntax.html
- **Title**: YouTrack Query Language Reference
- **Summary**: Complete reference for YQL syntax, operators, and field references
- **Status**: ✅ Extracted
- **Local Files**:
  - [x] `youtrack-query-language.md` - Complete YQL syntax reference with examples

### YouTrack Custom Fields Documentation
- **URL**: https://www.jetbrains.com/help/youtrack/devportal/api-concept-custom-fields.html
- **Title**: YouTrack Custom Fields
- **Summary**: Documentation for custom field types, configuration, and API handling
- **Status**: ✅ Extracted
- **Local Files**:
  - [x] `youtrack-custom-fields.md` - All custom field types and their properties

### YouTrack Error Handling and Status Codes
- **URL**: https://www.jetbrains.com/help/youtrack/devportal/api-troubleshooting.html
- **Title**: YouTrack API Error Handling
- **Summary**: Error response formats, HTTP status codes, and error recovery patterns
- **Status**: ✅ Extracted
- **Local Files**:
  - [x] `youtrack-error-handling.md` - Error response patterns and handling

## Extraction Status

### ✅ Completed Extractions
1. **YouTrack API Concepts** - Core API patterns, authentication, URL structure
2. **YouTrack Query Language** - Complete YQL syntax reference with examples  
3. **YouTrack Custom Fields** - All field types, API endpoints, value structures
4. **YouTrack Commands API** - Bulk operations, command syntax, practical examples
5. **YouTrack Error Handling** - HTTP status codes, error patterns, troubleshooting

### 🔄 Additional Extractions Needed
1. **YouTrack Activities API** - Issue history and activity tracking (for TODO.md Phase 4)
2. **YouTrack Issue Search** - Advanced search patterns and pagination
3. **YouTrack Project Management** - Project configuration and management APIs

## Extraction Coverage

**Primary Use Cases Covered:**
- ✅ Authentication and API basics
- ✅ Query language syntax and examples
- ✅ Custom field handling (all types)
- ✅ Bulk operations via Commands API
- ✅ Error handling and troubleshooting

**Secondary Use Cases (Future):**
- ⏳ Activity tracking for user analysis
- ⏳ Advanced project management
- ⏳ Workflow automation patterns

## Usage Notes

- All extracted documentation should preserve original structure and examples
- Include URL references and extraction dates for version tracking
- Focus on API patterns and examples most relevant to MCP implementation
- Maintain markdown format for easy reading and searching
- Include code examples and response formats where available

## Last Updated
Created: 2025-06-13