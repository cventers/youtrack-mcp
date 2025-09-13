# Plan: Fix YouTrack MCP Issues - 2025-09-13

## Objectives
- [ ] Resolve assignee field handling returning null values
- [ ] Implement proper date range syntax support
- [ ] Enhance API response expansion for assignee details
- [ ] Improve query validation and error handling

## Critical Issues to Address

### 1. Assignee Field Handling
**Problem:** Top-level `assignee` field consistently returns `null` despite assignee-based queries
**Root Cause:** Assignee data stored in `customFields` arrays with project-specific IDs

### 2. Date Range Syntax
**Problem:** Standard date range syntax not supported (`-6m .. *`, `{6 months ago .. Today}`)
**Impact:** Cannot filter tickets by date ranges, returns 400 invalid_query errors

### 3. API Response Limitations
**Problem:** Assignee details not expanded in basic queries
**Impact:** Requires custom field parsing for assignee information

## Tasks

### Phase 1: Assignee Field Resolution
- [ ] Analyze customFields structure in YouTrack API responses
- [ ] Identify project-specific assignee field ID patterns
- [ ] Create custom field mapping utility for assignee resolution
- [ ] Update search tools to parse assignee from customFields
- [ ] Add assignee expansion to default query parameters
- [ ] Test assignee queries across multiple projects (PAY, SP, CLUSTER, OPS, SOC)

### Phase 2: Date Range Syntax Implementation
- [ ] Research correct YouTrack date syntax patterns
- [ ] Document supported date formats and operators
- [ ] Implement date range validation in query tools
- [ ] Add date syntax conversion utilities
- [ ] Update search tools to handle date ranges properly
- [ ] Test various date range queries (last 6 months, specific periods)

### Phase 3: API Response Enhancement
- [ ] Implement field expansion parameters in search queries
- [ ] Add default expansion for assignee and related fields
- [ ] Update issue retrieval to include customFields by default
- [ ] Enhance response parsing to extract assignee information
- [ ] Optimize API calls to reduce unnecessary requests

### Phase 4: Error Handling and Validation
- [ ] Improve query syntax validation before API calls
- [ ] Add better error messages for invalid date syntax
- [ ] Implement fallback mechanisms for failed queries
- [ ] Update documentation with correct syntax examples
- [ ] Add unit tests for edge cases and error conditions

### Phase 5: Testing and Validation
- [ ] Create comprehensive test suite for assignee queries
- [ ] Test date range filtering across different scenarios
- [ ] Validate field expansion functionality
- [ ] Perform integration testing with real YouTrack data
- [ ] Update existing test cases to cover new functionality

## Completion Criteria
- [ ] All assignee queries return proper assignee information (not null)
- [ ] Date range syntax works for common patterns (last N months, date ranges)
- [ ] API responses include expanded assignee details by default
- [ ] Query validation prevents invalid syntax errors
- [ ] All existing functionality remains backward compatible
- [ ] Comprehensive test coverage for new features
- [ ] Documentation updated with correct usage patterns

## Risk Assessment
- **Low Risk:** Assignee field parsing (backward compatible)
- **Medium Risk:** Date syntax changes (may break existing queries)
- **Low Risk:** Field expansion (additive enhancement)
- **Low Risk:** Error handling improvements (defensive programming)

## Dependencies
- Access to YouTrack API documentation for field structures
- Test environment with various project configurations
- Coordination with existing codebase patterns

## Success Metrics
- 100% assignee field resolution in queries
- Support for all common date range patterns
- Zero 400 invalid_query errors for valid syntax
- Improved user experience with expanded data by default