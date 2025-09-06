# YouTrack Commands API Documentation

**Source**: https://www.jetbrains.com/help/youtrack/devportal/api-usecase-commands.html  
**Extracted**: 2025-06-13

## Overview

The YouTrack Commands API allows you to perform operations with one or several issues much faster and easier than individual API calls. It uses the same command syntax as the YouTrack UI.

## API Endpoint

```
POST /api/commands
```

## Required Permissions

- **Update Issue** permissions for targeted issues
- Commands will only apply to issues where user has appropriate permissions

## Request Structure

### Basic Request Format
```json
{
  "query": "command_syntax",
  "issues": [
    {"idReadable": "PROJECT-123"},
    {"idReadable": "PROJECT-124"}
  ]
}
```

### Full Request Options
```json
{
  "query": "command_syntax",
  "issues": [
    {"idReadable": "PROJECT-123"}
  ],
  "comment": "Optional comment text",
  "silent": false,
  "visibilityGroup": "group_name"
}
```

## Command Syntax Examples

### Basic Status Changes
```json
{
  "query": "Fixed",
  "issues": [{"idReadable": "PROJECT-123"}]
}
```

### Assignment Commands
```json
{
  "query": "for john.doe",
  "issues": [
    {"idReadable": "PROJECT-123"},
    {"idReadable": "PROJECT-124"}
  ]
}
```

### Multiple Commands Combined
```json
{
  "query": "for jane.doe Fixed",
  "issues": [{"idReadable": "PROJECT-123"}]
}
```

### Priority and Type Updates
```json
{
  "query": "Priority Critical Type Bug",
  "issues": [{"idReadable": "PROJECT-123"}]
}
```

### Tag Operations
```json
{
  "query": "tag Important tag {Ready for testing}",
  "issues": [{"idReadable": "PROJECT-123"}]
}
```

### Custom Field Updates
```json
{
  "query": "{Fix Version} 2024.1 {Component} Backend",
  "issues": [{"idReadable": "PROJECT-123"}]
}
```

### Remove Operations
```json
{
  "query": "remove tag Important",
  "issues": [{"idReadable": "PROJECT-123"}]
}
```

## Advanced Options

### Silent Commands
Suppress notifications for bulk operations:
```json
{
  "query": "{Fix Version} 2024.1",
  "issues": [
    {"idReadable": "PROJECT-123"},
    {"idReadable": "PROJECT-124"}
  ],
  "silent": true
}
```

### Comments with Visibility Groups
Add comments with restricted visibility:
```json
{
  "query": "for john.doe tag Important",
  "issues": [{"idReadable": "PROJECT-123"}],
  "comment": "Assigned for review",
  "visibilityGroup": "Developers"
}
```

### Bulk Operations
Apply to multiple issues efficiently:
```json
{
  "query": "State {In Progress} Priority High",
  "issues": [
    {"idReadable": "PROJECT-100"},
    {"idReadable": "PROJECT-101"}, 
    {"idReadable": "PROJECT-102"},
    {"idReadable": "PROJECT-103"}
  ]
}
```

## Issue Identification

### Human-Readable IDs (Recommended)
```json
{"idReadable": "PROJECT-123"}
```

### Database IDs
```json
{"id": "2-123"}
```

### Mixed Identification
```json
{
  "issues": [
    {"idReadable": "PROJECT-123"},
    {"id": "2-124"}
  ]
}
```

## Response Format

### Successful Command
```json
{
  "preview": {
    "issues": [
      {
        "id": "2-123",
        "idReadable": "PROJECT-123"
      }
    ]
  }
}
```

### Command with Errors
```json
{
  "preview": {
    "issues": [...],
    "errors": [
      {
        "error": "Command failed: Invalid state transition"
      }
    ]
  }
}
```

## Common Command Patterns

### Issue Linking
```json
{
  "query": "relates to PROJECT-124",
  "issues": [{"idReadable": "PROJECT-123"}]
}
```

### Dependency Creation
```json
{
  "query": "depends on PROJECT-125",
  "issues": [{"idReadable": "PROJECT-123"}]
}
```

### Link Removal
```json
{
  "query": "remove relates to PROJECT-124",
  "issues": [{"idReadable": "PROJECT-123"}]
}
```

### Time Tracking
```json
{
  "query": "spent 2h 30m",
  "issues": [{"idReadable": "PROJECT-123"}]
}
```

## Error Handling

### Permission Errors
- Commands fail silently for issues where user lacks permissions
- Partial success possible when applying to multiple issues

### Syntax Errors
- Invalid command syntax returns error details
- Specific field validation errors are returned

### Field Validation
- Custom field names must be exact (case-sensitive)
- Field values must be valid for field type
- Bundle values must exist for enum fields

## Best Practices

### 1. Batch Similar Operations
```json
{
  "query": "Priority High Type Bug for john.doe",
  "issues": [
    {"idReadable": "BUG-100"},
    {"idReadable": "BUG-101"},
    {"idReadable": "BUG-102"}
  ]
}
```

### 2. Use Silent Mode for Bulk Updates
```json
{
  "query": "{Fix Version} 2024.2",
  "issues": [...],
  "silent": true
}
```

### 3. Add Descriptive Comments
```json
{
  "query": "State Fixed",
  "issues": [...],
  "comment": "Fixed in build 2024.2.1"
}
```

### 4. Handle Partial Failures
- Check response for individual issue results
- Retry failed operations with corrected syntax
- Log successful operations for audit trail

## Authentication and Headers

### Required Headers
```http
Authorization: Bearer YOUR_PERMANENT_TOKEN
Content-Type: application/json
Accept: application/json
```

### Example cURL Request
```bash
curl -X POST \
  https://your-youtrack.com/api/commands \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "for john.doe Priority High",
    "issues": [{"idReadable": "PROJECT-123"}]
  }'
```

## Performance Considerations

- **Bulk Operations**: Much faster than individual API calls
- **Silent Mode**: Reduces notification overhead
- **Batch Size**: Reasonable batch sizes (50-100 issues) for optimal performance
- **Field Validation**: Commands validate fields server-side, reducing client complexity