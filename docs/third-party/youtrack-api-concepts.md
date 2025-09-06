# YouTrack REST API Concepts

**Source**: https://www.jetbrains.com/help/youtrack/devportal/youtrack-rest-api.html  
**Extracted**: 2025-06-13

## Overview

The YouTrack REST API allows programmatic interaction with YouTrack for operations such as:
- Issue import, creation, and modification
- Project manipulation
- Custom field management
- Agile board operations
- Issue link type management

## Key Characteristics

### API Version
- **Current**: Uses `/api` prefix (new API)
- **Legacy**: `/rest` prefix (deprecated)
- **Data Format**: JSON for all data exchange

### Authentication
- **Required**: Authorization HTTP header is mandatory
- **Recommended Method**: Permanent token
- **Content Negotiation**: Supported

### Availability
- **Status**: Always enabled
- **Access Control**: Admin-configurable origin access

## Required Headers

### For All Requests
```http
Accept: application/json
Authorization: Bearer YOUR_PERMANENT_TOKEN
```

### For POST/PUT Requests
```http
Content-Type: application/json
Accept: application/json
Authorization: Bearer YOUR_PERMANENT_TOKEN
```

## Official Tools and Libraries

### YouTrackSharp
- **Type**: .NET library
- **Purpose**: Official .NET integration

### YouTrack Mobile App
- **Platform**: Mobile devices
- **Uses**: YouTrack REST API

### YouTrack Integration Plugin
- **Platform**: JetBrains IDEs
- **Purpose**: IDE integration with YouTrack

## Base URL Structure

The API uses the format:
```
https://your-youtrack-instance.com/api/[endpoint]
```

## Migration Notes

- Legacy REST API with `/rest` prefix is deprecated
- All new integrations should use the `/api` prefix
- JSON is the primary data exchange format
- Authentication is required for all operations

## Next Steps

For detailed endpoint documentation, authentication methods, and specific operation examples, refer to:
- Authentication documentation
- Endpoint reference
- Query language documentation
- Error handling patterns