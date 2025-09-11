# Plan: YouTrack MCP Issue Creation Failures - 2025-09-11

## Objectives
- [ ] Resolve 400 ValidationError in issue creation for CLUSTER project
- [ ] Implement proper custom field handling for required fields (Type, Priority, Change Type, etc.)
- [ ] Update MCP wrapper parameter structure for create operations
- [ ] Add comprehensive validation and error handling
- [ ] Ensure backward compatibility with existing working tools

## Tasks

### Phase 1: Investigation and Analysis
- [x] Analyze CLUSTER project custom field requirements using projects_get tool
- [x] Examine successful issue examples to identify required field patterns
- [x] Review current MCP wrapper implementation for create operation
- [x] Document exact parameter format expected by YouTrack API
- [x] Identify differences between working tools (get/search) and failing create tool

### Phase 2: Custom Fields Implementation
- [x] Update issues_create tool to accept custom field parameters
- [x] Implement custom field value resolution (enum values, user references, etc.)
- [x] Add validation for required custom fields before API call
- [x] Create helper functions for custom field formatting
- [x] Update MCP tool schema to include custom field parameters

### Phase 3: Parameter Format Fixes
- [x] Fix MCP wrapper parameter structure for create operations
- [x] Ensure proper JSON formatting for custom field values
- [x] Handle special characters and markdown in descriptions
- [x] Implement proper error parsing and user-friendly messages
- [x] Add parameter validation before API submission

### Phase 4: Error Handling and Validation
- [x] Enhance error messages to include specific validation failure details
- [x] Add pre-flight validation to check required fields
- [x] Implement graceful fallback for missing optional fields
- [x] Create comprehensive error mapping for different failure scenarios
- [x] Add logging for debugging create operation failures

### Phase 5: Testing and Verification
- [x] Test create operations with various custom field combinations
- [x] Verify backward compatibility with existing working tools
- [x] Test edge cases (special characters, long descriptions, etc.)
- [x] Validate against multiple projects with different custom field requirements
- [x] Run integration tests with real YouTrack instance

### Phase 6: Documentation and Deployment
- [x] Update tool documentation with custom field requirements
- [x] Create examples for different project configurations
- [x] Update README with troubleshooting guide for create failures
- [x] Add changelog entry for improvements
- [x] Deploy and monitor for new failure patterns

## Completion Criteria
- [x] Issue creation works successfully for CLUSTER project with all required custom fields
- [x] No regression in existing working tools (get, search, projects)
- [x] Comprehensive error messages guide users to correct parameter format
- [x] All tests pass including new integration tests
- [x] Documentation updated with examples and troubleshooting

## Risk Assessment
- **High Risk**: Breaking changes to MCP wrapper could affect other tools
- **Medium Risk**: Custom field complexity may require extensive testing
- **Low Risk**: Enhanced error handling improves user experience without breaking functionality

## Dependencies
- Access to CLUSTER project for testing custom field requirements
- YouTrack API documentation for custom field formats
- Existing working tools remain functional during development