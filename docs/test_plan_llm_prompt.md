# LLM Test Plan for YouTrack MCP Tools

## Objective
This test plan serves as an LLM prompt to guide an AI agent in comprehensively exercising all YouTrack MCP tools. The goal is to verify functionality, error handling, schema compliance, and integration across all 12 core tools.

## Prerequisites
- Access to a YouTrack instance with test data (projects, issues, users)
- Valid authentication credentials (token or OAuth)
- Test environment where creating/modifying data is safe
- Understanding of YouTrack concepts (projects, issues, custom fields, YQL)

## Test Execution Guidelines
As an AI agent, follow these steps systematically:

1. **Tool Calling Format**: Always use the strict JSON object format for tool calls:
   ```json
   {
     "tool_name": "issues.get",
     "arguments": {
       "issue_id": "DEMO-123",
       "include": ["customFields", "comments"]
     }
   }
   ```

2. **Error Handling**: Test both success and failure scenarios for each tool
3. **Data Validation**: Verify that responses match expected schemas
4. **Integration Testing**: Use outputs from one tool as inputs to another
5. **Edge Cases**: Test with invalid inputs, missing permissions, non-existent entities

## Tool Test Matrix

### 1. issues.get - Rich Issue Retrieval
**Test Scenarios:**
- Retrieve existing issue with minimal fields
- Retrieve with all expansions: `include: ["customFields", "comments", "attachments", "links", "work_items", "history", "activities", "time_tracking"]`
- Test with invalid issue ID
- Test with non-existent project
- Verify custom field values are properly resolved (not just IDs)

**Expected Behavior:**
- Returns complete issue data with requested expansions
- Handles 404 for non-existent issues
- Provides educational error messages for invalid inputs

### 2. issues.create - Schema-Aware Issue Creation
**Test Scenarios:**
- Create basic issue with required fields only
- Create with custom fields (test different field types: enum, user, date, text)
- Test with invalid project ID
- Test with missing required fields
- Test with invalid custom field values

**Expected Behavior:**
- Validates all inputs against project schema
- Returns created issue ID
- Handles validation errors with specific field feedback

### 3. issues.patch - Flexible Issue Updates
**Test Scenarios:**
- Update system fields using `/fields/<FieldName>` syntax
- Add comments using `/comments`
- Attach files using `/attachments`
- Update work items using `/work_items`
- Link issues using `/links`
- Test with invalid field names
- Test with incompatible field values

**Expected Behavior:**
- Supports both `fields{}` and `ops[]` patterns
- Validates field compatibility
- Returns updated issue data
- Handles partial failures gracefully

### 4. projects.list - Project Discovery
**Test Scenarios:**
- List all accessible projects
- Test pagination parameters
- Verify project metadata (shortName, name, description)

**Expected Behavior:**
- Returns array of project summaries
- Handles pagination correctly
- Filters by user permissions

### 5. projects.get - Detailed Project Information
**Test Scenarios:**
- Retrieve project with basic info
- Retrieve with full expansions: `include: ["schema", "versions", "builds", "subsystems"]`
- Test with invalid project ID
- Verify custom field schema details

**Expected Behavior:**
- Returns comprehensive project data
- Includes field definitions and validation rules
- Handles 404 for non-existent projects

### 6. projects.schema - Custom Field Schema
**Test Scenarios:**
- Get schema for existing project
- Verify field types, requirements, and validation rules
- Test with invalid project ID

**Expected Behavior:**
- Returns complete field schema
- Includes enum values, user groups, date formats
- Used for validating issue creation/updates

### 7. projects.patch - Project Modifications
**Test Scenarios:**
- Update project metadata (name, description)
- Modify custom field definitions
- Test with invalid field configurations
- Verify permission requirements

**Expected Behavior:**
- Validates field schema changes
- Returns updated project data
- Handles permission errors appropriately

### 8. projects.create - New Project Creation
**Test Scenarios:**
- Create project with minimal required fields
- Create with custom fields defined
- Test with invalid lead user
- Test duplicate shortName

**Expected Behavior:**
- Validates all input parameters
- Returns created project data
- Handles validation errors with specific feedback

### 9. users.search - User Discovery
**Test Scenarios:**
- Search by exact login
- Search by partial name
- Test with non-existent user
- Verify user metadata (name, email, groups)

**Expected Behavior:**
- Returns matching user objects
- Handles fuzzy matching
- Filters by visibility permissions

### 10. search.query - YQL Query Execution
**Test Scenarios:**
- Execute simple queries: `project: DEMO`
- Execute complex YQL: `project: DEMO state: Open assignee: me`
- Test date ranges: `created: 2024-01-01 .. 2024-12-31`
- Test custom fields: `{Priority}: High`
- Test invalid query syntax

**Expected Behavior:**
- Returns matching issues
- Handles query parsing errors
- Supports all YQL operators and functions

### 11. search.autosearch - Natural Language to YQL
**Test Scenarios:**
- Convert natural language: "show me all open bugs in Demo project"
- Test complex queries: "issues assigned to me with high priority"
- Test ambiguous requests
- Verify generated YQL accuracy

**Expected Behavior:**
- Translates natural language to valid YQL
- Returns issues matching the intent
- Provides query explanation when needed

### 12. ai.plan - Operation Planning
**Test Scenarios:**
- Request plan for complex multi-step operations
- Test with ambiguous requirements
- Verify plan structure and feasibility

**Expected Behavior:**
- Returns structured operation plan
- Includes prerequisites and dependencies
- Provides alternative approaches

### 13. resources.read - MCP Resource Access
**Test Scenarios:**
- Read documentation resources
- Test with invalid URIs
- Verify resource content accuracy

**Expected Behavior:**
- Returns requested resource content
- Handles 404 for non-existent resources
- Supports different content formats

## Integration Test Scenarios

### End-to-End Workflows
1. **Issue Lifecycle**:
   - Create project with custom fields
   - Create issue with custom fields
   - Update issue fields
   - Search for the issue
   - Add comments and attachments
   - Link to other issues

2. **Project Setup**:
   - Create project
   - Define custom fields
   - Create issues using the schema
   - Update project settings

3. **User Management**:
   - Search for users
   - Assign issues to users
   - Update user-related custom fields

### Error Recovery
- Test network failures
- Test authentication expiration
- Test rate limiting
- Verify graceful degradation

## Validation Checklist
- [ ] All tools respond with valid JSON
- [ ] Error messages are educational and actionable
- [ ] Schema validation works correctly
- [ ] Custom fields are properly resolved
- [ ] Permissions are respected
- [ ] Performance is acceptable
- [ ] No sensitive data is leaked

## Reporting
After completing all tests, provide a summary report including:
- Tools tested and their status
- Any failures or unexpected behaviors
- Performance observations
- Recommendations for improvements