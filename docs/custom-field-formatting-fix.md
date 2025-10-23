# Custom Field Formatting Fix for Update Operations

## Problem
The `update_issue_custom_fields` method is failing with "Incompatible field type: 65-2" because it's not using the schema-aware formatting that was implemented in the morning session.

## Current State

### What's Working (in create_issue and update_issue)
- `_get_project_schema()` - Fetches and caches project field schemas
- `_format_custom_field_with_schema()` - Formats fields with proper `$type` based on actual schema
- These methods properly handle all field types with correct discriminators

### What's Broken (in update_issue_custom_fields)
- `_update_other_custom_fields()` uses hardcoded type mappings
- Calls old methods like `_create_enum_field_object()` instead of schema-aware formatting
- Results in "Incompatible field type" errors

## Solution: Unified Custom Field Formatting

Create a new method `format_custom_fields_for_api()` that:
1. Takes issue_id or project_id, and custom_fields dict
2. Gets the project schema (cached)
3. Formats ALL fields using `_format_custom_field_with_schema()`
4. Returns properly formatted list ready for API

### Proposed Implementation

```python
async def format_custom_fields_for_api(
    self,
    custom_fields: Dict[str, Any],
    project_id: Optional[str] = None,
    issue_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Format custom fields for YouTrack API with proper schema-based types.

    Args:
        custom_fields: Dictionary of field names and values
        project_id: Project ID (if known)
        issue_id: Issue ID (to get project if project_id not provided)

    Returns:
        List of formatted custom field objects with proper $type
    """
    # Get project ID if not provided
    if not project_id and issue_id:
        issue_data = await self.get_issue(issue_id)
        if hasattr(issue_data, 'project') and issue_data.project:
            if isinstance(issue_data.project, dict):
                project_id = issue_data.project.get('id')
            else:
                project_id = getattr(issue_data.project, 'id', None)

    if not project_id:
        logger.warning("Could not determine project ID for schema lookup")
        # Fall back to simple formatting
        return self._format_custom_fields_simple(custom_fields)

    # Get cached project schema
    project_schema = await self._get_project_schema(project_id)

    # Format each field using schema
    custom_fields_list = []
    for field_name, field_value in custom_fields.items():
        # Normalize the value
        normalized_value = self._normalize_field_value(field_value)

        # Get schema for this field
        field_schema = project_schema.get(field_name, {})

        if field_schema:
            # Use schema-based formatting
            formatted_field = self._format_custom_field_with_schema(
                field_name, normalized_value, field_schema
            )
        else:
            # Fallback for unknown fields
            logger.warning(f"Field '{field_name}' not in schema, using fallback")
            formatted_field = {
                "name": field_name,
                "value": normalized_value,
                "$type": "TextIssueCustomField"
            }

        custom_fields_list.append(formatted_field)

    return custom_fields_list
```

### Update Existing Methods

1. **create_issue**: Already uses schema-aware formatting ✅

2. **update_issue**: Already uses schema-aware formatting ✅

3. **update_issue_custom_fields**: Needs to replace `_update_other_custom_fields` with:
```python
# In _update_other_custom_fields, replace the entire formatting logic with:
custom_fields_list = await self.format_custom_fields_for_api(
    custom_fields=other_fields,
    issue_id=issue_id
)
update_data = {"customFields": custom_fields_list}
```

## Benefits

1. **Single source of truth** for custom field formatting
2. **Consistent behavior** across create and update operations
3. **Automatic handling** of all field types based on actual schema
4. **Cached schema lookups** for performance
5. **Fixes the "Incompatible field type" errors**

## Testing

After implementation, test with:
```python
# Should work without "Incompatible field type" errors
await issues.patch(
    issue_id="CLUSTER-4441",
    fields={
        "Priority": "Normal",
        "Type": "Change Control",
        "Assignee": ["cventers"],  # Will be ID-resolved
        "Due Date": "2025-10-25",
        "Change Type": "Configuration Change",
        "Emergency Change?": "No",
        "Customer Facing?": "Yes"
    }
)
```