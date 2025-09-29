# Test Suite Async Fixes Plan

**Date:** 2025-09-29
**Status:** Not Started
**Objective:** Fix async/await mismatches in the test suite using Serena and MorphLLM tools

## Overview

The YouTrack MCP test suite has ~400+ failing tests due to async/await mismatches. Tests are calling async methods synchronously without `await` keywords and proper `@pytest.mark.asyncio` decorators. This plan guides an AI agent through systematic fixes using Serena's code analysis tools and MorphLLM's batch editing capabilities.

## Prerequisites

- [ ] Verify Serena MCP tools are available (`mcp__serena__*`)
- [ ] Verify MorphLLM tools are available (`mcp__morphllm-fast-apply__*`)
- [ ] Confirm virtual environment is activated: `source .venv/bin/activate`
- [ ] **DO NOT run integration or E2E tests** - only unit tests with mocked dependencies

## Phase 1: Analysis and Discovery

### 1.1 Identify Async Methods in Production Code

- [ ] Use `mcp__serena__find_symbol` to locate all async methods in `youtrack_mcp/api/`:
  ```
  Search pattern: "async def" in youtrack_mcp/api/client.py
  Search pattern: "async def" in youtrack_mcp/api/issues.py
  Search pattern: "async def" in youtrack_mcp/api/projects.py
  Search pattern: "async def" in youtrack_mcp/api/search.py
  Search pattern: "async def" in youtrack_mcp/api/users.py
  ```

- [ ] Create a reference list of all async method signatures:
  - `IssuesClient.search_issues()`
  - `IssuesClient.get_issue()`
  - `IssuesClient.create_issue()`
  - `IssuesClient.update_issue()`
  - `IssuesClient.batch_update_custom_fields()`
  - `IssuesClient.update_issue_custom_fields()`
  - `IssuesClient._validate_custom_field_value()`
  - All `YouTrackClient._make_request()` variants
  - Other async methods as discovered

### 1.2 Scan Test Files for Async Violations

- [ ] Use `mcp__serena__search_for_pattern` to find test methods calling async methods without await:
  ```
  Pattern: "\.search_issues\("
  Path: tests/unit/test_api_issues.py
  Check if preceded by "await" keyword
  ```

- [ ] Use `mcp__serena__list_dir` to get all test files:
  ```
  Path: tests/unit/
  Recursive: true
  ```

- [ ] For each test file, use `mcp__serena__get_symbols_overview` to identify test methods

## Phase 2: Fix test_api_issues.py (Priority 1)

This file has ~26 failing tests due to async issues.

### 2.1 Fix TestIssuesClientSearchMethods

- [ ] Read `tests/unit/test_api_issues.py` using `mcp__serena__read_file` with focus on lines 370-410

- [ ] Use `mcp__morphllm-fast-apply__edit_file` to fix `test_search_issues_basic`:
  ```
  Instruction: "Convert test_search_issues_basic to async test with proper await calls"
  Code edit:
  - Add @pytest.mark.asyncio decorator if missing
  - Change def to async def
  - Add await before issues_client.search_issues() call
  ```

- [ ] Use `mcp__morphllm-fast-apply__edit_file` to fix `test_search_issues_with_limit`:
  ```
  Instruction: "Convert test_search_issues_with_limit to async test with proper await"
  Code edit:
  - Add @pytest.mark.asyncio decorator
  - Change def to async def
  - Add await before search_issues() call
  ```

- [ ] Use `mcp__morphllm-fast-apply__edit_file` to fix `test_search_issues_empty_results`:
  ```
  Instruction: "Convert test_search_issues_empty_results to async test"
  Code edit:
  - Add @pytest.mark.asyncio decorator
  - Change def to async def
  - Add await before search_issues() call
  ```

### 2.2 Fix TestIssuesClientErrorHandling

- [ ] Use `mcp__serena__find_symbol` to locate `test_handle_api_error_response` in test_api_issues.py

- [ ] Use `mcp__morphllm-fast-apply__edit_file` to fix async handling:
  ```
  Instruction: "Fix test_handle_api_error_response to properly await async methods"
  Code edit:
  - Add @pytest.mark.asyncio decorator
  - Change def to async def
  - Add await before search_issues() call in the test
  - Update mock setup to use AsyncMock for async methods
  ```

### 2.3 Fix TestIssuesCustomFields (22 tests)

- [ ] Use `mcp__serena__find_symbol` with pattern "TestIssuesCustomFields" to get all test methods

- [ ] Batch fix all methods calling `batch_update_custom_fields()`:
  ```
  - test_batch_update_custom_fields_success
  - test_batch_update_custom_fields_with_errors
  ```
  Use `mcp__morphllm-fast-apply__edit_file` with instruction:
  "Convert to async tests and await batch_update_custom_fields calls"

- [ ] Batch fix all methods calling `update_issue_custom_fields()`:
  ```
  - test_update_issue_custom_fields_empty_fields
  - test_update_issue_custom_fields_success
  - test_update_issue_custom_fields_validation_error
  - test_update_issue_custom_fields_with_enhanced_objects
  ```
  Use `mcp__morphllm-fast-apply__edit_file` for each

- [ ] Fix methods calling `_validate_custom_field_value()`:
  ```
  - test_validate_custom_field_value_invalid
  - test_validate_custom_field_value_valid
  ```
  Add await and async conversion

- [ ] Fix methods testing async field extraction/formatting:
  ```
  - test_extract_custom_field_value_* (5 tests)
  - test_format_custom_field_value_* (3 tests)
  - test_get_issue_custom_fields_* (2 tests)
  ```
  Check if these methods are actually async, if so add await

### 2.4 Fix TestIssuesCustomFieldValidation

- [ ] Use `mcp__serena__find_symbol` to locate all validation tests

- [ ] Fix each validation test:
  ```
  - test_validate_date_field_invalid
  - test_validate_integer_field_invalid
  - test_validate_state_field_invalid
  - test_validate_user_field_invalid
  ```
  Check if validation methods are async, add await if needed

## Phase 3: Fix Other API Test Files

### 3.1 Scan and Fix test_api_projects.py

- [ ] Use `mcp__serena__get_symbols_overview` on tests/unit/test_api_projects.py

- [ ] Use `mcp__serena__search_for_pattern` to find all async method calls without await

- [ ] Apply fixes using `mcp__morphllm-fast-apply__edit_file` in batches

### 3.2 Scan and Fix test_api_users.py

- [ ] Use `mcp__serena__get_symbols_overview` on tests/unit/test_api_users.py

- [ ] Search for async violations and fix with MorphLLM

### 3.3 Scan and Fix test_api_search.py

- [ ] Use `mcp__serena__get_symbols_overview` on tests/unit/test_api_search.py

- [ ] Search for async violations and fix with MorphLLM

## Phase 4: Fix Tool Test Files

### 4.1 Fix tests/unit/tools/ test files

- [ ] Use `mcp__serena__list_dir` to enumerate all tool test files:
  ```
  Path: tests/unit/tools/
  Recursive: false
  ```

- [ ] For each tool test file:
  - [ ] Use `mcp__serena__get_symbols_overview` to see test structure
  - [ ] Use `mcp__serena__search_for_pattern` to find async violations
  - [ ] Apply batch fixes with `mcp__morphllm-fast-apply__edit_file`

### 4.2 Priority Tool Tests

Fix in this order (highest impact):
- [ ] tests/unit/tools/test_issues_tools.py
- [ ] tests/unit/tools/test_projects_tools.py
- [ ] tests/unit/tools/test_search_tools.py
- [ ] tests/unit/tools/test_users_tools.py

## Phase 5: Mock Setup Fixes

### 5.1 Update Mock Configuration

Many tests need AsyncMock instead of Mock for async methods.

- [ ] Use `mcp__serena__search_for_pattern` to find all `Mock(spec=IssuesClient)`:
  ```
  Pattern: "Mock\(spec=IssuesClient\)"
  Path: tests/unit/
  ```

- [ ] For each found instance, check if async methods are mocked

- [ ] Use `mcp__morphllm-fast-apply__edit_file` to change:
  ```
  OLD: mock_client.some_async_method.return_value = result
  NEW: mock_client.some_async_method = AsyncMock(return_value=result)
  ```

### 5.2 Update Fixture Definitions

- [ ] Use `mcp__serena__search_for_pattern` to find all `@pytest.fixture`:
  ```
  Pattern: "@pytest.fixture"
  Path: tests/unit/
  ```

- [ ] Check if fixtures create clients that call async methods

- [ ] Update fixtures to be async if they need to await:
  ```python
  @pytest.fixture
  async def async_client():
      client = IssuesClient(...)
      await client.some_init()
      return client
  ```

## Phase 6: Validation and Testing

### 6.1 Run Unit Tests Only (NO API CALLS)

**CRITICAL:** Only run tests with mocked dependencies. Do NOT run integration or E2E tests.

- [ ] Run fixed test files individually:
  ```bash
  pytest tests/unit/test_api_issues.py -v --tb=short
  ```

- [ ] If failures occur:
  - [ ] Use `mcp__serena__read_file` to examine failing test
  - [ ] Check error message for remaining async issues
  - [ ] Apply targeted fix with `mcp__morphllm-fast-apply__edit_file`
  - [ ] Re-run test

### 6.2 Run Core Module Tests

- [ ] Test API client modules:
  ```bash
  pytest tests/unit/test_api_client.py tests/unit/test_api_issues.py tests/unit/test_api_projects.py -v
  ```

- [ ] Test tool modules:
  ```bash
  pytest tests/unit/tools/ -v --tb=short
  ```

### 6.3 Final Validation

- [ ] Run all unit tests (excluding integration/e2e):
  ```bash
  pytest tests/unit/ -v -m "not integration and not e2e"
  ```

- [ ] Document pass rate in this file

## Phase 7: Documentation

### 7.1 Update Test Documentation

- [ ] Use `mcp__morphllm-fast-apply__write_file` to update tests/README.md with:
  - Async testing patterns used
  - How to properly mock async methods
  - Examples of correct test structure

### 7.2 Create Testing Best Practices

- [ ] Create `docs/testing-async-patterns.md` with:
  - AsyncMock usage examples
  - Common async pitfalls
  - Test fixture patterns for async code

## Common Patterns Reference

### Pattern 1: Basic Async Test Conversion

```python
# BEFORE
def test_something(self):
    result = client.async_method()
    assert result == expected

# AFTER
@pytest.mark.asyncio
async def test_something(self):
    result = await client.async_method()
    assert result == expected
```

### Pattern 2: AsyncMock Setup

```python
# BEFORE
mock_client.async_method.return_value = result

# AFTER
mock_client.async_method = AsyncMock(return_value=result)
# OR
mock_client.async_method.return_value = result  # If mock_client is already AsyncMock
```

### Pattern 3: Context Manager for Async

```python
# BEFORE
with mock_client:
    result = mock_client.async_method()

# AFTER
async with mock_client:
    result = await mock_client.async_method()
```

### Pattern 4: Exception Testing with Async

```python
# BEFORE
with pytest.raises(SomeError):
    client.async_method()

# AFTER
@pytest.mark.asyncio
async def test_exception(self):
    with pytest.raises(SomeError):
        await client.async_method()
```

## Success Criteria

- [ ] All unit tests pass (target: 95%+ pass rate)
- [ ] No "coroutine was never awaited" warnings
- [ ] No "TypeError: object of type 'coroutine'" errors
- [ ] All async methods properly awaited in tests
- [ ] All async test methods have @pytest.mark.asyncio decorator
- [ ] Mock objects correctly use AsyncMock for async methods

## Notes for AI Agent

1. **DO NOT run integration tests** - They connect to real YouTrack instances
2. **DO NOT run E2E tests** - They require live services
3. **Use Serena tools** for code analysis and navigation
4. **Use MorphLLM tools** for batch editing
5. **Test incrementally** - Fix one file, verify, move to next
6. **Update checkboxes** as you complete each task
7. **Document any unexpected issues** in a notes section below

## Agent Progress Notes

<!-- Agent: Add your progress notes, blockers, and observations here -->

---

## Completion Checklist

- [ ] Phase 1 complete (Analysis)
- [ ] Phase 2 complete (test_api_issues.py)
- [ ] Phase 3 complete (Other API tests)
- [ ] Phase 4 complete (Tool tests)
- [ ] Phase 5 complete (Mock fixes)
- [ ] Phase 6 complete (Validation)
- [ ] Phase 7 complete (Documentation)

**Final Status:** <!-- Agent: Update when complete -->
**Pass Rate:** <!-- Agent: Update with final test pass rate -->