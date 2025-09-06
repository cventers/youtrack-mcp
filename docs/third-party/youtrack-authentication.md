# YouTrack Authentication Methods

**Source**: https://www.jetbrains.com/help/youtrack/devportal/OAuth-authorization-in-youtrack.html  
**Extracted**: 2025-06-13

## Authentication Options

YouTrack supports two primary authentication methods:
1. **Permanent Token Authorization** (Recommended for most use cases)
2. **OAuth 2.0 Authorization** (For client-side applications)

## OAuth 2.0 Authentication

### When to Use OAuth 2.0
- Client-side authentication required
- User consent and delegation needed
- Public client applications
- **Note**: Only recommended when your application requires client-side authentication

### OAuth 2.0 Endpoints

#### Authentication Endpoint
```
<Hub service URL>/api/rest/oauth2/auth
```

#### Token Endpoint  
```
<Hub service URL>/api/rest/oauth2/token
```

### Authorization Request Parameters

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `response_type` | Yes | Must be "token" | `token` |
| `state` | Yes | Unique identifier for current app state | `abc123xyz` |
| `redirect_uri` | Yes | Client application URI for responses | `https://myapp.com/callback` |
| `request_credentials` | No | Login behavior control | `skip`, `silent`, `required`, `default` |
| `client_id` | Yes | YouTrack service ID from Hub | `service-id-123` |
| `scope` | Yes | Access scope | `YouTrack` |

### Authorization URL Example
```
https://hub.example.com/api/rest/oauth2/auth?response_type=token&state=abc123&redirect_uri=https://myapp.com/callback&client_id=service-id-123&scope=YouTrack
```

### Important OAuth 2.0 Limitations

#### Built-in Hub Service
- **Supported**: Implicit authorization grants only
- **Token Lifetime**: Default 1 hour (limited)
- **Refresh Tokens**: Not issued
- **Client Requirements**: Must be publicly available online

#### External Hub Installations
- **Supported**: Additional authorization methods available
- **Flexibility**: More configuration options

### Error Handling

OAuth 2.0 requests can return various error codes:
- Authorization errors at authentication endpoint
- Token errors at token endpoint
- Each error includes descriptive messages for debugging

## Permanent Token Authorization (Recommended)

### Advantages
- Simpler implementation
- No token expiration management
- Server-to-server authentication
- More secure for non-public clients

### Usage
```http
Authorization: Bearer YOUR_PERMANENT_TOKEN
```

### Token Management
- Generate tokens in YouTrack user profile
- Store tokens securely
- Use HTTPS for all requests
- Rotate tokens periodically

## Authentication Best Practices

### Security Considerations
1. **Always use HTTPS** for token transmission
2. **Store tokens securely** - never in client-side code
3. **Implement token rotation** for long-lived applications
4. **Use least privilege** - request minimal necessary scopes
5. **Handle token expiration** gracefully

### Error Handling
1. **401 Unauthorized**: Token invalid or expired
2. **403 Forbidden**: Insufficient permissions
3. **429 Rate Limited**: Too many requests

### Implementation Recommendations

#### For Server-to-Server Applications
```
✅ Use Permanent Token Authorization
❌ Avoid OAuth 2.0 complexity
```

#### For Client-Side Applications
```
✅ Use OAuth 2.0 with proper state management
✅ Handle token expiration
✅ Implement secure token storage
```

#### For MCP Servers
```
✅ Permanent Token Authorization (recommended)
✅ Environment variable token storage
✅ Lazy token loading for security
```

## Request Headers

### Required for All Authenticated Requests
```http
Authorization: Bearer YOUR_TOKEN
Accept: application/json
```

### For POST/PUT Requests
```http
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json
Accept: application/json
```

## Testing Authentication

### Verify Token Validity
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Accept: application/json" \
     https://your-youtrack.com/api/users/me
```

### Expected Response for Valid Token
```json
{
  "id": "user-id",
  "login": "username", 
  "fullName": "User Name",
  "email": "user@example.com"
}
```