# Plan to Fix YouTrack MCP Server Errors

## Date: 2025-09-25
## Status: Ready for Implementation

## Problem Summary

Based on analysis of `local/youtrack-problems.md` and the YouTrack MCP log file, the following critical issues have been identified:

### 1. **Custom Field Type Incompatibility (Critical)**
- **Error**: `"Incompatible field type: 65-10"` and `"Incompatible field type: 65-2"`
- **Root Cause**: The MCP server is incorrectly using field IDs (65-10, 65-2) as field type identifiers
- **Impact**: Cannot create issues with custom fields, especially assignee field

**Log Evidence**:
```
Creating issue with data: {'project': {'id': '63-10'},
'summary': 'Update AWS IAM password policy...',
'customFields': [{'$type': 'SingleUserIssueCustomField',
'name': 'Assignee', 'value': {'$type': 'User', 'id': '25-6'}}]}

{"event": "API error for POST https://exceleron.myjetbrains.com/api/issues:
API request failed with status 400: Bad Request",
"timestamp": "2025-09-24T16:08:47.795736Z"}

{"event": "Response content: {\"error\":\"Bad Request\",
\"error_description\":\"Incompatible field type: 65-10\"}",
"timestamp": "2025-09-24T16:08:47.796154Z"}
```

### 2. **Incorrect Assignee Field Format**
- **Error**: Assignee field value formatted as `"[{'id': '25-6'}]"` (string) instead of proper object
- **Root Cause**: Incorrect JSON serialization of user reference in custom fields
- **Impact**: Assignment operations fail silently or with validation errors

**Log Evidence**:
```
Creating issue with data: {'project': {'id': '63-10'},
'customFields': [{'$type': 'SingleUserIssueCustomField',
'name': 'Assignee', 'value': {'$type': 'User', 'id': "[{'id': '25-6'}]"}}]}
# Note: The user ID is a STRING containing "[{'id': '25-6'}]" instead of an object

Could not find bundle element for Type=Task, using simple value
Could not find bundle element for Priority=Normal, using simple value
```

### 3. **Silent Patch Operation Failures**
- **Error**: Patch operations report success but don't actually update fields
- **Root Cause**: Incorrect field path casing or format (`/Assignee` vs `/assignee`)
- **Impact**: False success reports mislead users

### 4. **LLM Tool Choice Failures**
- **Error**: LLM failing with "Tool choice is required, but model did not call a tool"
- **Root Cause**: Model not generating structured output when tools are defined and tool_choice is set
- **Impact**: AI planning features fail when strict tool calling is required

**Log Evidence**:
```
litellm.BadRequestError: GroqException - {"error":{"message":"Tool call validation failed:
tool call validation failed: attempted to call tool 'IntentAnalysis' which was not in request.tools",
"type":"invalid_request_error","code":"tool_use_failed"}}

litellm.BadRequestError: GroqException - {"error":{"message":"Tool call validation failed:
parameters for tool IntentAnalysisResponse did not match schema: errors:
[`/plan/0`: missing properties: 'tool', 'description', 'parameters', 'expected_result',
`/plan/0/step`: expected integer, but got string]"}}

litellm.RateLimitError: GroqException - {"error":{"message":"Tool choice is required,
but model did not call a tool","type":"invalid_request_error","code":"tool_use_failed",
"failed_generation":"**Execution Plan – \"Find all tickets created by *Chase Venters*..."}}
```

**Pattern Analysis**:
- Tool name mismatches: Model tries to call 'IntentAnalysis' when expecting 'IntentAnalysisResponse'
- Schema validation failures: Plan steps have wrong structure (string instead of integer for step number)
- Model generates markdown tables instead of tool calls when required

## Implementation Plan

### Phase 1: Fix Custom Field Type Handling ⚠️ **CRITICAL**

#### 1.1 Diagnose Field Type Issue
```python
# Location: youtrack_mcp/api/issues.py
# The error "Incompatible field type: 65-10" suggests we're passing
# a field ID where a field TYPE is expected

# Current problematic code likely looks like:
customFields = [{
    "$type": "SingleUserIssueCustomField",  # This might be wrong
    "name": "Assignee",
    "value": {"$type": "User", "id": "25-6"}
}]

# Should investigate if $type needs to be the actual field prototype ID
```

#### 1.2 Fix Custom Field Creation
- **File**: `youtrack_mcp/api/issues.py`
- **Method**: `create_issue` (around line 370)
- **Changes**:
  1. Remove hardcoded `$type` values for custom fields
  2. Use field schema to determine correct field types
  3. Properly format user references

```python
# Proposed fix structure:
async def format_custom_field(self, field_name, field_value, project_id):
    # Get field schema from project
    schema = await self.get_project_custom_field(project_id, field_name)

    # Format based on actual field type from schema
    if schema['fieldType']['$type'] == 'UserProjectCustomField':
        return {
            "$type": schema['field']['fieldType']['valueType'],
            "name": field_name,
            "value": {"id": field_value} if isinstance(field_value, str) else field_value
        }
```

### Phase 2: Fix Assignee Field Handling

#### 2.1 Correct JSON Serialization
- **File**: `youtrack_mcp/tools/issues/custom_fields.py`
- **Issue**: User ID being converted to string `"[{'id': '25-6'}]"`
- **Fix**:
```python
# Wrong:
if field_name == "Assignee":
    value = str([{"id": user_id}])  # This creates a string!

# Correct:
if field_name == "Assignee":
    value = {"id": user_id}  # Keep as object
```

#### 2.2 Implement Proper Field Resolution
- Add field type detection before formatting
- Use YouTrack's field schema API to validate field types
- Cache field schemas per project

### Phase 3: Fix Patch Operations

#### 3.1 Field Path Normalization
- **File**: `youtrack_mcp/tools/issues/dedicated_updates.py`
- **Changes**:
```python
def normalize_field_path(path: str) -> str:
    """Normalize field paths for YouTrack API."""
    # Handle both /Assignee and /assignee
    field_name = path.lstrip('/')

    # Map common field names to correct API paths
    field_map = {
        'Assignee': 'assignee',
        'assignee': 'assignee',
        'Type': 'type',
        'Priority': 'priority',
        # Add more mappings
    }

    return f"/{field_map.get(field_name, field_name)}"
```

#### 3.2 Validate Patch Results
- After patch operation, fetch the field value to confirm update
- Return actual error if field didn't update
- Log detailed information about failed updates

### Phase 4: Fix LLM Tool Integration

#### 4.1 Update Tool Choice Format
- **File**: `youtrack_mcp/ai/llm_client.py`
- **Changes**:
```python
# Add tool_choice parameter when tools are provided
if tools:
    call_kwargs["tool_choice"] = "auto"  # or "required" when strict tool use is needed
```

#### 4.2 Handle Tool Choice Requirements
- Ensure proper tool_choice parameter is set when tools are provided
- Handle cases where model doesn't call tools despite requirement
- Implement fallback for non-tool responses

### Phase 5: Add Comprehensive Error Handling

#### 5.1 Enhanced Error Messages
```python
class DetailedValidationError(Exception):
    def __init__(self, message, field_errors=None, suggestion=None):
        self.message = message
        self.field_errors = field_errors or {}
        self.suggestion = suggestion
        super().__init__(message)
```

#### 5.2 Field Validation Before API Calls
- Validate custom field formats before sending to API
- Check field permissions and types
- Provide clear error messages with field-specific issues

### Phase 6: Testing Strategy

#### 6.1 Unit Tests
```python
# tests/test_custom_field_handling.py
async def test_assignee_field_format():
    """Test that assignee field is properly formatted."""
    # Test with user ID string
    # Test with user object
    # Test with invalid formats

async def test_field_type_resolution():
    """Test that field types are correctly resolved from schema."""
    # Mock project schema
    # Test different field types
    # Verify correct $type values
```

#### 6.2 Integration Tests
- Create issue with all custom field types
- Update each field type via patch
- Verify actual changes in YouTrack

### Phase 7: Documentation Updates

#### 7.1 Update CLAUDE.md
- Document correct custom field formats
- Add examples of working field updates
- Include troubleshooting guide

#### 7.2 Add Field Format Examples
```markdown
## Custom Field Formats

### User Fields (Assignee)
```json
{
  "name": "Assignee",
  "value": {"id": "user-id-here"}
}
```

### Enum Fields (Type, Priority)
```json
{
  "name": "Type",
  "value": {"name": "Bug"}
}
```
```

## Implementation Priority

1. **URGENT**: Fix custom field type issue (Phase 1) - Blocking issue creation
2. **HIGH**: Fix assignee field format (Phase 2) - Affects most operations
3. **HIGH**: Fix patch operations (Phase 3) - Silent failures are dangerous
4. **MEDIUM**: Fix LLM integration (Phase 4) - AI features broken
5. **MEDIUM**: Enhanced error handling (Phase 5) - Improves debugging
6. **LOW**: Testing and documentation (Phases 6-7) - Quality improvements

## Success Metrics

- [ ] Can create issues with custom fields including assignee
- [ ] Patch operations actually update fields
- [ ] Clear error messages when operations fail
- [ ] AI planning features work with tool calling
- [ ] All existing tests pass
- [ ] New tests cover fixed functionality

## Next Steps

1. Start with Phase 1.1 - Diagnose the exact field type issue
2. Implement minimal fix to unblock issue creation
3. Test with real YouTrack instance
4. Iterate through remaining phases