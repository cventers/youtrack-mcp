# YouTrack Custom Fields API Documentation

**Source**: https://www.jetbrains.com/help/youtrack/devportal/api-concept-custom-fields.html  
**Extracted**: 2025-06-13

## Core Custom Field Entities

### 1. CustomField
- **Purpose**: Defines the basic field attributes and settings across projects
- **Scope**: Global field definition
- **Contains**: Field name, type, and global configuration

### 2. ProjectCustomField  
- **Purpose**: Contains field-specific settings for a particular project
- **Scope**: Project-specific configuration
- **Contains**: Field bundle (values), canBeEmpty flag, project reference
- **Relationship**: Links CustomField to specific project with project-specific settings

### 3. IssueCustomField
- **Purpose**: Represents the actual field value within a specific issue
- **Scope**: Issue-specific value
- **Contains**: Field value, reference to ProjectCustomField
- **Relationship**: Contains the actual data for a custom field in an issue

## Custom Field Types

### Enum Fields
- **Single Enum**: `SingleEnumIssueCustomField` / `EnumProjectCustomField`
- **Multi Enum**: `MultiEnumIssueCustomField` / `EnumProjectCustomField`
- **Use Case**: Dropdown selections, multiple choice options
- **Value Structure**: Links to bundle elements

### User/Group Fields
- **Single User**: `SingleUserIssueCustomField` / `UserProjectCustomField`
- **Multi User**: `MultiUserIssueCustomField` / `UserProjectCustomField`
- **Single Group**: `SingleGroupIssueCustomField` / `GroupProjectCustomField`
- **Multi Group**: `MultiGroupIssueCustomField` / `GroupProjectCustomField`
- **Use Case**: Assignee fields, reviewer lists, team assignments

### State Fields
- **Type**: `StateIssueCustomField` / `StateProjectCustomField`
- **Bundle**: Uses StateBundle with StateBundleElement values
- **Use Case**: Workflow states, approval status

### Numeric Fields
- **Integer**: `SimpleIssueCustomField` (integer type)
- **Float**: `SimpleIssueCustomField` (float type)
- **Use Case**: Estimates, ratings, counts

### Date/Time Fields
- **Date**: `DateIssueCustomField` / `DateProjectCustomField`
- **Date Time**: `DateTimeIssueCustomField` / `DateTimeProjectCustomField`
- **Use Case**: Due dates, timestamps, milestones

### Text Fields
- **Simple Text**: `TextIssueCustomField` / `TextProjectCustomField`
- **Use Case**: Short descriptions, identifiers

### Build/Version Fields
- **Build**: `BuildIssueCustomField` / `BuildProjectCustomField`
- **Version**: `VersionIssueCustomField` / `VersionProjectCustomField`
- **Use Case**: Release tracking, version assignment

### Owned Fields
- **Type**: `SingleOwnedIssueCustomField` / `OwnedProjectCustomField`
- **Use Case**: Subsystems, components with ownership

## API Endpoints

### Get All Custom Fields (Global)
```
GET /api/admin/customFieldSettings/customFields
```
- **Purpose**: Retrieve all global custom field definitions
- **Returns**: List of CustomField entities

### Get Project Custom Fields
```
GET /api/admin/projects/{projectId}/customFields
```
- **Purpose**: Get all custom fields configured for a specific project
- **Returns**: List of ProjectCustomField entities with project-specific settings

### Get Issue Custom Field Value
```
GET /api/issues/{issueId}/customFields/{fieldId}
```
- **Purpose**: Get the value of a specific custom field in an issue
- **Returns**: IssueCustomField entity with current value

### Get All Issue Custom Fields
```
GET /api/issues/{issueId}/customFields
```
- **Purpose**: Get all custom field values for an issue
- **Returns**: List of IssueCustomField entities

## Field Parameters and Attributes

### Fields Parameter
By default, YouTrack returns only the `$type` attribute. To get comprehensive information:

```
?fields=id,name,localizedName,fieldType,isPublic,bundle(id,name,values(id,name))
```

### Common Attributes
- `id`: Unique field identifier
- `name`: Field name
- `localizedName`: Display name
- `fieldType`: Type information
- `isPublic`: Visibility flag
- `bundle`: Value bundle for enum/selection fields

## Value Structure Examples

### Single Enum Field Value
```json
{
  "$type": "SingleEnumIssueCustomField",
  "id": "field-id",
  "value": {
    "$type": "EnumBundleElement", 
    "id": "value-id",
    "name": "High Priority"
  }
}
```

### User Field Value
```json
{
  "$type": "SingleUserIssueCustomField",
  "id": "field-id", 
  "value": {
    "$type": "User",
    "id": "user-id",
    "login": "john.doe",
    "fullName": "John Doe"
  }
}
```

### Date Field Value
```json
{
  "$type": "DateIssueCustomField",
  "id": "field-id",
  "value": 1640995200000
}
```

### Text Field Value
```json
{
  "$type": "TextIssueCustomField", 
  "id": "field-id",
  "value": "Custom text value"
}
```

## Authentication and Headers

### Required Headers
```http
Authorization: Bearer YOUR_PERMANENT_TOKEN
Accept: application/json
```

### For Updates (POST/PUT)
```http
Authorization: Bearer YOUR_PERMANENT_TOKEN
Content-Type: application/json
Accept: application/json
```

## Best Practices

### 1. Field Type Validation
- Always check `$type` to determine field type
- Handle different value structures appropriately
- Validate field types match expected project configuration

### 2. Bundle Handling
- For enum fields, validate values against bundle elements
- Cache bundle values for performance
- Handle bundle updates gracefully

### 3. Null Value Handling
- Check `canBeEmpty` flag in ProjectCustomField
- Handle null/undefined values appropriately
- Distinguish between null and empty string values

### 4. Performance Optimization
- Use specific field parameters to limit response size
- Cache field definitions when possible
- Batch field operations when updating multiple fields

## Error Scenarios

### Common Issues
1. **Field not found**: Invalid field ID or field not available in project
2. **Invalid value type**: Value doesn't match field type constraints
3. **Bundle constraint violation**: Value not in allowed bundle elements
4. **Permission denied**: User lacks field modification permissions
5. **Required field empty**: Attempting to set empty value on required field

### Error Response Example
```json
{
  "error": "Bad Request",
  "error_description": "Field value is not valid for this field type"
}
```