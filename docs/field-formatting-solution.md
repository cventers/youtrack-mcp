# YouTrack MCP Field Formatting Solution

## Overview
This document describes the unified custom field formatting solution implemented to fix "Incompatible field type" errors in YouTrack MCP.

## Problem Statement
YouTrack REST API requires specific `$type` discriminators for custom fields based on their actual field types. Without proper formatting, the API returns errors like:
- "Incompatible field type: 65-2"
- "Incompatible value format for type date"
- "Incompatible field type: 64-102"

## Solution Architecture

### 1. Unified Formatting Method
Created `format_custom_fields_for_api()` in `youtrack_mcp/api/issues.py`:

```python
async def format_custom_fields_for_api(
    self,
    custom_fields: Dict[str, Any],
    project_id: Optional[str] = None,
    issue_id: Optional[str] = None
) -> List[Dict[str, Any]]:
```

This method:
- Fetches and caches project schema
- Formats ALL fields using schema-aware formatting
- Returns properly formatted list with correct `$type` discriminators
- Used by both create and update operations

### 2. Schema-Based Field Formatting
The `_format_custom_field_with_schema()` method handles field-specific formatting:

```python
def _format_custom_field_with_schema(
    self,
    field_name: str,
    field_value: Any,
    field_schema: Dict[str, Any]
) -> Dict[str, Any]:
```

#### Field Type Handling

##### Date Fields
- **Problem**: Date strings like "2025-10-25" were rejected
- **Solution**: Convert to Unix timestamps in milliseconds
- **Formats supported**:
  - YYYY-MM-DD
  - ISO 8601 (YYYY-MM-DDTHH:MM:SS)
  - YYYY-MM-DDTHH:MM:SSZ
  - Unix timestamps

```python
if field_type == "date":
    custom_field["$type"] = "DateIssueCustomField"
    # Convert string dates to timestamps
    dt = datetime.strptime(value, date_format)
    custom_field["value"] = int(dt.timestamp() * 1000)
```

##### Multi-Value Enum Fields
- **Problem**: Fields with `bundle_id: "enum[*]"` were incorrectly detected as single-value
- **Solution**:
  1. Detect asterisk pattern in bundle_id as multi-value indicator
  2. Format values as array of objects with proper type

```python
# Detection
if "[*]" in bundle_id_str:
    is_multi_value = True

# Formatting
if is_multi_value:
    custom_field["$type"] = "MultiEnumIssueCustomField"
    custom_field["value"] = [{
        "$type": "EnumBundleElement",
        "name": field_value
    }]
```

##### User Fields
- Single user: `SingleUserIssueCustomField`
- Multi-user: `MultiUserIssueCustomField`
- Value format: `{"$type": "User", "login": username}`

##### State Fields
- Type: `StateIssueCustomField`
- Value format: `{"$type": "StateBundleElement", "name": state_name}`

##### Period Fields
- Type: `PeriodIssueCustomField`
- Value: Number in minutes

### 3. Schema Caching
Project schemas are cached to avoid repeated API calls:

```python
_schema_cache = {}  # project_id -> schema dict

async def _get_project_schema(self, project_id: str) -> Dict[str, Any]:
    if project_id in self._schema_cache:
        return self._schema_cache[project_id]

    # Fetch and cache schema
    schema = await fetch_from_api()
    self._schema_cache[project_id] = schema
    return schema
```

### 4. Fallback Formatting
When schema is unavailable, uses field name heuristics:

```python
def _format_custom_fields_simple(self, custom_fields: Dict[str, Any]):
    # Uses field name patterns to guess types
    if 'date' in field_name.lower():
        field_type = "DateIssueCustomField"
    elif field_name.lower() in ['priority', 'type']:
        field_type = "SingleEnumIssueCustomField"
    # etc...
```

## Key Improvements

### 1. Multi-Value Field Detection
Enhanced field schema detection to recognize multi-value fields based on:
- `isMultiValue` property from API
- Bundle ID pattern `[*]` (e.g., `enum[*]`, `user[*]`)

### 2. Proper API Endpoint for Multi-Value Enums
When bundle_id contains asterisk, fetch values via field instance:
```python
if actual_bundle_id == "*":
    # Use field instance endpoint instead of bundle endpoint
    field_url = f"admin/projects/{project_id}/customFields/{field_name}"
```

### 3. Consistent Formatting
All issue operations now use the same formatting logic:
- `create_issue()` → Uses `format_custom_fields_for_api()`
- `update_issue()` → Uses `format_custom_fields_for_api()`
- `update_issue_custom_fields()` → Uses `format_custom_fields_for_api()`

## Error Prevention

### Common Errors Prevented
1. **"Incompatible field type"** - Fixed by proper `$type` discriminators
2. **"Incompatible value format for type date"** - Fixed by timestamp conversion
3. **Multi-value field errors** - Fixed by array formatting with proper types
4. **"Entity with id * not found"** - Fixed by alternative API endpoint for wildcard bundles

### Validation
Field values are validated before submission:
- Check allowed values for enums
- Verify user IDs exist
- Validate date formats
- Ensure required fields are present

## Usage Examples

### Create Issue with Custom Fields
```python
await issues.create(
    project="CLUSTER",
    summary="Test Issue",
    custom_fields={
        "Priority": "High",           # Single enum
        "Due Date": "2025-10-25",    # Date → timestamp
        "Change Type": "Configuration", # Multi-value enum
        "Assignee": ["cventers"]      # User field
    }
)
```

### Update Custom Fields
```python
await issues.patch(
    issue_id="CLUSTER-4441",
    fields={
        "Change Type": "Configuration",    # Auto-detects multi-value
        "Emergency Change?": "No",         # Single enum
        "Customer Facing?": "Yes",         # Single enum
        "Due Date": "2025-10-30"          # Date conversion
    }
)
```

## Benefits

1. **Unified Logic**: Single source of truth for field formatting
2. **Schema Awareness**: Uses actual project schema for accurate formatting
3. **Performance**: Cached schemas reduce API calls
4. **Error Handling**: Clear errors with troubleshooting guidance
5. **Backward Compatibility**: Fallback formatting when schema unavailable
6. **Future-Proof**: Easily extensible for new field types

## Implementation Files

- **Main Implementation**: `/home/chase/Development/Personal/youtrack-mcp/youtrack_mcp/api/issues.py`
  - `format_custom_fields_for_api()` - Unified formatting method
  - `_format_custom_field_with_schema()` - Schema-based formatting
  - `_format_custom_fields_simple()` - Fallback formatting

- **Multi-Value Detection**: `/home/chase/Development/Personal/youtrack-mcp/youtrack_mcp/api/projects.py`
  - Enhanced to detect `[*]` pattern in bundle IDs
  - Alternative API endpoint for wildcard bundles

- **Tool Integration**:
  - `/home/chase/Development/Personal/youtrack-mcp/youtrack_mcp/tools/issues_tools.py`
  - All tools use unified formatting

## Testing

Test script available at: `tests/test_multivalue_enum_fix.py`

Verifies:
1. Multi-value field detection
2. Proper formatting of single values for multi-value fields
3. Date field conversion
4. Schema caching behavior

## Conclusion

This unified field formatting solution ensures consistent, schema-aware formatting across all YouTrack MCP operations, eliminating "Incompatible field type" errors and providing a robust foundation for custom field handling.