# Bug Report: Validation Errors Not Showing in MCP Tool Responses

**Date**: 2025-10-14
**Reported By**: Chase Venters
**Severity**: High
**Status**: ✅ FIXED

---

## Problem Summary

When YouTrack API returns validation errors (HTTP 400), the MCP tool response incorrectly shows `is_error: False` when it should show `is_error: True`. This causes LLM clients to treat API errors as successful responses.

---

## Root Cause Analysis

### The Issue

From analyzing `@local/20251012-youtrack-query.md`, validation errors were being caught and returned as JSON objects rather than propagated as exceptions:

```python
# Line 945: HTTP 400 validation error
[{'tool_use_id': 'toolu_01MYPk8yVazhnmWpcGk3fZqe',
  'type': 'tool_result',
  'content': [{'type': 'text', 'text': '{\n  "error": "API request failed with status 400: invalid_query",\n  "error_type": "ValidationError",\n  "query": "project: SP created: -1w .. Today #Unresolved"\n}'}]}]
```

**Problem**: `is_error: False` should have been `is_error: True`.

### Call Stack

1. **API Client** (`youtrack_mcp/api/client.py:270`)
   - ✅ Correctly raises `ValidationError` for HTTP 400 responses

2. **Search Tools** (`youtrack_mcp/tools/search_tools.py:177-183`)
   - ❌ Catches **all** exceptions with broad `except Exception`
   - ❌ Returns errors as JSON dicts: `{"error": ..., "error_type": ...}`

3. **MCP Tools** (`youtrack_mcp/server_fastmcp.py:67-69`)
   - ❌ Simply returns the result from `search_tools.query()`
   - No awareness that result contains error

4. **MCP Protocol**
   - ❌ Treats returned JSON as successful result
   - Sets `is_error: False` because no exception was raised

---

## Impact

### User Experience
- LLM models receive "successful" responses containing error messages
- Models may attempt to parse error messages as valid data
- Incorrect retry logic and error handling in LLM workflows

### Example Failure
```bash
# User Query
"Check the SP board for any issues about Android logins this week"

# Tool Call
mcp__youtrack__search_query(
    query="project: SP created: -1w .. Today #Unresolved"
)

# Result (WRONG)
{
  "is_error": False,  # ❌ Should be True
  "content": {
    "error": "API request failed with status 400: invalid_query",
    "error_type": "ValidationError"
  }
}
```

---

## Solution Implemented

### Changes Made

#### 1. Modified `youtrack_mcp/tools/search_tools.py`

**Before** (lines 177-183):
```python
except Exception as e:
    logger.exception(f"Error in search query: {query}")
    return {
        "error": str(e),
        "error_type": type(e).__name__,
        "query": query
    }
```

**After**:
```python
except Exception as e:
    # Let YouTrack API errors propagate so MCP can mark them as is_error=True
    from youtrack_mcp.api.client import YouTrackAPIError
    if isinstance(e, YouTrackAPIError):
        logger.error(f"YouTrack API error in search query: {query}",
                   error_type=type(e).__name__,
                   status_code=getattr(e, 'status_code', None))
        raise

    # For truly unexpected errors, log and re-raise
    logger.exception(f"Unexpected error in search query: {query}")
    raise
```

**Same fix applied to `autosearch()` method** (lines 255-281)

#### 2. Created Comprehensive Test Suite

`tests/unit/test_validation_error_propagation.py`:
- ✅ `test_validation_error_propagates_as_exception` - Confirms ValidationError is raised
- ✅ `test_validation_error_not_returned_as_json` - Confirms no error dicts returned
- ✅ `test_other_exceptions_also_propagate` - Confirms all exceptions propagate
- ✅ `test_successful_query_returns_dict` - Confirms successful queries still work

---

## Testing Results

### Before Fix
```bash
$ pytest tests/unit/test_validation_error_propagation.py -v
test_validation_error_propagates_as_exception FAILED  # ❌
test_validation_error_not_returned_as_json FAILED     # ❌
test_other_exceptions_still_caught PASSED             # ⚠️
test_successful_query_returns_dict PASSED             # ✅
```

### After Fix
```bash
$ pytest tests/unit/test_validation_error_propagation.py -v
test_validation_error_propagates_as_exception PASSED  # ✅
test_validation_error_not_returned_as_json PASSED     # ✅
test_other_exceptions_also_propagate PASSED           # ✅
test_successful_query_returns_dict PASSED             # ✅
```

---

## Behavior Changes

### Exception Propagation

| Exception Type | Old Behavior | New Behavior |
|----------------|--------------|--------------|
| `ValidationError` | Caught, returned as JSON | Propagated to MCP |
| `AuthenticationError` | Caught, returned as JSON | Propagated to MCP |
| `PermissionDeniedError` | Caught, returned as JSON | Propagated to MCP |
| `ResourceNotFoundError` | Caught, returned as JSON | Propagated to MCP |
| `RateLimitError` | Caught, returned as JSON | Propagated to MCP |
| `ServerError` | Caught, returned as JSON | Propagated to MCP |
| `YouTrackAPIError` (any) | Caught, returned as JSON | Propagated to MCP |
| Other exceptions | Caught, returned as JSON | Propagated to MCP |

### MCP Response Format

**Successful Query:**
```json
{
  "is_error": false,
  "content": {
    "query": "project: SP",
    "results": [...],
    "count": 10
  }
}
```

**Failed Query (NEW):**
```json
{
  "is_error": true,
  "content": "API request failed with status 400: invalid_query"
}
```

---

## Files Modified

1. `youtrack_mcp/tools/search_tools.py`
   - Modified `query()` method exception handling
   - Modified `autosearch()` method exception handling

2. `tests/unit/test_validation_error_propagation.py` (NEW)
   - Comprehensive test coverage for error propagation

---

## Verification Steps

1. **Run New Tests**
   ```bash
   pytest tests/unit/test_validation_error_propagation.py -v
   ```
   ✅ All 4 tests pass

2. **Test Invalid YQL Query**
   ```python
   # This should now raise ValidationError
   await search_tools.query("project: SP created: -1w .. Today")
   ```

3. **Test Valid Query**
   ```python
   # This should still return normal results
   await search_tools.query("project: SP #Unresolved")
   ```

---

## Follow-Up Tasks

### Completed ✅
- [x] Identify root cause in search_tools.py
- [x] Fix exception handling to propagate API errors
- [x] Create comprehensive test suite
- [x] Verify fix with test execution
- [x] Document the fix and create bug report

### Future Considerations
- [ ] Review other tool files (issues_tools, projects_tools, users_tools) for similar patterns
- [ ] Add integration tests with actual YouTrack instance
- [ ] Consider adding error code categorization for better error handling
- [ ] Update error handling best practices documentation

---

## Related Files

- **Log File**: `@local/20251012-youtrack-query.md` (original bug evidence)
- **API Client**: `youtrack_mcp/api/client.py` (error definitions)
- **MCP Server**: `youtrack_mcp/server_fastmcp.py` (tool registration)
- **Test Suite**: `tests/unit/test_validation_error_propagation.py`

---

## References

- MCP Protocol Specification: Error handling requires exceptions, not error dicts
- YouTrack API Documentation: HTTP 400 indicates invalid query syntax
- FastMCP Library: Exceptions are automatically converted to `is_error: true` responses

---

**Fix Verified**: 2025-10-14
**All Tests Passing**: ✅
**Production Ready**: ✅
