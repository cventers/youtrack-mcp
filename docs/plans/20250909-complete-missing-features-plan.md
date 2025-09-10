# Plan: Complete Missing Features and TODO Items - 2025-09-09

## Executive Summary
This plan addresses all incomplete features and TODO items identified in the YouTrack MCP codebase. Based on analysis of the TODO.md file and codebase inspection, we've identified 21 major features that need completion, ranging from critical async migration to advanced AI features.

## Objectives
- Complete all high-priority critical fixes (async migration, security, compatibility)
- Implement missing core functionality (custom fields, activity tracking, MCP resources)
- Add advanced AI capabilities for better user experience
- Improve error handling and LLM optimization
- Enhance testing and deployment infrastructure

## Current Status Assessment
- **Completed**: ID consistency fixes, modular architecture refactoring
- **Partially Implemented**: Core tools (issues, projects, search, users, AI)
- **Missing/Incomplete**: 21 features across 5 priority levels

## Implementation Phases

### Phase 1: Critical Infrastructure Fixes (Week 1)
**Priority**: HIGH - These are blocking issues that affect core functionality

#### 1.1 Async Migration & Performance
- [ ] **httpx.AsyncClient Migration**
  - Replace blocking `requests` library with `httpx.AsyncClient`
  - Update `youtrack_mcp/api/client.py` lifespan event in `main.py`
  - Impact: Eliminates thread-pool overhead, better FastAPI scaling
  - Files: `youtrack_mcp/api/client.py`, `main.py`

- [ ] **Token Security Enhancement**
  - Implement lazy loading per request instead of process lifetime
  - Reduce memory exposure of sensitive tokens
  - Files: `config.py`, `youtrack_mcp/api/client.py`

#### 1.2 Compatibility & Standards
- [ ] **MCP Compliance Testing**
  - Install `pip install mcp[test]`
  - Run `pytest -k mcp_contracts`
  - Guard against handshake/capability message breakage
  - Risk: CLI auto-resume failures

- [ ] **Pydantic v2 Migration**
  - Remove v1 validators (`@validator`)
  - Run `pydantic codemod`
  - Fix runtime warnings and faster model parsing
  - Files: All model definitions

#### 1.3 Claude Code CLI Compatibility
- [ ] **Fast Handshake Implementation**
  - Flush handshake JSON immediately: `print(json.dumps(msg), flush=True)`
  - Ensure <2s handshake time for session auto-resume
  - Files: `main.py` startup sequence

- [ ] **Structured JSON Logging**
  - Replace print statements with `structlog`
  - Enable better debugging with Claude Code's `/mcp debug` command
  - Files: All logging throughout codebase

- [ ] **MCP_TIMEOUT Support**
  - Handle `MCP_TIMEOUT` environment variable
  - Prevent early server kills on slow startup
  - Update Podman/systemd examples

### Phase 2: Core Functionality Enhancement (Week 2-3)
**Priority**: HIGH - Essential features for production use

#### 2.1 Exception Handling & Error Management
- [ ] **Specific Exception Types**
  - Replace `except Exception as e:` with specific exceptions
  - Add HTTP, API, validation, network, and server exceptions
  - Files: `main.py` (all @mcp.tool() functions)

- [ ] **LLM-Optimized Error Responses**
  - Add descriptive error messages for LLM learning
  - Include what went wrong, why it failed, and how to fix it
  - Provide examples of correct syntax/usage
  - Give guidance for future attempts

#### 2.2 Date/Time Handling for LLMs
- [ ] **Comprehensive Date Conversion Tool**
  - Create `convert_datetime()` tool for LLM date inputs → YouTrack format
  - Support ISO 8601, relative dates, epoch timestamps, human readable
  - Handle timezones and validation
  - Let YouTrack validate its own date syntax in queries

#### 2.3 MCP Resources Integration
- [ ] **Resources for Documentation**
  - Add `mcp_resources.py` module
  - Create `youtrack://query-syntax` resource for YQL guide
  - Add `youtrack://project/{id}/fields` for field definitions
  - Add `youtrack://projects` and `youtrack://users` resources
  - Impact: Context without consuming limited tool slots

### Phase 3: Advanced Features (Week 4-5)
**Priority**: HIGH/MEDIUM - Enhanced user experience

#### 3.1 Custom Fields Support
- [ ] **Generic Custom Field Updates**
  - Create `update_custom_field()` tool
  - Support all custom field types (text, enum, date, user, multi-value)
  - Add field value validation
  - Enhance existing `update_issue` tool

#### 3.2 Activity Tracking & Analysis
- [ ] **User Activity Search Tools**
  - Create `get_user_activity()` tool with date ranges
  - Add `get_issue_history()` for activity feeds
  - Implement `get_activity_summary()` for aggregations
  - Add company-wide and team activity searches

#### 3.3 AI-Powered Features
- [ ] **Local AI Inference Engine**
  - Integrate CPU-optimized models (DeepSeek-7B 4-bit, DistilBERT)
  - Create `LocalAIProcessor` class for query enhancement
  - Implement model loading with memory optimization (<2GB RAM)

- [ ] **Natural Language to YQL Translation**
  - Create `smart_search_issues()` tool with natural language input
  - AI-powered query translation: "Show me critical bugs from last week"
  - Context-aware project detection from conversation history

### Phase 4: Performance & Testing (Week 6)
**Priority**: MEDIUM - Quality assurance and optimization

#### 4.1 Caching & Performance
- [ ] **Intelligent Caching System**
  - Multi-layer caching: Redis + in-process + background jobs
  - AI-powered cache prefetch based on usage patterns
  - Smart cache invalidation using activity monitoring
  - Performance optimization: <5s company-wide searches

#### 4.2 Testing Infrastructure
- [ ] **Multi-Model Regression Tests**
  - Set up LLM provider test matrix (Anthropic, OpenAI, Google, Mistral)
  - Create `tests/providers.py` with provider wrappers
  - Add `tests/harness/mcp_runner.py` for subprocess stdio testing
  - Add `tests/harness/judge.py` for JSON schema validation

#### 4.3 Security & Deployment
- [ ] **Docker Security Hardening**
  - Run as non-root UID 10001
  - Add `--chown` on copy, `USER 10001`
  - Reduce CVE scanner noise in supply-chain reviews

### Phase 5: Advanced Optimizations (Week 7-8)
**Priority**: LOW/MEDIUM - Future enhancements

#### 5.1 Advanced AI Features
- [ ] **AI Error Enhancement**
  - AI-powered error message improvement with learning context
  - Context-aware query syntax correction using local inference
  - Smart "did you mean" suggestions for field names and projects

- [ ] **Activity Pattern Analysis**
  - Add relevance scoring engine (new issues > minor field changes)
  - Implement time-window grouping for related activities
  - Add user session detection and productivity analysis

#### 5.2 Infrastructure Improvements
- [ ] **Rate Limiting & API Optimization**
  - Wrap `httpx.AsyncClient` in rate limiting
  - Implement exponential backoff for API failures
  - Add request timing tracking and adaptive throttling

- [ ] **Comprehensive Logging**
  - Replace print statements with proper logging
  - Add debug-level logging for API calls
  - Add info-level logging for operations

## Success Metrics

### Phase Success Criteria
- **Phase 1**: All async calls use httpx, MCP compliance tests pass, token loaded per-request
- **Phase 2**: Specific exceptions for all error types, resources accessible to LLMs
- **Phase 3**: All custom field types supported, activity search working
- **Phase 4**: Company-wide searches complete in <30s, all LLM providers pass tests
- **Phase 5**: Advanced AI features working, rate limiting prevents API throttling

### Risk Mitigation Strategies
- **API Changes**: Mock YouTrack responses for testing, version compatibility checks
- **Performance Degradation**: Baseline measurements, performance budgets, rollback plans
- **Breaking Changes**: Semantic versioning, deprecation warnings, migration guides
- **Memory Issues**: Memory profiling, cache size limits, garbage collection monitoring

## Dependencies & Prerequisites

### Required Before Starting
1. **Environment Setup**: Ensure uv/virtual environment is properly configured
2. **API Access**: Valid YouTrack instance with API token for testing
3. **Dependencies**: All Python packages installed via `uv pip install -e .`

### Phase Dependencies
- Phase 2 depends on Phase 1 MCP compliance tests
- Phase 3 depends on Phase 2 error handling infrastructure
- Phase 4 depends on Phase 3 activity tracking for performance testing
- Phase 5 depends on Phase 4 stable API patterns

## Implementation Notes

### Code Quality Standards
- **Exception Handling**: No more `except Exception as e:` - use specific exceptions
- **Async Best Practices**: All HTTP calls must use `httpx.AsyncClient`
- **Security**: Lazy token loading, no secrets in logs
- **LLM Optimization**: Error messages should help LLMs learn and improve

### Testing Strategy
- **MCP Compliance**: Required for Claude Code CLI compatibility
- **Multi-Model Testing**: Detect when providers break tool-call formatting
- **Mock API**: Use `respx` for YouTrack API mocking in CI
- **Performance Baselines**: Measure before/after for all optimizations

### Documentation Updates
- Update tool documentation with examples for each tool
- Document error conditions and parameter validation rules
- Create API integration guide and troubleshooting documentation

## Timeline & Milestones

### Week 1: Infrastructure Foundation
- Complete async migration and token security
- Fix Pydantic v2 issues
- Implement MCP compliance testing

### Week 2: Core Compatibility
- Add Claude CLI compatibility features
- Implement specific exception handling
- Create LLM-optimized error responses

### Week 3: Advanced Functionality
- Add date/time conversion tools
- Implement MCP Resources
- Complete custom field support

### Week 4: AI & Activity Features
- Add local AI inference engine
- Implement activity tracking tools
- Create natural language query translation

### Week 5: Performance & Testing
- Implement intelligent caching
- Add multi-model regression tests
- Harden Docker security

### Week 6-7: Advanced Features
- Complete AI error enhancement
- Add activity pattern analysis
- Implement rate limiting

### Week 8: Finalization
- Comprehensive logging
- Systemd deployment examples
- Final testing and documentation

## Risk Assessment

### High Risk Items
1. **Async Migration**: Could break existing functionality if not done carefully
2. **MCP Compliance**: Critical for Claude Code CLI integration
3. **Token Security**: Must not break authentication flow

### Mitigation Strategies
- **Incremental Changes**: Test each change individually before committing
- **Rollback Plans**: Keep backup of working versions
- **Comprehensive Testing**: Both unit and integration tests for all changes
- **Gradual Rollout**: Deploy changes in phases with monitoring

## Conclusion

This plan provides a comprehensive roadmap for completing all missing features in the YouTrack MCP server. The phased approach ensures that critical infrastructure issues are addressed first, followed by feature enhancements and performance optimizations. Success will result in a robust, AI-enhanced YouTrack integration that provides excellent user experience for both human users and LLM assistants.

The plan prioritizes stability and compatibility while adding powerful new capabilities that will make the YouTrack MCP server a leading example of MCP implementation excellence.