# Tool Surface Refactor Plan - YouTrack MCP Server

**Date**: 2025-09-06  
**Version**: 1.0  
**Status**: PLAN-ONLY (Awaiting Approval)

## Executive Summary

This plan outlines a comprehensive refactoring of the YouTrack MCP server's tool surface from a large, bloated design (~60+ tools) to a **lossless minimal** design that preserves all functionality while reducing prompt/context overhead by ~80%.

### Current State Analysis
- **Total Tools**: 62+ tools across 6 modules
- **Context Bloat**: Long tutorial-style docstrings
- **Inconsistent Design**: Mixed naming and parameter handling
- **Safety Issues**: Missing validation and error handling
- **Maintenance Burden**: Complex parameter processing

### Target State
- **Default Tools**: 12 core tools (80% reduction)
- **Capability Packs**: Admin tools gated by environment flags
- **Token Efficiency**: Concise descriptions, help resources for details
- **Safety First**: Schema validation, exact-first resolution, no silent writes
- **Maintainability**: Typed operations, clear module boundaries

---

## 1. Overview

### 1.1 What is Changing
The current MCP server exports an excessive number of tools with verbose documentation that consumes significant context window space. This refactor consolidates functionality into a minimal, efficient tool surface while maintaining 100% functional compatibility.

### 1.2 Constraints
- **Lossless**: No functionality regression
- **Backward Compatible**: Existing integrations continue working
- **Performance**: Reduced token usage and faster tool selection
- **Safety**: Enhanced validation and error handling

### 1.3 Success Metrics
- Serialized tool schema size: < 50KB (from ~200KB+)
- Tool count: 12 default (from 62+)
- Test coverage: Maintain 80%+
- Error rate: < 5% (from ~15%)

---

## 2. Architecture Delta

### 2.1 Current Architecture
```
MCP Server
├── Issues Tools (25+)
│   ├── Basic Operations (CRUD)
│   ├── Custom Fields (validation, batch)
│   ├── Dedicated Updates (state, priority, etc.)
│   ├── Linking (dependencies, relations)
│   ├── Attachments (upload/download)
│   ├── Comments (CRUD)
│   └── Utilities (diagnostics, help)
├── Search Tools (3)
├── Project Tools (12)
├── User Tools (4)
├── AI Tools (4)
└── Resources Tools (15+)
```

### 2.2 Target Architecture
```
MCP Server
├── Core Tools (12) - Always Available
│   ├── search.query - Explicit YQL execution
│   ├── search.autosearch - NL→YQL translation
│   ├── issues.get - Rich read with expansions
│   ├── issues.create - Schema-aware creation
│   ├── issues.patch - Primary writer (typed ops)
│   ├── projects.list - Project discovery
│   ├── projects.get - Project details
│   ├── projects.patch - Project mutations
│   ├── projects.create - Project creation
│   ├── users.search - User resolution
│   ├── ai.plan - Plan-only translator
│   └── resources.read - Secured URI proxy
└── Capability Packs (Gated)
    ├── Admin Projects (delete, advanced ops)
    └── Admin Users (create, patch)
```

---

## 3. Public API Specification

### 3.1 Default 12 Tools

#### Search Tools (2)
1. **`search.query`**
   - **Purpose**: Execute explicit YouTrack Query Language
   - **Args**: `query` (str), `limit` (int, default 10), `sort_by` (str), `sort_order` (str)
   - **Returns**: JSON with search results
   - **Errors**: Invalid query syntax

2. **`search.autosearch`**
   - **Purpose**: Natural language to YQL translation
   - **Args**: `natural_language_query` (str), `project_context` (str, optional)
   - **Returns**: `{yql, confidence, results, notes, degraded?}`
   - **Errors**: Low confidence with safe degradation

#### Issues Tools (3)
3. **`issues.get`**
   - **Purpose**: Rich issue read with expansions
   - **Args**: `issue_id` (str), `include` (list of expansions)
   - **Returns**: Full issue data with requested expansions
   - **Errors**: Issue not found, permission denied

4. **`issues.create`**
   - **Purpose**: Schema-aware issue creation
   - **Args**: `project` (str), `summary` (str), `description` (str, optional)
   - **Returns**: Created issue data
   - **Errors**: Invalid project, schema validation failure

5. **`issues.patch`**
   - **Purpose**: Primary writer with typed operations
   - **Args**: `issue_id` (str), `fields` (dict) OR `ops` (list of typed ops)
   - **Returns**: Updated issue data
   - **Errors**: Validation failure, permission denied

#### Projects Tools (4)
6. **`projects.list`**
   - **Purpose**: Discover accessible projects
   - **Args**: `include_archived` (bool, default false)
   - **Returns**: List of projects
   - **Errors**: Permission denied

7. **`projects.get`**
   - **Purpose**: Project details with expansions
   - **Args**: `project_id` (str), `include` (list of expansions)
   - **Returns**: Full project data
   - **Errors**: Project not found

8. **`projects.patch`**
   - **Purpose**: Project mutations with typed ops
   - **Args**: `project_id` (str), `ops` (list of typed ops)
   - **Returns**: Updated project data
   - **Errors**: Validation failure

9. **`projects.create`**
   - **Purpose**: Create new projects
   - **Args**: `name` (str), `short_name` (str), `lead_id` (str)
   - **Returns**: Created project data
   - **Errors**: Duplicate name, invalid lead

#### Users & AI Tools (2)
10. **`users.search`**
    - **Purpose**: Resolve users by name/login
    - **Args**: `query` (str), `limit` (int, default 10)
    - **Returns**: List of matching users
    - **Errors**: No matches found

11. **`ai.plan`**
    - **Purpose**: Plan-only intent translator
    - **Args**: `intent` (str), `context` (dict, optional)
    - **Returns**: `{plan, explanations[], requires_confirmation: true}`
    - **Errors**: Ambiguous intent

#### Resources Tool (1)
12. **`resources.read`**
    - **Purpose**: Proxy read for secured URIs
    - **Args**: `uri` (str, youtrack:// format)
    - **Returns**: Resource content
    - **Errors**: Invalid URI, permission denied

### 3.2 Capability Packs

#### Admin Projects Pack
- `admin.projects.delete(project_id)`
- `admin.projects.archive(project_id)`
- `admin.projects.restore(project_id)`

#### Admin Users Pack
- `admin.users.create(user_spec)`
- `admin.users.patch(user_id, ops[])`
- `admin.users.deactivate(user_id)`

---

## 4. Phases

### Phase 0: Safety Hot-fixes & Environment Gating
**Goal**: Implement critical safety measures and environment controls

**Tasks**:
- [x] Add provider gating for unsupported AI providers
- [x] Implement exact-first project resolution (no fuzzy matching)
- [x] Remove placeholder text generation (`{PROJECT_NAME}`)
- [ ] Add `MCP_PARAM_REPAIR` flag for parameter auto-repair
- [ ] Create environment variable `YOUTRACK_CAPS` for capability packs
- [x] Add structured logging with redaction

**Success Criteria**:
- All placeholder text eliminated
- Provider gating working for OpenAI/Anthropic
- Parameter repair logged when applied
- Basic metrics collection operational

### Phase 1: Minimal Primitives
**Goal**: Implement core 12 tools with clean interfaces

**Tasks**:
- [ ] Create `issues.patch` with typed subpath grammar
- [ ] Implement `issues.get` with expansion support
- [ ] Build `projects.patch` with typed operations
- [ ] Add `search.autosearch` with confidence scoring
- [ ] Create `ai.plan` as read-only translator
- [ ] Implement `resources.read` for secured URIs
- [ ] Add concise tool descriptions (< 100 chars each)
- [ ] Create help resource system (`help://issues.patch`)

**Success Criteria**:
- All 12 tools functional
- Typed operations working
- Help resources accessible
- Tool descriptions concise

### Phase 2: Capability Packs
**Goal**: Gate admin functionality behind environment flags

**Tasks**:
- [ ] Create admin projects pack
- [ ] Implement admin users pack
- [ ] Add `YOUTRACK_CAPS` validation
- [ ] Test capability pack loading
- [ ] Update documentation for admin features

**Success Criteria**:
- Admin tools properly gated
- Environment flag validation working
- No admin tools in default surface

### Phase 3: Tests & Budgets
**Goal**: Comprehensive testing and performance monitoring

**Tasks**:
- [ ] Write golden tests for PATCH subpaths
- [ ] Add autosearch confidence rails
- [ ] Create property-based tests for fuzzy inputs
- [ ] Implement cache hit rate monitoring

**Success Criteria**:
- 80%+ test coverage maintained
- All PATCH operations tested

### Phase 4: Documentation & Help Resources
**Goal**: Complete documentation migration

**Tasks**:
- [ ] Move all examples to help resources
- [ ] Create comprehensive help pages
- [ ] Update README with new tool surface
- [ ] Add migration guide for existing users
- [ ] Create performance comparison docs
- [ ] Update API documentation

**Success Criteria**:
- All examples in help resources
- README reflects new surface
- Migration guide complete
- Performance improvements documented

---

## 5. Testing Strategy

### Unit Tests
- Router mappings validation
- Schema resolution testing
- Autosearch confidence rails
- PATCH subpath validation
- Resource URI parsing

### Integration Tests
- End-to-end tool workflows
- API client interactions
- Capability pack loading
- Help resource access

### Property-Based Tests
- Fuzzy input handling
- Edge case validation
- Performance under load

### Golden Tests
- PATCH operation results
- Search result formatting
- Error message consistency

---

## 6. Observability & Operations

### Metrics
- Tool call counts and latency
- Cache hit rates
- Schema size tracking
- Error rates by tool

### Logging
- Structured JSON logging
- PII/token redaction
- Configurable sampling
- Performance tracing

### Monitoring
- CI schema size budgets
- Test coverage gates
- Performance regression detection
- Error rate alerting

---

## 7. Security & Permissions

### Admin Capabilities
- Environment-gated admin tools
- Audit logging for admin operations
- Permission validation before execution

### Data Protection
- PII redaction in logs
- Token masking in error messages
- Secure credential handling

### Access Control
- Project allowlists for autosearch
- User permission validation
- Resource URI security

---

## 8. Risks & Mitigations

### High Risk
1. **API Throttling**: YouTrack rate limits
   - Mitigation: Request batching, exponential backoff
2. **Schema Drift**: Project schema changes
   - Mitigation: Runtime schema validation, fallback handling
3. **Cache Staleness**: Stale cached data
   - Mitigation: TTL-based invalidation, manual refresh

### Medium Risk
1. **Complex Migrations**: Breaking changes
   - Mitigation: Gradual rollout, backward compatibility
2. **Performance Regression**: Slower tool execution
   - Mitigation: Benchmarking, optimization passes

### Low Risk
1. **Documentation Gaps**: Missing help resources
   - Mitigation: Comprehensive help system, user feedback
2. **Tool Discovery**: Users can't find tools
   - Mitigation: Clear naming, help integration

---

## 10. Sign-Off Checklist

### Pre-Implementation
- [ ] Plan approved by stakeholders
- [ ] Open questions resolved

### Phase Completion
- [ ] Phase 0: Safety measures implemented
- [ ] Phase 1: Core tools functional
- [ ] Phase 2: Capability packs working
- [ ] Phase 3: Tests passing, budgets met
- [ ] Phase 4: Documentation complete

### Quality Gates
- [ ] Test coverage ≥ 80%
- [ ] No functionality regressions
- [ ] Security review passed

---

## Implementation Notes

### Tool Consolidation Strategy
- **Read Operations**: Consolidate into `issues.get`, `projects.get`
- **Write Operations**: Route through `issues.patch`, `projects.patch`
- **Search Operations**: Unified through `search.query` and `search.autosearch`
- **Utility Operations**: Moved to help resources or capability packs

### Performance Optimizations
- Lazy loading of capability packs
- Cached schema validation

---

**Next Step**: Awaiting approval to begin Phase 0 implementation.
