# YouTrack REST API Error Handling

**Source**: https://www.jetbrains.com/help/youtrack/devportal/api-troubleshooting.html  
**Extracted**: 2025-06-13

## Overview

YouTrack REST API provides detailed error responses to help developers troubleshoot integration issues. Errors include specific HTTP status codes and descriptive error messages.

## Common HTTP Status Codes

### 400 Bad Request
**Scenarios:**
- Adding custom field value to a set with incorrect entity ID
- Creating issues without required field values  
- Updating conditional fields incorrectly
- Invalid query syntax in search requests
- Malformed request body or parameters

**Example Response:**
```json
{
  "error": "Bad Request",
  "error_description": "Entity id refers to entity of wrong type",
  "error_field": "value",
  "error_developer_message": "Value is not allowed"
}
```

### 401 Unauthorized
**Scenarios:**
- Missing or invalid authentication token
- Expired token
- Invalid authorization header format

**Example Response:**
```json
{
  "error": "Unauthorized", 
  "error_description": "Invalid authentication credentials"
}
```

### 403 Forbidden  
**Scenarios:**
- Insufficient permissions for requested operation
- Access denied to specific project or issue
- User lacks required role for administrative operations

**Example Response:**
```json
{
  "error": "Forbidden",
  "error_description": "Access denied"
}
```

### 404 Not Found
**Scenarios:**
- Issue, project, or user does not exist
- Invalid endpoint URL
- Resource deleted or moved

**Example Response:**
```json
{
  "error": "Not Found",
  "error_description": "Issue not found"
}
```

### 500 Internal Server Error
**Scenarios:**
- Updating custom field with incorrect field type
- Adding field to project with configuration conflicts
- Server-side processing errors
- Database constraint violations

**Example Response:**
```json
{
  "error": "Internal Server Error",
  "error_description": "Cannot cast field value to required type"
}
```

## Error Response Format

### Standard Error Structure
```json
{
  "error": "Error Type",
  "error_description": "Detailed error description",
  "error_field": "field_name",
  "error_developer_message": "Technical details for developers"
}
```

### Query Syntax Errors
```json
{
  "error": "Bad Request",
  "error_description": "Invalid query: project name 'INVALID' not found",
  "query": "project: INVALID",
  "suggested_fix": "Use valid project name or check project list"
}
```

### Field Validation Errors
```json
{
  "error": "Bad Request", 
  "error_description": "Field 'Priority' is required",
  "error_field": "Priority",
  "available_values": ["Critical", "High", "Normal", "Low"]
}
```

## Troubleshooting Guidelines

### 1. Authentication Errors (401)
- Verify token is valid and not expired
- Check authorization header format: `Bearer YOUR_TOKEN`
- Ensure token has required permissions

### 2. Permission Errors (403)
- Check user has appropriate project access
- Verify user role supports requested operation
- Confirm administrative permissions for admin endpoints

### 3. Resource Not Found (404)
- Validate resource IDs (issues, projects, users)
- Check spelling and case sensitivity
- Ensure resources haven't been deleted

### 4. Bad Request Errors (400)
- Validate request body JSON format
- Check required fields are present
- Verify field values match expected types
- Validate query syntax for search requests

### 5. Server Errors (500)
- Check field types match project configuration
- Validate custom field constraints
- Review request for data conflicts
- Contact support for persistent server errors

## Best Practices for Error Handling

### 1. Parse Error Responses
```python
try:
    response = requests.post(url, json=data, headers=headers)
    response.raise_for_status()
except requests.HTTPError as e:
    error_data = response.json()
    error_type = error_data.get('error')
    error_desc = error_data.get('error_description')
    # Handle specific error types
```

### 2. Implement Retry Logic
```python
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configure retry strategy
retry_strategy = Retry(
    total=3,
    status_forcelist=[429, 500, 502, 503, 504],
    backoff_factor=1
)
```

### 3. Log Error Details
```python
import logging

def handle_api_error(response):
    error_data = response.json()
    logging.error(f"YouTrack API Error: {error_data.get('error')}")
    logging.error(f"Description: {error_data.get('error_description')}")
    logging.error(f"Field: {error_data.get('error_field', 'N/A')}")
```

### 4. Provide User-Friendly Messages
```python
def convert_api_error_to_user_message(error_data):
    error_type = error_data.get('error')
    
    if error_type == 'Bad Request':
        return f"Invalid request: {error_data.get('error_description')}"
    elif error_type == 'Unauthorized':
        return "Authentication failed. Please check your credentials."
    elif error_type == 'Forbidden':
        return "You don't have permission to perform this action."
    elif error_type == 'Not Found':
        return "The requested resource was not found."
    else:
        return "An unexpected error occurred. Please try again."
```

## Rate Limiting

### Response Headers
YouTrack may include rate limiting headers:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1640995200
```

### 429 Too Many Requests
```json
{
  "error": "Too Many Requests",
  "error_description": "Rate limit exceeded",
  "retry_after": 60
}
```

## Field-Specific Error Patterns

### Custom Field Errors
- **Type Mismatch**: Value doesn't match field type
- **Bundle Validation**: Value not in allowed bundle elements
- **Required Field**: Missing value for required field
- **Permission**: User cannot modify field

### Query Syntax Errors  
- **Invalid Project**: Project name doesn't exist
- **Invalid Field**: Field name not recognized
- **Invalid Operator**: Unsupported query operator
- **Date Format**: Invalid date format in query

### Command Errors
- **Invalid Command**: Command syntax not recognized
- **State Transition**: Invalid workflow state change
- **Field Value**: Value not valid for field type
- **Permission**: User cannot execute command