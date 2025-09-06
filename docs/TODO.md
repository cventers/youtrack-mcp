# YouTrack MCP TODO List

## ✅ COMPLETED - ID Consistency Fix (2025-01-18)

### Issue Resolution: Human-Readable ID Preference
- **Problem**: MCP tools inconsistently returned internal IDs (`82-12318`) vs human-readable IDs (`PAY-557`)
- **Solution**: Implemented ID normalization system with clear AI guidance

**Changes Made**:
- ✅ **Added ID normalization utilities** (`utils.py`):
  - `normalize_issue_ids()` - Ensures human-readable IDs are primary
  - `is_human_readable_id()` - Validates ID format patterns
  - `validate_issue_id()` - Provides ID classification and recommendations

- ✅ **Updated all MCP tool responses**:
  - All search and get tools now return `id` field with human-readable ID (e.g., `PAY-557`)
  - Internal database IDs moved to `_internal_id` field (discouraged from use)
  - Added `_id_usage_note` field with explicit guidance

- ✅ **Enhanced tool descriptions**:
  - Clear documentation that `id` field contains human-readable ID
  - Explicit warnings against using `_internal_id` field
  - Added `validate_issue_id_format()` tool for ID validation

**Impact**: AI models will now consistently use human-readable IDs (PAY-557) instead of internal IDs (82-12318), improving readability and user experience.

## Critical Issues from Bot/Technical Review

### Immediate Priority - Performance & Compatibility

- [ ] **Switch from requests to httpx.AsyncClient**
  - Current: Using blocking `requests` library in FastAPI async context
  - Fix: Implement `httpx.AsyncClient` with shared connection pool
  - Impact: Eliminates thread-pool overhead, better FastAPI scaling
  - Files: `youtrack_mcp/api/client.py`, lifespan event in `main.py`

- [ ] **Fix Pydantic v2 migration issues**
  - Current: Mixing v1 validators (`@validator`) with v2 (`model_validator`)
  - Fix: Remove v1 imports, run `pydantic codemod`
  - Impact: Fewer runtime warnings, faster model parsing
  - Files: All model definitions

- [ ] **Add MCP compliance tests**
  - Missing: Official SDK contract tests
  - Add: `pip install mcp[test]` and `pytest -k mcp_contracts`
  - Impact: Guards against breaking handshake/capability messages
  - Risk: CLI auto-resume failures

- [ ] **Fix token security risk**
  - Current: Token loaded into memory for process lifetime
  - Fix: Lazy loading per request or async LRU cache
  - Impact: Reduced memory exposure of sensitive tokens
  - Files: `config.py`

### High Priority - Claude Code CLI Compatibility

- [ ] **Support project-scoped .mcp.json auto-approval**
  - Add: Single-line example with `"type": "stdio"` field
  - Update: README with copy-paste example
  - Impact: Better user onboarding experience

- [ ] **Handle MCP_TIMEOUT environment variable**
  - Add: Documentation for `export MCP_TIMEOUT=15000`
  - Update: Podman/systemd examples
  - Impact: Prevent early server kills on slow startup

- [ ] **Ensure fast handshake for session auto-resume**
  - Fix: Flush handshake JSON immediately: `print(json.dumps(msg), flush=True)`
  - Requirement: Clean handshake within 2 seconds after CLI crash
  - Files: `main.py` startup sequence

- [ ] **Add structured JSON logging**
  - Current: Limited observability
  - Add: `structlog` for JSON logs
  - Impact: Better debugging with Claude Code's `/mcp debug` command
  - Files: All logging throughout codebase

### High Priority - Security & Deployment

- [ ] **Harden Dockerfile**
  - Current: Running as root user
  - Add: Non-root UID 10001, `--chown` on copy, `USER 10001`
  - Impact: Reduces CVE scanner noise in supply-chain reviews
  - Files: `Dockerfile`

- [ ] **Create systemd user-unit example**
  - Add: `~/.config/systemd/user/youtrack-mcp.service` example
  - Include: Podman integration with proper user/security settings
  - Files: New file in `docs/`

## Code Quality Improvements (Based on Upstream PR Feedback)

### High Priority - Exception Handling & LLM Error Communication

- [ ] **Replace generic exception handling with specific exceptions**
  - Current: `except Exception as e:` everywhere
  - Need: Specific HTTP, API, validation, and network exceptions
  - Files to update: `main.py` (all @mcp.tool() functions)

- [ ] **Implement proper error categorization**
  - [ ] Network/connectivity errors (requests.ConnectionError, TimeoutError)
  - [ ] API authentication errors (401, 403 status codes)
  - [ ] API rate limiting errors (429 status codes)
  - [ ] Resource not found errors (404 status codes)
  - [ ] Validation errors (400 status codes, malformed data)
  - [ ] Server errors (500+ status codes)

- [ ] **Add LLM-optimized error responses (CRITICAL)**
  - [ ] **Descriptive error messages for LLM learning**
    - Include what went wrong, why it failed, and how to fix it
    - Provide examples of correct syntax/usage
    - Give guidance for future attempts
  - [ ] **YouTrack query syntax errors**
    - Parse YouTrack API error responses for query syntax issues
    - Explain valid YouTrack Query Language (YQL) syntax
    - Provide corrected query examples
    - Remember: "In the future, use this syntax instead..."
  - [ ] **Parameter validation errors**
    - Explain valid parameter formats (dates, project names, user logins)
    - Provide examples of correct parameter values
    - Suggest alternatives when parameters are invalid
  - [ ] **Context-rich error details**
    - Include operation attempted, parameters used, expected format
    - Hide technical tracebacks but preserve diagnostic information
    - Add "Recommendation" section for LLM guidance

- [ ] **Add YouTrack-specific error handling**
  - [ ] **Post-error query education (recommended approach)**
    - Return YouTrack errors as-is but add educational context
    - Parse YouTrack API error responses and enhance with explanations
    - Don't pre-validate - let YouTrack be authoritative for its own syntax
    - Example: Return YouTrack's "Invalid query" + our explanation of correct syntax
  - [ ] **Field name validation and suggestions**
    - Validate custom field names against project schema when possible
    - Suggest correct field names for typos
    - Explain available fields when field not found
  - [ ] **Project/user existence validation**
    - Check if projects/users exist before complex operations
    - Suggest similar names if exact match not found
    - Provide helpful "did you mean?" suggestions
  - [ ] **Date/time conversion for LLM inputs (CRITICAL)**
    - Create `convert_datetime()` tool for LLM date inputs → YouTrack format
    - Support multiple LLM input formats: "2025-06-13", "last week", "3 days ago", "yesterday"
    - Handle epochs, epoch_ms, ISO 8601, relative dates, timezones
    - Let YouTrack validate its own date syntax in queries
    - When YouTrack rejects dates, add educational context to the error

### High Priority - Date/Time Handling for LLMs

- [ ] **Add comprehensive date/time conversion tool**
  - [ ] Create `convert_datetime(date_input, timezone='UTC', output_format='youtrack')` tool
  - [ ] Support input formats:
    - ISO 8601: "2025-06-13T10:30:00Z", "2025-06-13T10:30:00-05:00"
    - Simple dates: "2025-06-13", "2025/06/13", "Jun 13, 2025"
    - Relative dates: "yesterday", "last week", "3 days ago", "2 weeks ago"
    - Epoch timestamps: 1718276400 (seconds), 1718276400000 (milliseconds)
    - Human readable: "June 13, 2025", "last Monday", "beginning of this month"
  - [ ] Output formats: YouTrack YQL, ISO 8601, epoch, human readable
  - [ ] Timezone handling with explicit conversion and validation

- [ ] **Add date range validation and suggestion**
  - [ ] Validate date ranges make sense (start_date < end_date)
  - [ ] Suggest reasonable defaults for common queries
  - [ ] Handle timezone-aware date ranges properly
  - [ ] Provide examples of valid date range formats

- [ ] **Add date/time error education for LLMs**
  - [ ] Explain YouTrack's expected date formats in error messages
  - [ ] Show conversion examples: "Your input 'last week' converts to '2025-06-06 .. 2025-06-13'"
  - [ ] Provide timezone guidance: "Times are in UTC unless specified"
  - [ ] Common mistakes: "Use YYYY-MM-DD format, not MM/DD/YYYY"

### Medium Priority - API Best Practices

- [ ] **Implement proper HTTP status code handling**
  - [ ] Check response status codes before processing
  - [ ] Handle different status codes appropriately
  - [ ] Implement retry logic for transient errors

- [ ] **Add request validation**
  - [ ] Validate required parameters before API calls
  - [ ] Validate parameter formats (project names, issue IDs, etc.)
  - [ ] Provide helpful validation error messages

- [ ] **Improve API client robustness**
  - [ ] Add connection pooling
  - [ ] Implement timeout configuration
  - [ ] Add request/response logging for debugging

### Low Priority - Code Quality

- [ ] **Add comprehensive logging**
  - [ ] Replace print statements with proper logging
  - [ ] Add debug-level logging for API calls
  - [ ] Add info-level logging for operations
  - [ ] Add warn-level logging for recoverable errors

- [ ] **Improve parameter handling**
  - [ ] Add parameter aliases for better UX
  - [ ] Implement parameter validation
  - [ ] Add parameter normalization

- [ ] **Add comprehensive tests**
  - [ ] Unit tests for individual tools
  - [ ] Integration tests with mock YouTrack API
  - [ ] Error handling tests

## User Activity Tracking (Use Case: User Touch History)

### High Priority - User Activity Analysis

- [ ] **Add user activity search tool**
  - [ ] Create `get_user_activity(user_login, start_date, end_date, activity_types=None)` tool
  - [ ] Track: created, updated, commented, voted, field changes, state changes
  - [ ] Return: issue list with activity details and timestamps
  - [ ] Support multiple users: `get_users_activity([user1, user2], start_date, end_date)`

- [ ] **Add issue history/activity tools**
  - [ ] Create `get_issue_history(issue_id, start_date=None, end_date=None)` tool
  - [ ] Include: all field changes, comments, votes, attachments, links
  - [ ] Filter by: user, activity type, date range
  - [ ] Format: chronological activity feed with user attribution

- [ ] **Add activity aggregation tools**
  - [ ] Create `get_activity_summary(users, start_date, end_date)` tool
  - [ ] Return: summary stats (issues created, updated, commented on)
  - [ ] Group by: user, project, activity type, time period
  - [ ] Export formats: JSON, CSV for reporting

### High Priority - Organizational Activity Analysis

- [ ] **Add company-wide activity search**
  - [ ] Create `get_company_activity(start_date, end_date, projects=None, limit=500)` tool
  - [ ] Search across ALL projects by default
  - [ ] Return: chronological feed of all significant activity
  - [ ] Include: new issues, major updates, resolutions, critical comments
  - [ ] Performance: Use pagination and smart filtering for large datasets

- [ ] **Add team-based activity search**
  - [ ] Create `get_team_activity(team_users, start_date, end_date, projects=None)` tool
  - [ ] Filter activity by team member list
  - [ ] Cross-project team collaboration tracking
  - [ ] Show: team productivity, cross-team interactions, project contributions

- [ ] **Add smart activity summarization**
  - [ ] Create `get_activity_digest(scope, start_date, end_date, summary_level='high')` tool
  - [ ] Scope: 'company', 'team', 'project', 'user'
  - [ ] Smart filtering: prioritize critical/major changes over minor updates
  - [ ] Summary levels: 'high' (major changes only), 'medium', 'detailed'
  - [ ] Group related activities (e.g., issue creation + immediate updates)

### High Priority - Large-Scale Search Optimization

- [ ] **Add bulk activity search with performance optimization**
  - [ ] Implement parallel project searches for company-wide queries (asyncio.Semaphore(10))
  - [ ] Use YouTrack's comprehensive field queries with activities/comments included
  - [ ] Implement result streaming for large datasets
  - [ ] Add circuit breaker pattern for YouTrack API failures

- [ ] **Add intelligent caching system**
  - [ ] **Redis-based distributed cache** for multi-instance deployments
    - Cache key: `activity:{project_hash}:{start_date}:{end_date}:{summary_level}`
    - TTL: 5-15 minutes (configurable by query scope)
    - Share cache across multiple Claude Code instances
  - [ ] **In-process LRU cache** for single-instance deployments
    - Use `cachetools.TTLCache` for lightweight caching
    - Cache project lists, user groups, field definitions
    - Memory-efficient for smaller deployments
  - [ ] **Multi-layer caching strategy**
    - Layer 1: In-process cache (project metadata, user info) - 1 hour TTL
    - Layer 2: Redis cache (activity results) - 5-15 minute TTL
    - Layer 3: Background job pre-computation (daily/weekly summaries) - 24 hour TTL

- [ ] **Add activity relevance scoring engine**
  - [ ] Score activities by importance (new issues > minor field changes)
  - [ ] Priority multipliers: Critical(3x), High(2x), Normal(1x), Low(0.5x)
  - [ ] Activity weights: issue_created(10), resolved(8), priority_changed(6), comment(3)
  - [ ] Filter noise (automated updates, minor formatting changes)
  - [ ] Summary level thresholds: high(15+), medium(8+), detailed(1+)

### High Priority - Technical Implementation

- [ ] **Implement ActivityAnalyzer core engine**
  - [ ] Create ActivityScorer class with configurable weights/thresholds
  - [ ] Create ActivityGrouper for related activity consolidation
  - [ ] Implement time-window grouping (1-hour windows for related activities)
  - [ ] Add user session detection (group activities by user + time proximity)

- [ ] **Add rate limiting and API optimization**
  - [ ] Implement RateLimitedClient wrapper with exponential backoff
  - [ ] Max 10 concurrent requests to YouTrack API (configurable)
  - [ ] Handle 429 rate limit responses gracefully
  - [ ] Add request timing tracking and adaptive throttling

- [ ] **Add comprehensive activity extraction**
  - [ ] Extract activities from issue history API
  - [ ] Parse comments with author/timestamp attribution
  - [ ] Track field changes with old/new value details
  - [ ] Include vote changes, attachment additions, link modifications
  - [ ] Handle custom field changes with proper type resolution

### Medium Priority - Enhanced Activity Tracking

- [ ] **Add advanced activity filtering**
  - [ ] Filter by project, issue type, priority
  - [ ] Filter by specific field changes (e.g., only status changes)
  - [ ] Include/exclude specific activity types
  - [ ] Cross-reference with custom fields

- [ ] **Add team activity analysis**
  - [ ] Track team productivity metrics
  - [ ] Compare activity across team members
  - [ ] Identify collaboration patterns (who works on same issues)
  - [ ] Track issue handoffs between users

- [ ] **Add contextual activity grouping**
  - [ ] Group related activities (issue + comments + updates)
  - [ ] Detect activity bursts (lots of changes in short time)
  - [ ] Identify cross-project initiatives
  - [ ] Track epic/feature progress across multiple issues

## Custom Field Enhancements

### High Priority

- [ ] **Add generic custom field update capability**
  - [ ] Create `update_custom_field(issue_id, field_name, field_value)` tool
  - [ ] Support all custom field types (text, enum, date, user, multi-value)
  - [ ] Add field value validation

- [ ] **Enhance existing update_issue tool**
  - [ ] Support custom fields alongside built-in fields
  - [ ] Add `custom_fields: Dict[str, str]` parameter
  - [ ] Maintain backward compatibility

### Medium Priority

- [ ] **Add field definition tools**
  - [ ] `get_field_definitions(project)` - Available custom fields for project
  - [ ] `get_field_possible_values(project, field_name)` - Enum/bundle values
  - [ ] `validate_field_value(project, field_name, value)` - Pre-update validation

- [ ] **Improve field value handling**
  - [ ] Better date field parsing/formatting
  - [ ] Improved multi-value field handling
  - [ ] User field lookup by name/email

## Documentation Improvements

### High Priority

- [ ] **Update tool documentation**
  - [ ] Add examples for each tool
  - [ ] Document error conditions
  - [ ] Add parameter validation rules

- [ ] **Create API integration guide**
  - [ ] Authentication setup
  - [ ] Common usage patterns
  - [ ] Error handling examples

### Medium Priority

- [ ] **Add troubleshooting guide**
  - [ ] Common error scenarios
  - [ ] Debug logging setup
  - [ ] Performance optimization tips

## Testing & Validation

### High Priority - Multi-Model Regression Tests

- [ ] **Set up LLM provider test matrix**
  - [ ] Create `tests/providers.py` with provider wrappers (Anthropic, OpenAI, Google, Mistral)
  - [ ] Add `tests/harness/mcp_runner.py` for subprocess stdio testing
  - [ ] Add `tests/harness/judge.py` for JSON schema validation
  - [ ] Create prompt templates in `tests/prompts/` (create_issue.md, search_urgent_issues.md, etc.)
  - Impact: Detect when providers break tool-call formatting or hallucinate parameters

- [ ] **Mock YouTrack API for testing**
  - [ ] Use `respx` to mock `https://dummy.local/youtrack`
  - [ ] Enable CI testing without external API dependencies
  - [ ] Create realistic response fixtures

- [ ] **Add GitHub Actions LLM matrix**
  - [ ] Matrix strategy for multiple providers
  - [ ] Secure API key management via secrets
  - [ ] Fail fast on JSON schema mismatches
  - [ ] Artifact logging for full model responses

### High Priority - MCP Compliance

- [ ] **Add MCP contract tests** (CRITICAL)
  - [ ] Install: `pip install mcp[test]`
  - [ ] Run: `pytest -k mcp_contracts`
  - [ ] Guard against handshake/capability message breakage
  - [ ] Ensure CLI auto-resume compatibility

### Medium Priority

- [ ] **Create comprehensive test suite**
  - [ ] Mock YouTrack API server
  - [ ] Test all tool functions
  - [ ] Test error conditions

- [ ] **Add integration testing**
  - [ ] Test with real YouTrack instance
  - [ ] Validate all tools work end-to-end
  - [ ] Performance testing

- [ ] **Add automated testing**
  - [ ] CI/CD pipeline setup
  - [ ] Automated regression testing
  - [ ] Code quality checks

## Performance Optimizations

### Medium Priority

- [ ] **Optimize API calls**
  - [ ] Implement response caching where appropriate
  - [ ] Batch operations where possible
  - [ ] Reduce redundant field fetching

- [ ] **Improve memory usage**
  - [ ] Stream large result sets
  - [ ] Implement pagination for large queries
  - [ ] Clean up unused objects

## Security Enhancements

### High Priority

- [ ] **Improve authentication handling**
  - [ ] Secure token storage
  - [ ] Token validation
  - [ ] Better error messages for auth failures

- [ ] **Add input validation**
  - [ ] Sanitize user inputs
  - [ ] Validate injection-prone parameters
  - [ ] Implement rate limiting

## Deployment & Operations

### High Priority - Activity Search Configuration

- [ ] **Add caching configuration options**
  - [ ] Environment variables: `CACHE_TYPE` (redis/memory), `REDIS_URL`, `CACHE_TTL`
  - [ ] Fallback gracefully: Redis → in-process → no cache
  - [ ] Cache size limits: `MAX_CACHE_SIZE`, `MAX_CACHE_ENTRIES`
  - [ ] Activity search specific: `ACTIVITY_CACHE_TTL`, `PROJECT_CACHE_TTL`

- [ ] **Add performance tuning configuration**
  - [ ] `MAX_CONCURRENT_REQUESTS` (default: 10) for YouTrack API
  - [ ] `ACTIVITY_SEARCH_TIMEOUT` (default: 30s) for large queries
  - [ ] `MAX_PROJECTS_PER_QUERY` (default: 50) to prevent overload
  - [ ] `DEFAULT_ACTIVITY_LIMIT` (default: 500) for result size control

- [ ] **Add activity search feature flags**
  - [ ] `ENABLE_COMPANY_ACTIVITY_SEARCH` for large-scale queries
  - [ ] `ENABLE_ACTIVITY_CACHING` to disable caching if needed
  - [ ] `ENABLE_PARALLEL_PROJECT_SEARCH` for performance tuning
  - [ ] `ACTIVITY_SCORING_ENABLED` to toggle relevance scoring

### Medium Priority

- [ ] **Add monitoring capabilities**
  - [ ] Health check endpoints
  - [ ] Metrics collection (cache hit rates, search performance)
  - [ ] Performance monitoring (activity search latency, API call counts)
  - [ ] Activity search specific metrics: queries/min, cache efficiency

- [ ] **Improve configuration management**
  - [ ] Configuration validation
  - [ ] Environment-specific configs
  - [ ] Runtime configuration updates

## MCP Resources Integration

### High Priority - Resources vs Tools

- [ ] **Add MCP Resources for documentation and configuration**
  - [ ] Create `mcp_resources.py` module for resource handling
  - [ ] Add YouTrack query syntax guide as `youtrack://query-syntax` resource
  - [ ] Add available field definitions as `youtrack://project/{id}/fields` resource
  - [ ] Add project list as `youtrack://projects` resource
  - [ ] Add user directory as `youtrack://users` resource
  - Impact: Provides context to LLMs without consuming tool slots

- [ ] **Implement dual resource/tool strategy**
  - [ ] Use Resources for: documentation, field schemas, project metadata
  - [ ] Use Tools for: actions, searches, updates, issue operations
  - [ ] Add resource refresh capability with TTL caching
  - Pros: Better context, reduced tool complexity, cacheable reference data
  - Cons: Additional implementation complexity, need resource management

- [ ] **Add resource-aware error handling**
  - [ ] Reference available resources in error messages
  - [ ] Suggest relevant resources for common error scenarios
  - [ ] Auto-refresh stale resource data when errors indicate schema changes

## Long-term Enhancements (Based on Technical Review)

### Medium Priority - Modern Tooling

- [ ] **Add async rate-limiting**
  - [ ] Wrap `httpx.AsyncClient` in `http-toolkit/ratelimit`
  - [ ] Prevent bursts from tripping YouTrack quotas
  - [ ] Configurable rate limits per endpoint

- [ ] **Implement tool discovery endpoint**
  - [ ] Add dynamic schema extension (`tool_discovery/listTools`)
  - [ ] Support MCP v1.7 proposals
  - [ ] Enable `/mcp refresh` without restart

- [ ] **Switch to modern Python packaging**
  - [ ] Move build metadata to `pyproject.toml`
  - [ ] Use Hatch for publishing
  - [ ] Single version field for image tag + Python wheel

- [ ] **Modernize code quality tools**
  - [ ] Replace flake8 + isort with ruff + black
  - [ ] Add pre-commit CI hooks
  - [ ] Faster linting and formatting

### Low Priority - Advanced Integrations

- [ ] **Add LangChain adapter support**
  - [ ] Use `langchain-mcp-adapters 0.1.7`
  - [ ] Expose YouTrack tools in agent graphs
  - [ ] Enable automated regression triage

- [ ] **Advanced features**
  - [ ] Workflow automation tools
  - [ ] Report generation
  - [ ] Bulk operations
  - [ ] Export/import capabilities

- [ ] **Integration improvements**
  - [ ] Better Claude Code CLI integration
  - [ ] WebHook support
  - [ ] Real-time notifications

## Implementation Order (Recommended)

### Phase 1: Critical Fixes (Week 1)
1. **Switch to httpx.AsyncClient** - Biggest performance impact
2. **Add MCP compliance tests** - Prevent CLI auto-resume breakage  
3. **Fix token security** - Security risk
4. **Fix Pydantic v2 migration** - Runtime warnings
**Dependencies:** None
**Success Metrics:** All async calls use httpx, compliance tests pass, token loaded per-request
**Risk Mitigation:** Test with existing FastAPI endpoints, backup current implementation

### Phase 2: Claude CLI Compatibility (Week 2)
1. **Fast handshake for auto-resume** - Critical for reliability
2. **Structured JSON logging** - Better debugging
3. **MCP_TIMEOUT support** - Prevent startup kills
4. **Project-scoped .mcp.json examples** - Better UX
**Dependencies:** Phase 1 MCP compliance tests
**Success Metrics:** <2s handshake time, JSON logs parseable, examples in README
**Risk Mitigation:** Test auto-resume scenarios, validate log format compatibility

### Phase 3: Exception Handling & MCP Resources (Week 3)
1. **Replace generic exceptions** - Bot feedback priority
2. **Add structured error responses** - Better error UX
3. **Implement MCP Resources** - Context without tool slots
4. **HTTP status code handling** - API robustness
**Dependencies:** Phase 2 logging infrastructure
**Success Metrics:** Specific exceptions for all error types, resources accessible to LLMs
**Risk Mitigation:** Maintain backward compatibility, test error scenarios extensively

### Phase 4: Custom Fields & Activity Tracking (Week 4)
1. **Generic custom field updates** - User priority feature
2. **Enhanced field handling** - Core functionality
3. **User activity search tools** - Core functionality
4. **Date/time conversion utilities** - LLM usability
**Dependencies:** Phase 3 error handling, MCP Resources for field schemas
**Success Metrics:** All custom field types supported, activity search working
**Risk Mitigation:** Test with diverse project configurations, validate date parsing

### Phase 5: Performance & Testing (Week 5)
1. **Implement caching strategy** - Performance for activity searches
2. **Multi-model regression tests** - Quality assurance
3. **Harden Dockerfile** - Security compliance
4. **Activity summarization engine** - Advanced features
**Dependencies:** Phase 4 activity tracking, stable API patterns
**Success Metrics:** <5s company-wide searches, all LLM providers pass tests
**Risk Mitigation:** Cache fallback strategies, performance baseline measurements

## Code Examples from Technical Review

### LLM-Optimized Error Response Format
```python
def create_llm_friendly_error(operation: str, error: Exception, context: dict) -> dict:
    """Create detailed error response optimized for LLM learning."""
    
    if isinstance(error, YouTrackQuerySyntaxError):
        return {
            "error": f"YouTrack query syntax error in {operation}",
            "details": f"Invalid query: '{context.get('query', 'unknown')}'",
            "youtrack_error": str(error),
            "explanation": "YouTrack Query Language (YQL) syntax is case-sensitive and requires exact field names.",
            "correct_example": "project: MYPROJECT assignee: john.doe state: Open",
            "recommendation": "In the future, ensure project names match exactly (case-sensitive) and use valid field names. Check spelling carefully.",
            "operation_attempted": operation,
            "parameters_used": context,
            "suggested_fix": generate_corrected_query(context.get('query', '')),
            "learn_from_this": "Remember: YouTrack field names are case-sensitive. Common fields: project, assignee, state, priority, created, updated."
        }
    
    elif isinstance(error, ProjectNotFoundError):
        similar_projects = find_similar_project_names(context.get('project', ''))
        return {
            "error": f"Project not found in {operation}",
            "details": f"Project '{context.get('project', 'unknown')}' does not exist",
            "explanation": "Project names in YouTrack are case-sensitive short names (keys), not display names.",
            "did_you_mean": similar_projects,
            "recommendation": f"Use one of these valid project keys: {', '.join(similar_projects[:5])}. In the future, verify project names before using them in queries.",
            "how_to_check": "Use get_projects() tool to see all available project keys",
            "learn_from_this": "Always use project 'shortName' (key) not 'name' (display name) in queries."
        }
    
    elif isinstance(error, CustomFieldNotFoundError):
        available_fields = get_project_custom_fields(context.get('project', ''))
        return {
            "error": f"Custom field not found in {operation}",
            "details": f"Field '{context.get('field_name', 'unknown')}' not available in project",
            "available_fields": [f["name"] for f in available_fields],
            "explanation": "Custom fields are project-specific and case-sensitive",
            "recommendation": f"Use one of the available custom fields for this project. In the future, check available fields with get_custom_fields(project) first.",
            "correct_syntax": "Use curly braces for custom fields: {Custom Field Name}: value",
            "learn_from_this": "Custom field names must match exactly and use {Field Name}: value syntax in queries."
        }

# Example usage in tool functions:
@mcp.tool()
def search_issues(query: str, limit: int = 10) -> Dict[str, Any]:
    try:
        # ... existing logic
        return results
    except YouTrackAPIError as e:
        # Return YouTrack's error as-is, but add educational context
        return {
            "error": "YouTrack API Error",
            "youtrack_error": str(e),  # Preserve original error
            "youtrack_status_code": getattr(e, 'status_code', None),
            "operation": "search_issues", 
            "query_used": query,
            "explanation": "YouTrack rejected the query. This usually means syntax issues.",
            "common_query_fixes": {
                "spelling": "Check project names are exact (case-sensitive): 'project: MYPROJECT'",
                "operators": "Use colons not equals: 'assignee: john.doe' not 'assignee = john.doe'",
                "dates": "Use YYYY-MM-DD format: 'created: 2025-06-13' or relative: 'created: -7d .. *'",
                "custom_fields": "Use braces for custom fields: '{Priority}: High'"
            },
            "recommendation": "Check the youtrack_error for specifics. Use convert_datetime() for date issues.",
            "learn_from_this": "YouTrack's error messages are authoritative. Learn the correct syntax from them."
        }
    except Exception as e:
        # Log full traceback for developers
        logger.exception(f"Unexpected error in search_issues: {e}")
        
        # Return LLM-friendly generic error
        return {
            "error": "Unexpected error in search_issues",
            "details": str(e),
            "explanation": "An unexpected error occurred while searching for issues",
            "recommendation": "Try simplifying your query or check if all parameters are valid. If the error persists, this may be a system issue.",
            "operation_attempted": "search_issues",
            "parameters_used": {"query": query, "limit": limit},
            "troubleshooting": "Verify your query syntax and ensure all referenced projects/users exist."
        }
```

### Date/Time Conversion for LLMs
```python
from datetime import datetime, timezone, timedelta
import dateutil.parser
import re

@mcp.tool()
def convert_datetime(date_input: str, timezone_str: str = "UTC", output_format: str = "youtrack") -> Dict[str, Any]:
    """
    Convert various date/time formats to YouTrack-compatible format.
    
    Args:
        date_input: Date in various formats (ISO, relative, epoch, human readable)
        timezone_str: Timezone for interpretation (default: UTC)
        output_format: Output format (youtrack, iso8601, epoch, human)
        
    Returns:
        Converted date with examples and explanations
    """
    try:
        converted_date = normalize_datetime(date_input, timezone_str)
        
        result = {
            "input": date_input,
            "converted": {
                "youtrack": converted_date.strftime("%Y-%m-%d"),
                "youtrack_with_time": converted_date.strftime("%Y-%m-%d %H:%M"),
                "iso8601": converted_date.isoformat(),
                "epoch": int(converted_date.timestamp()),
                "epoch_ms": int(converted_date.timestamp() * 1000),
                "human": converted_date.strftime("%B %d, %Y at %H:%M UTC"),
            },
            "timezone_used": timezone_str,
            "explanation": f"Converted '{date_input}' to {converted_date.strftime('%Y-%m-%d')} in {timezone_str}",
            "youtrack_usage_examples": [
                f"created: {converted_date.strftime('%Y-%m-%d')} .. *",
                f"updated: * .. {converted_date.strftime('%Y-%m-%d')}",
                f"created: {converted_date.strftime('%Y-%m-%d')} .. {(converted_date + timedelta(days=7)).strftime('%Y-%m-%d')}"
            ]
        }
        
        return result
        
    except Exception as e:
        return create_datetime_error_response(date_input, str(e))

def normalize_datetime(date_input: str, timezone_str: str = "UTC") -> datetime:
    """Normalize various date inputs to datetime object."""
    
    # Handle relative dates
    relative_patterns = {
        r'\byesterday\b': lambda: datetime.now(timezone.utc) - timedelta(days=1),
        r'\btoday\b': lambda: datetime.now(timezone.utc),
        r'\blast week\b': lambda: datetime.now(timezone.utc) - timedelta(weeks=1),
        r'\bthis week\b': lambda: datetime.now(timezone.utc) - timedelta(days=datetime.now().weekday()),
        r'\blast month\b': lambda: datetime.now(timezone.utc) - timedelta(days=30),
        r'\b(\d+)\s+days?\s+ago\b': lambda m: datetime.now(timezone.utc) - timedelta(days=int(m.group(1))),
        r'\b(\d+)\s+weeks?\s+ago\b': lambda m: datetime.now(timezone.utc) - timedelta(weeks=int(m.group(1))),
        r'\b(\d+)\s+months?\s+ago\b': lambda m: datetime.now(timezone.utc) - timedelta(days=int(m.group(1)) * 30),
    }
    
    date_input_lower = date_input.lower().strip()
    
    # Check relative patterns
    for pattern, func in relative_patterns.items():
        match = re.search(pattern, date_input_lower)
        if match:
            if callable(func):
                return func() if 'lambda' in str(func) and match.groups() == () else func(match)
    
    # Handle epoch timestamps
    if date_input.isdigit():
        timestamp = int(date_input)
        # Detect if it's milliseconds (> year 2001 in seconds)
        if timestamp > 1000000000000:  # Milliseconds
            return datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc)
        else:  # Seconds
            return datetime.fromtimestamp(timestamp, tz=timezone.utc)
    
    # Handle ISO and other standard formats
    try:
        # Use dateutil.parser for flexible parsing
        parsed_date = dateutil.parser.parse(date_input)
        
        # If no timezone info, assume specified timezone
        if parsed_date.tzinfo is None:
            target_tz = timezone.utc if timezone_str == "UTC" else timezone.utc  # Extend for other timezones
            parsed_date = parsed_date.replace(tzinfo=target_tz)
        
        return parsed_date.astimezone(timezone.utc)
        
    except Exception:
        raise ValueError(f"Could not parse date: {date_input}")

def create_datetime_error_response(date_input: str, error_msg: str) -> Dict[str, Any]:
    """Create educational error response for date/time parsing failures."""
    
    return {
        "error": f"Could not parse date/time: '{date_input}'",
        "details": error_msg,
        "explanation": "YouTrack accepts specific date formats and LLMs often struggle with date conversions",
        "supported_formats": {
            "ISO_8601": ["2025-06-13", "2025-06-13T10:30:00Z", "2025-06-13T10:30:00-05:00"],
            "Simple_dates": ["2025-06-13", "2025/06/13", "Jun 13, 2025", "June 13, 2025"],
            "Relative_dates": ["yesterday", "last week", "3 days ago", "2 weeks ago", "last Monday"],
            "Epoch_timestamps": ["1718276400 (seconds)", "1718276400000 (milliseconds)"],
            "YouTrack_ranges": ["2025-06-01 .. 2025-06-13", "-7d .. *", "* .. 2025-06-13"]
        },
        "examples": {
            "last_week_range": "Use: created: -7d .. * (last 7 days)",
            "specific_date": "Use: created: 2025-06-13 (specific day)",
            "date_range": "Use: created: 2025-06-01 .. 2025-06-13 (range)",
            "relative_youtrack": "Use: updated: -1w .. * (last week in YouTrack syntax)"
        },
        "recommendation": "Use the convert_datetime() tool first to validate and convert your date input before using it in queries.",
        "learn_from_this": "Always validate dates with convert_datetime() tool. YouTrack uses YYYY-MM-DD format and supports relative dates like '-7d' for last 7 days.",
        "common_mistakes": [
            "MM/DD/YYYY format (use YYYY-MM-DD instead)",
            "Ambiguous relative dates (be specific: '7 days ago' not 'last week')",
            "Missing timezone context (specify timezone or use UTC)",
            "Mixing epoch seconds vs milliseconds"
        ]
    }

# Enhanced activity search with automatic date conversion
@mcp.tool()
def get_user_activity_smart(user_login: str, start_date: str, end_date: str, 
                           timezone_str: str = "UTC") -> Dict[str, Any]:
    """
    Get user activity with automatic date conversion and validation.
    
    Args:
        user_login: User login name
        start_date: Start date (flexible format: ISO, relative, epoch, human)
        end_date: End date (flexible format)
        timezone_str: Timezone for date interpretation
        
    Returns:
        User activity with converted dates and explanations
    """
    try:
        # Convert and validate dates
        start_converted = normalize_datetime(start_date, timezone_str)
        end_converted = normalize_datetime(end_date, timezone_str)
        
        # Validate date range
        if start_converted >= end_converted:
            return {
                "error": "Invalid date range",
                "details": f"Start date ({start_converted.strftime('%Y-%m-%d')}) must be before end date ({end_converted.strftime('%Y-%m-%d')})",
                "explanation": "Date ranges must have start_date < end_date",
                "corrected_suggestion": f"Try: start_date='{(end_converted - timedelta(days=7)).strftime('%Y-%m-%d')}', end_date='{end_converted.strftime('%Y-%m-%d')}'",
                "learn_from_this": "Always ensure your date range is logical with start before end"
            }
        
        # Build YouTrack query with converted dates
        youtrack_start = start_converted.strftime("%Y-%m-%d")
        youtrack_end = end_converted.strftime("%Y-%m-%d")
        
        # Execute the actual search
        results = get_user_activity(user_login, youtrack_start, youtrack_end)
        
        # Add conversion info to results
        if isinstance(results, dict) and "error" not in results:
            results["date_conversion"] = {
                "input_start": start_date,
                "input_end": end_date,
                "converted_start": youtrack_start,
                "converted_end": youtrack_end,
                "timezone_used": timezone_str,
                "youtrack_query_used": f"updated: {youtrack_start} .. {youtrack_end}"
            }
        
        return results
        
    except Exception as e:
        return create_datetime_error_response(f"start_date='{start_date}', end_date='{end_date}'", str(e))
```

### YouTrack Query Validation and Correction
```python
def validate_and_correct_youtrack_query(query: str, project_context: str = None) -> dict:
    """Pre-validate YouTrack queries and suggest corrections."""
    
    corrections = []
    warnings = []
    
    # Common typos and corrections
    query_corrections = {
        r'\bprojet\b': 'project',  # Common typo
        r'\bassignee\s*=\s*': 'assignee: ',  # Wrong operator
        r'\bstate\s*=\s*': 'state: ',  # Wrong operator
        r'\bpriority\s*=\s*': 'priority: ',  # Wrong operator
    }
    
    corrected_query = query
    for pattern, replacement in query_corrections.items():
        if re.search(pattern, query, re.IGNORECASE):
            corrected_query = re.sub(pattern, replacement, corrected_query, flags=re.IGNORECASE)
            corrections.append(f"Changed '{pattern}' to '{replacement}'")
    
    # Note: We don't pre-validate dates - let YouTrack be authoritative
    # Date validation happens post-error with educational context
    # Validate field references
    custom_field_pattern = r'\{([^}]+)\}'
    custom_fields = re.findall(custom_field_pattern, query)
    
    if project_context and custom_fields:
        available_fields = get_project_custom_fields(project_context)
        available_names = [f["name"] for f in available_fields]
        
        for field in custom_fields:
            if field not in available_names:
                similar = find_similar_field_names(field, available_names)
                if similar:
                    warnings.append(f"Custom field '{field}' not found. Did you mean '{similar[0]}'?")
    
    return {
        "original_query": query,
        "corrected_query": corrected_query,
        "corrections_made": corrections,
        "warnings": warnings,
        "is_valid": len(warnings) == 0
    }
```

### httpx.AsyncClient Implementation
```python
# In main.py lifespan event
async def lifespan(app: FastAPI):
    # Startup
    async with httpx.AsyncClient() as client:
        app.state.http_client = client
        yield
    # Shutdown - client auto-closes
```

### Fast Handshake for Auto-Resume
```python
# Ensure immediate flush in main.py
print(json.dumps(handshake_msg), flush=True)
```

### Systemd User Unit Template
```ini
# ~/.config/systemd/user/youtrack-mcp.service
[Unit]
Description=YouTrack MCP (stdio)
After=network.target

[Service]
Environment=YOUTRACK_URL=https://your.youtrack.cloud
Environment=YOUTRACK_API_TOKEN=perm:XXXX
Environment=MCP_TIMEOUT=15000
ExecStart=podman run --rm -i --name youtrack-mcp --user 10001:10001 docker.io/yourrepo/youtrack-mcp:latest
Restart=on-failure

[Install]
WantedBy=default.target
```

## Technical Implementation Research Needed

### API Research Requirements
- [ ] **YouTrack Activities API investigation**
  - Research: Does `/api/activities` endpoint exist? What fields are available?
  - Alternative: Use `/api/issues/{id}/activities` per-issue approach
  - Fallback: Parse issue history changes for activity extraction

- [ ] **Custom field type handling research**
  - Research: Complete list of YouTrack custom field types and their API representations
  - Test: Multi-value fields, user fields, date fields, enum fields
  - Document: Conversion patterns for each field type

- [ ] **Rate limiting and pagination research**
  - Research: YouTrack API rate limits, burst allowances, retry-after headers
  - Test: Large result set pagination patterns
  - Document: Optimal batch sizes for different operation types

## Success Metrics & Validation

### Phase Success Criteria
- **Phase 1:** All existing functionality works with httpx, 100% MCP compliance test pass
- **Phase 2:** Auto-resume success rate >95%, structured logs parseable by standard tools
- **Phase 3:** LLM error resolution rate >80%, resources accessible in Claude Code
- **Phase 4:** Support for all custom field types in use, activity search <10s response
- **Phase 5:** Company-wide searches complete in <30s, regression test coverage >90%

### Risk Mitigation Strategies
- **API Changes:** Mock YouTrack responses for testing, version compatibility checks
- **Performance Degradation:** Baseline measurements, performance budgets, rollback plans
- **Breaking Changes:** Semantic versioning, deprecation warnings, migration guides
- **Memory Issues:** Memory profiling, cache size limits, garbage collection monitoring

## 🚀 NEW ENHANCEMENT ROADMAP - AI-Powered YouTrack Assistant

### **Phase A: Local AI Integration Foundation** (Priority: HIGH)

- [ ] **Local AI Inference Engine Setup**
  - [ ] Integrate lightweight CPU-optimized models (DeepSeek-7B 4-bit, DistilBERT)
  - [ ] Create `LocalAIProcessor` class for query enhancement and error processing
  - [ ] Implement model loading with memory optimization (<2GB RAM usage)
  - [ ] Add configurable AI features (enable/disable per deployment)

- [ ] **Smart Error Enhancement System**
  - [ ] AI-powered error message improvement with learning context
  - [ ] Context-aware query syntax correction using local inference
  - [ ] Smart "did you mean" suggestions for field names and projects
  - [ ] Error pattern learning from user interactions

### **Phase B: Intelligent Query Processing** (Priority: HIGH)

- [ ] **Natural Language to YQL Translation**
  - [ ] Create `smart_search_issues()` tool with natural language input
  - [ ] AI-powered query translation: "Show me critical bugs from last week" → YQL
  - [ ] Context-aware project detection from conversation history
  - [ ] Confidence scoring for query translations

- [ ] **Advanced Caching with AI Prefetch**
  - [ ] Multi-layer caching: Redis + in-process + background jobs
  - [ ] AI-powered cache prefetch based on usage patterns
  - [ ] Smart cache invalidation using activity monitoring
  - [ ] Performance optimization: <5s company-wide searches

### **Phase C: Predictive Analytics & Intelligence** (Priority: MEDIUM)

- [ ] **Smart Issue Management**
  - [ ] AI-powered issue priority prediction based on content analysis
  - [ ] Resolution time estimation using historical patterns
  - [ ] Similar issue detection with semantic matching
  - [ ] Automated issue categorization and tagging suggestions

- [ ] **Advanced Activity Analytics**
  - [ ] `analyze_user_patterns()` tool with AI insights
  - [ ] Team productivity analysis with collaboration patterns
  - [ ] Predictive workload balancing suggestions
  - [ ] Cross-project activity correlation analysis

### **Phase D: Enhanced User Experience** (Priority: MEDIUM)

- [ ] **Context-Aware Operations**
  - [ ] Smart project context detection from conversation
  - [ ] User preference learning for common operations
  - [ ] Intelligent field suggestions based on project schema
  - [ ] Auto-completion for repetitive tasks

- [ ] **Advanced Reporting & Summarization**
  - [ ] `generate_intelligent_report()` with AI-generated insights
  - [ ] Executive summaries with actionable recommendations
  - [ ] Trend analysis with predictive insights
  - [ ] Custom report generation based on natural language requests

### **Phase E: Advanced Integration & Optimization** (Priority: LOW)

- [ ] **Performance & Scalability**
  - [ ] Distributed cache architecture for multi-instance deployments
  - [ ] Advanced rate limiting with intelligent batching
  - [ ] Memory optimization for large-scale deployments
  - [ ] Performance monitoring with AI-driven optimization

- [ ] **Extended Integrations**
  - [ ] LangChain adapter support for agent workflows
  - [ ] WebHook integration for real-time updates
  - [ ] Advanced notification system with smart filtering
  - [ ] Export/import capabilities with data validation

## Implementation Priority Order (UPDATED)

### **Phase 1: ID Consistency + Core AI (Week 1)** ✅ COMPLETED + NEW
1. ✅ **ID consistency fixes** - COMPLETED
2. **Local AI inference engine** - CPU-optimized setup
3. **Smart error enhancement** - AI-powered error processing
4. **httpx.AsyncClient migration** - Performance improvement

### **Phase 2: Query Intelligence (Week 2)**
1. **Natural language query translation** - AI-powered YQL generation
2. **Context-aware validation** - Smart query correction
3. **Intelligent caching system** - AI prefetch optimization
4. **MCP compliance testing** - Reliability assurance

### **Phase 3: Analytics & Insights (Week 3)**
1. **Activity pattern analysis** - AI-driven user insights
2. **Predictive issue management** - Priority/time predictions
3. **Smart reporting system** - Automated report generation
4. **Advanced search capabilities** - Semantic matching

### **Phase 4: Experience Enhancement (Week 4)**
1. **Context detection system** - Conversation-aware operations
2. **User preference learning** - Adaptive behavior
3. **Intelligent field suggestions** - Schema-aware recommendations
4. **Performance optimization** - Multi-layer caching

### **Phase 5: Advanced Features (Week 5)**
1. **Distributed architecture** - Multi-instance support
2. **Advanced integrations** - LangChain, WebHooks
3. **Scalability improvements** - Enterprise-ready features
4. **Comprehensive testing** - Multi-model regression tests

## Key Innovation: Local AI Integration

The major enhancement is integrating **lightweight local AI models** for:

1. **Real-time query enhancement** without external API calls
2. **Context-aware error messaging** that learns from user patterns  
3. **Intelligent argument validation** before YouTrack API hits
4. **Natural language interface** for non-technical users
5. **Predictive insights** based on activity analysis

This transforms the MCP from a simple API wrapper into a **smart YouTrack assistant** while maintaining **privacy** (no external AI calls) and **performance** (CPU inference with quantized models).

## Notes

- ✅ **ID Consistency**: Completed - all tools now consistently return human-readable IDs
- Priority levels based on upstream technical review and bot feedback
- Phase 1 addresses performance and stability issues flagged by bot
- Exception handling improvements come after critical async fixes
- Custom fields remain high priority due to user usage patterns
- Focus on backward compatibility for all changes
- Each phase builds on previous phase's improvements
- MCP Resources provide context without consuming limited tool slots
- Activity tracking requires significant API research and optimization
- **NEW**: Local AI integration provides immediate value while maintaining privacy