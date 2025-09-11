# Custom Fields Migration Guide

## Overview

The YouTrack MCP server has been refactored to use a minimal tool surface while preserving all functionality. Legacy custom fields tools have been consolidated into the core tool set with backward compatibility.

## What Changed

### Removed Tools (Available via Router)
- `projects.custom_fields` → Use `projects.schema`
- `issues.custom_fields.update_custom_fields` → Use `issues.patch`

### New/Enhanced Tools
- `projects.schema` - Canonical schema discovery
- `projects.get(include=["schema"])` - Schema via expansion
- `issues.patch` - Unified writer with `/fields/<FieldName>` support

## Migration Examples

### Before: Getting Custom Fields
```python
# Old way
result = await projects.custom_fields("MY_PROJECT")
```

### After: Using Schema Tool
```python
# New way - recommended
result = await projects.schema("MY_PROJECT")

# Or via expansion
result = await projects.get("MY_PROJECT", include=["schema"])
```

### Before: Updating Custom Fields
```python
# Old way
result = await issues.custom_fields.update_custom_fields(
    "PROJECT-123",
    {"Type": "Bug", "Priority": "High"}
)
```

### After: Using Patch Tool
```python
# New way - friendly format
result = await issues.patch(
    "PROJECT-123",
    fields={"Type": "Bug", "Priority": "High"}
)

# Or with subpath operations
result = await issues.patch(
    "PROJECT-123",
    ops=[
        {"op": "set", "path": "/fields/Type", "value": "Bug"},
        {"op": "set", "path": "/fields/Priority", "value": "High"}
    ]
)
```

## Backward Compatibility

All legacy tool calls will continue to work with:
- Automatic routing to new implementations
- One-time deprecation warnings per process
- Identical response formats where possible

## Benefits of New Architecture

### For Users
- **Simpler API**: Fewer tools to learn and remember
- **Better Error Messages**: Schema-aware validation with helpful guidance
- **Unified Interface**: Single `issues.patch` tool for all updates
- **Comprehensive Schema**: Complete field metadata in one call

### For Developers
- **Minimal Surface**: Reduced tool count for better performance
- **Schema-Aware**: Automatic field type validation and coercion
- **Maintainable**: Consolidated logic in fewer, focused tools
- **Testable**: Clear separation of concerns for comprehensive testing

## Response Format Changes

### Schema Tool Response
```json
{
  "project_id": "MY_PROJECT",
  "schemas": {
    "Type": {
      "type": "enum",
      "required": true,
      "allowed_values": ["Bug", "Feature", "Task"]
    }
  },
  "required_fields": [...],
  "optional_fields": [...],
  "usage_guide": {...}
}
```

### Patch Tool Response
```json
{
  "issue": {...},
  "updated": true,
  "regular_fields_updated": ["summary"],
  "custom_fields_updated": ["Type", "Priority"],
  "total_fields_updated": 3,
  "message": "Successfully updated issue PROJECT-123"
}
```

## Help Resources

Access detailed documentation for the new tools:

- `help://projects.schema` - Complete schema tool documentation
- `help://issues.patch` - Patch tool with examples and field support
- `help://projects.get` - Updated with schema expansion examples

## Troubleshooting

### Deprecation Warnings
If you see deprecation warnings, update your code to use the new tools. The warnings will appear once per process and include migration guidance.

### Schema Errors
If schema calls fail, ensure:
- Project ID/name is correct
- You have permission to view the project
- The project exists and is accessible

### Patch Errors
If patch operations fail:
- Verify field names match project schema
- Check that enum values are from allowed_values list
- Ensure user fields contain valid user identifiers

## Timeline

- **Immediate**: Legacy tools work via router with deprecation warnings
- **Recommended**: Migrate to new tools for better performance and features
- **Future**: Legacy tools may be removed in future versions

## Need Help?

- Check `help://` resources for detailed examples
- Review test files in `tests/unit/test_tool_reactor.py` for usage patterns
- See `docs/plans/20250911-tool-reactor-plan.md` for implementation details</content>
</xai:function_call">Create comprehensive migration guide for custom fields refactoring