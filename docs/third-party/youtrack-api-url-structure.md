# YouTrack REST API URL Structure and Endpoints

**Source**: https://www.jetbrains.com/help/youtrack/devportal/api-url-and-endpoints.html  
**Extracted**: 2025-06-13

## Base URL Structure

### YouTrack Server Installations
```
{YouTrack-Service-URL}/api
```

**Examples:**
- `https://www.example.com/youtrack/api`
- `https://youtrack.example.com/api`

### YouTrack Cloud Installations
```
{YouTrack-Service-URL}/api
{YouTrack-Service-URL}/youtrack/api
```

**Examples:**
- `https://example.youtrack.cloud/api`
- `https://example.myjetbrains.com/youtrack/api`

## Standard Endpoint Pattern

All YouTrack REST API endpoints follow the pattern:
```
{base-url}/api/{resource}
```

### Example Standard Endpoints
- **Current user profile**: `{base-url}/api/users/me`
- **Issues**: `{base-url}/api/issues`
- **Projects**: `{base-url}/api/admin/projects`
- **Users**: `{base-url}/api/admin/users`

## Custom Endpoints

YouTrack supports custom endpoints added via HTTP Handlers with the pattern:
```
{host}/api/{scope}/extensionEndpoints/app/handler/endpoint
```

### Supported Scopes
- **issue**: Issue-specific endpoints
- **article**: Article-specific endpoints  
- **project**: Project-specific endpoints
- **user**: User-specific endpoints
- **global**: Global endpoints (accessible to most users)

### Permissions
- Each custom endpoint requires permissions matching its scope
- Global endpoints have the broadest access
- Endpoints can be extended through app installations

## Authentication Context

All endpoints require proper authentication through:
- Permanent tokens (recommended)
- OAuth 2.0 authentication
- Authorization header required for all requests

## Migration Notes

- Legacy `/rest` prefix is deprecated (discontinued February 17, 2021)
- All new integrations must use `/api` prefix
- URLs are case-sensitive
- Always use HTTPS in production environments