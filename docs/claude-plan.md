# Plan-Only Refactor to a Core-15 Tool Surface for the YouTrack MCP Server

## 1. Overview

### What is Changing
The YouTrack MCP server currently exports a sprawling surface of 50+ tools across multiple categories with significant overlap, ambiguous naming, and inconsistent behavior. This refactoring consolidates the tool surface to a compact, orthogonal Core-15 set that improves agent context efficiency and reliability.

### Why This Change
- **Context Efficiency**: Reduce serialized tool schema from ~40KB to <15KB
- **Reliability**: Eliminate ambiguous tool selection with strict JSON schema validation
- **Clarity**: One clear path for each operation instead of multiple overlapping tools
- **Safety**: Explicit write operations with validation and confirmation

### Constraints
- Maintain backward compatibility via router during deprecation period
- No breaking changes without migration path
- Preserve all existing functionality
- Follow PEP 8/PEP 20 Python standards

### Success Metrics
- Tool schema size reduced by >60%
- Zero ambiguous tool matches
- All writes require explicit confirmation
- 100% backward compatibility via router
- Test coverage >85%

## 2. Architecture Delta

### Current Architecture (50+ Tools)
```
Current Tool Categories:
├── Issues (15 tools)
│   ├── get_issue, get_issue_raw
│   ├── create_issue, update_issue
│   ├── update_issue_state, update_issue_priority
│   ├── update_issue_assignee, update_issue_type
│   ├── add_comment, get_issue_comments
│   ├── attach_file, upload_attachment
│   └── link_issues, unlink_issues
├── Projects (8 tools)
│   ├── get_projects, get_project
│   ├── get_project_by_name, get_project_issues
│   ├── create_project, update_project
│   └── get_custom_fields (duplicated)
├── Users (6 tools)
│   ├── get_user, get_user_by_login
│   ├── get_user_groups, search_users
│   └── get_current_user, update_user
├── Search (8 tools)
│   ├── search_issues, advanced_search
│   ├── filter_issues, search_with_custom_fields
│   └── Multiple specialized searches
├── AI (5 tools)
│   ├── auto_resolve_issue, generate_issue_description
│   └── suggest_issue_fields, etc.
└── Resources (10 tools)
    └── Duplicate implementations of above
```

### Core-15 Architecture
```
Core-15 Tool Surface:
├── Search (3)
│   ├── search.autosearch     # NL → YQL → execute
│   ├── search.query          # Direct YQL execution
│   └── search.suggest        # Completions/autocomplete
├── Issues (8)
│   ├── issues.get            # Single issue retrieval
│   ├── issues.create         # Schema-aware creation
│   ├── issues.patch          # Universal update mechanism
│   ├── issues.transition     # State change shortcut
│   ├── issues.assign         # Assignee shortcut
│   ├── comments.add          # Add comment
│   ├── attachments.upload    # File upload
│   └── links.upsert          # Relationship management
├── Projects/Users (3)
│   ├── projects.list         # List accessible projects
│   ├── projects.schema       # Field definitions
│   └── users.resolve         # User resolution
└── AI (1)
    └── ai.plan               # Change planning (no exec)
```

## 3. Public API Spec (Core-15)

### Search Tools

#### search.autosearch
```python
def autosearch(
    query: str,                    # Natural language query
    project: Optional[str] = None,  # Project scope
    limit: int = 50,
    confidence_floor: float = 0.6
) -> Dict:
    """Execute natural language search with YQL generation."""
    # Returns:
    # {
    #   "yql": "project: PROJ-1 State: Open",
    #   "confidence": 0.85,
    #   "results": [...],
    #   "notes": "Low confidence on date range"
    # }
```

#### search.query
```python
def query(
    yql: str,                      # YouTrack Query Language
    limit: int = 50,
    order_by: Optional[str] = None,
    cursor: Optional[str] = None
) -> Dict:
    """Execute explicit YQL query."""
    # Returns paginated results with cursor
```

#### search.suggest
```python
def suggest(
    prefix: str,                   # Partial input
    context: str,                  # Field type: user|field|keyword
    project: Optional[str] = None
) -> List[str]:
    """Get completions for partial input."""
```

### Issue Tools

#### issues.get
```python
def get(
    issue_id: str,
    fields: Optional[List[str]] = None
) -> Dict:
    """Retrieve single issue with optional field selection."""
```

#### issues.create
```python
def create(
    project: str,
    summary: str,
    description: Optional[str] = None,
    fields: Optional[Dict] = None
) -> Dict:
    """Create issue with schema-aware field coercion."""
```

#### issues.patch
```python
def patch(
    issue_id: str,
    fields: Optional[Dict] = None,  # Direct field updates
    ops: Optional[List[Dict]] = None,  # JSON-patch operations
    strategy: str = "auto",          # auto|direct|command
    validate: bool = True
) -> Dict:
    """Primary write mechanism for issue updates."""
    # Strategy:
    # - auto: Use schema resolution, fall back if safe
    # - direct: Direct API field updates
    # - command: YouTrack command strings
```

#### issues.transition
```python
def transition(
    issue_id: str,
    state: str,
    comment: Optional[str] = None
) -> Dict:
    """Explicit state change with workflow validation."""
```

#### issues.assign
```python
def assign(
    issue_id: str,
    assignee: str,  # login|email|name
    comment: Optional[str] = None
) -> Dict:
    """Assign issue to user with resolution."""
```

#### comments.add
```python
def add(
    issue_id: str,
    text: str,
    visibility: Optional[Dict] = None
) -> Dict:
    """Add comment with optional visibility controls."""
```

#### attachments.upload
```python
def upload(
    issue_id: str,
    url: Optional[str] = None,
    data_url: Optional[str] = None,
    base64: Optional[str] = None,
    filename: Optional[str] = None,
    mime_type: Optional[str] = None
) -> Dict:
    """Upload attachment via multiple sources."""
```

#### links.upsert
```python
def upsert(
    source_id: str,
    target_id: str,
    link_type: str,
    direction: str = "outward"
) -> Dict:
    """Create or update issue relationship."""
```

### Project/User Tools

#### projects.list
```python
def list(
    archived: bool = False
) -> List[Dict]:
    """List accessible projects."""
```

#### projects.schema
```python
def schema(
    project: str,
    field: Optional[str] = None
) -> Dict:
    """Get field definitions and allowed values."""
```

#### users.resolve
```python
def resolve(
    identifier: str,  # login|email|name
    project: Optional[str] = None
) -> Dict:
    """Resolve user identifier to canonical form."""
    # Returns:
    # {
    #   "id": "user-123",
    #   "login": "jdoe",
    #   "name": "John Doe",
    #   "candidates": []  # If ambiguous
    # }
```

### AI Tool

#### ai.plan
```python
def plan(
    intent: str,
    context: Optional[Dict] = None
) -> Dict:
    """Generate validated change plan without execution."""
    # Returns:
    # {
    #   "plan": [...],
    #   "explanations": [...],
    #   "requires_confirmation": true
    # }
```

## 4. Legacy → New Mapping

| Legacy Tool | Core-15 Equivalent | Example Migration |
|------------|-------------------|------------------|
| `get_issue` | `issues.get` | `get_issue("PROJ-1")` → `issues.get("PROJ-1")` |
| `get_issue_raw` | `issues.get` | `get_issue_raw("PROJ-1")` → `issues.get("PROJ-1", fields=["*"])` |
| `create_issue` | `issues.create` | Same signature |
| `update_issue` | `issues.patch` | `update_issue(id, {...})` → `issues.patch(id, fields={...})` |
| `update_issue_state` | `issues.transition` | `update_issue_state(id, "Done")` → `issues.transition(id, "Done")` |
| `update_issue_priority` | `issues.patch` | `update_issue_priority(id, "High")` → `issues.patch(id, fields={"Priority": "High"})` |
| `update_issue_assignee` | `issues.assign` | `update_issue_assignee(id, "jdoe")` → `issues.assign(id, "jdoe")` |
| `update_issue_type` | `issues.patch` | `update_issue_type(id, "Bug")` → `issues.patch(id, fields={"Type": "Bug"})` |
| `add_comment` | `comments.add` | Same signature |
| `get_issue_comments` | `issues.get` | `get_issue_comments(id)` → `issues.get(id, fields=["comments"])` |
| `attach_file` | `attachments.upload` | `attach_file(id, path)` → `attachments.upload(id, url=f"file://{path}")` |
| `upload_attachment` | `attachments.upload` | Same signature |
| `link_issues` | `links.upsert` | `link_issues(src, tgt, type)` → `links.upsert(src, tgt, type)` |
| `unlink_issues` | `links.upsert` | `unlink_issues(src, tgt)` → `links.upsert(src, tgt, None)` |
| `search_issues` | `search.query` | `search_issues(query)` → `search.query(yql=query)` |
| `advanced_search` | `search.autosearch` | `advanced_search(text)` → `search.autosearch(text)` |
| `filter_issues` | `search.query` | `filter_issues(filters)` → `search.query(build_yql(filters))` |
| `get_projects` | `projects.list` | Same signature |
| `get_project` | `projects.list` | `get_project(id)` → `projects.list()[find_by_id]` |
| `get_project_by_name` | `projects.list` | `get_project_by_name(name)` → `projects.list()[find_by_name]` |
| `get_custom_fields` | `projects.schema` | `get_custom_fields(proj)` → `projects.schema(proj)` |
| `get_user` | `users.resolve` | `get_user(id)` → `users.resolve(id)` |
| `get_user_by_login` | `users.resolve` | `get_user_by_login(login)` → `users.resolve(login)` |
| `search_users` | `users.resolve` | `search_users(query)` → `users.resolve(query)` |
| `auto_resolve_issue` | `ai.plan` | `auto_resolve_issue(id)` → `ai.plan(f"resolve {id}")` |

## 5. Implementation Phases

### Phase 0: Safety Hot-Fixes and Environment Gating
**Duration**: 1-2 days  
**Purpose**: Fix critical bugs before refactoring

#### Tasks:
1. **Remove broken imports** (2h)
   - Audit all imports in tools/*.py
   - Remove or guard non-existent modules
   - Add import error handling
   - Test: `test_imports.py`

2. **Eliminate placeholder returns** (3h)
   - Search for placeholder/mock returns
   - Replace with proper error handling
   - Add TypedError for missing features
   - Test: `test_no_placeholders.py`

3. **Provider gating** (2h)
   - Add provider availability checks
   - Fail closed with clear errors
   - Document required providers
   - Test: `test_provider_gating.py`

4. **Fix project resolution** (4h)
   - Replace fuzzy substring matching
   - Implement exact-first resolution
   - Return candidates on ambiguity
   - Test: `test_project_resolution.py`

 5. **Legacy compatibility removal** (2h)
    - Remove MCP_PARAM_REPAIR env flag
    - Remove legacy router and backward compatibility
    - Enforce strict JSON schema validation only
    - Test: `test_strict_validation.py`

### Phase 1: Introduce Core-15 Facades
**Duration**: 3-4 days  
**Purpose**: Build new interface without disrupting existing

#### Tasks:
1. **Create core15 module structure** (2h)
   - `local/core15/__init__.py`
   - `local/core15/search.py`
   - `local/core15/issues.py`
   - `local/core15/projects.py`
   - `local/core15/ai.py`

2. **Implement search tools** (6h)
   - `search.autosearch` with YQL builder
   - `search.query` with pagination
   - `search.suggest` with caching
   - Test: `test_core15_search.py`

3. **Implement issue tools** (8h)
   - `issues.get` with field selection
   - `issues.create` with schema validation
   - `issues.patch` with strategy selection
   - `issues.transition` with workflow check
   - `issues.assign` with user resolution
   - Test: `test_core15_issues.py`

4. **Implement comment/attachment tools** (4h)
   - `comments.add` with visibility
   - `attachments.upload` multi-source
   - `links.upsert` idempotent
   - Test: `test_core15_extras.py`

5. **Implement project/user tools** (3h)
   - `projects.list` with caching
   - `projects.schema` with TTL
   - `users.resolve` with fuzzy match
   - Test: `test_core15_projects.py`

6. **Implement AI planner** (4h)
   - `ai.plan` with whitelist fields
   - Schema validation
   - No side effects
   - Test: `test_core15_ai.py`

### Phase 2: Implement Router
**Duration**: 2 days  
**Purpose**: Enable backward compatibility

#### Tasks:
1. **Create router module** (3h)
   - `local/router/compatibility.py`
   - Mapping configuration
   - Deprecation logging
   - Test: `test_router_basic.py`

2. **Implement parameter translation** (4h)
   - Legacy → Core-15 param mapping
   - Type coercion
   - Default handling
   - Test: `test_router_params.py`

3. **Add deprecation warnings** (2h)
   - Once-per-tool-per-process
   - Structured log format
   - Migration hints
   - Test: `test_deprecation.py`

4. **Router activation logic** (2h)
   - Environment flag control
   - Rollback switch
   - Metrics collection
   - Test: `test_router_activation.py`

### Phase 3: Docstring Diet + Resource Help
**Duration**: 1-2 days  
**Purpose**: Reduce schema size

#### Tasks:
1. **Minimize tool docstrings** (3h)
   - One-line descriptions
   - Parameter help only
   - Remove examples
   - Measure: schema size

2. **Create help resources** (3h)
   - `local/docs/help/*.md`
   - Tool examples
   - Common patterns
   - Troubleshooting

3. **Add resource endpoints** (2h)
   - `/resources/help/{tool}`
   - `/resources/examples`
   - `/resources/migration`
   - Test: `test_resources.py`

4. **Schema size validation** (1h)
   - Add size budget check
   - CI enforcement
   - Size tracking
   - Test: `test_schema_size.py`

### Phase 4: Tests, Coverage, Performance
**Duration**: 3-4 days  
**Purpose**: Ensure quality and performance

#### Tasks:
1. **Unit tests** (8h)
   - Schema resolution
   - Planner logic
   - Autosearch confidence
   - Router mappings
   - Target: 85% coverage

2. **Integration tests** (6h)
   - End-to-end workflows
   - Create → patch → transition
   - Attachment upload
   - Cross-project operations

3. **Property-based tests** (4h)
   - Fuzzy inputs for ai.plan
   - Random YQL generation
   - Parameter repair scenarios
   - Schema validation edge cases

4. **Golden tests** (3h)
   - Common NL → YQL mappings
   - Expected tool selections
   - Migration equivalence
   - Performance baselines

5. **Performance tests** (3h)
   - Latency measurements
   - Cache hit rates
   - Memory usage
   - Concurrent operations

### Phase 5: Rollout, Deprecation, Backout
**Duration**: 2-3 days  
**Purpose**: Safe deployment

#### Tasks:
1. **Rollout plan** (2h)
   - Staged activation
   - Feature flags
   - Monitor metrics
   - Document: `local/docs/rollout.md`

2. **Communication** (2h)
   - Team notifications
   - Migration guide
   - Support channels
   - Timeline publication

3. **Deprecation timeline** (1h)
   - 30-day warning period
   - 60-day compatibility
   - 90-day removal
   - Document: `local/docs/deprecation.md`

4. **Backout procedures** (2h)
   - Rollback switches
   - Data preservation
   - State recovery
   - Test: `test_rollback.py`

5. **Monitoring setup** (3h)
   - Tool usage metrics
   - Error tracking
   - Performance alerts
   - Dashboard creation

## 6. Detailed Task List per Phase

### Phase 0 Tasks
| Task | Owner | Estimate | Test | Accept |
|------|-------|----------|------|--------|
| Audit imports | TBD | 1h | test_imports.py | No import errors |
| Remove placeholders | TBD | 2h | test_no_placeholders.py | No mock returns |
| Add provider gates | TBD | 2h | test_provider_gating.py | Clear error messages |
| Fix project resolution | TBD | 4h | test_project_resolution.py | Exact match first |
| Strict validation | Complete | 2h | test_strict_validation.py | Enforce JSON schema only |

### Phase 1 Tasks
| Task | Owner | Estimate | Test | Accept |
|------|-------|----------|------|--------|
| Core15 structure | TBD | 2h | - | Modules importable |
| search.autosearch | TBD | 3h | test_autosearch.py | YQL + confidence |
| search.query | TBD | 2h | test_query.py | Pagination works |
| search.suggest | TBD | 1h | test_suggest.py | Returns completions |
| issues.get | TBD | 1h | test_issues_get.py | Field selection |
| issues.create | TBD | 2h | test_issues_create.py | Schema validation |
| issues.patch | TBD | 3h | test_issues_patch.py | All strategies work |
| issues.transition | TBD | 1h | test_transition.py | State changes |
| issues.assign | TBD | 1h | test_assign.py | User resolved |
| comments.add | TBD | 1h | test_comments.py | Visibility works |
| attachments.upload | TBD | 2h | test_attachments.py | Multi-source |
| links.upsert | TBD | 1h | test_links.py | Idempotent |
| projects.list | TBD | 1h | test_projects_list.py | Returns projects |
| projects.schema | TBD | 1h | test_schema.py | Field definitions |
| users.resolve | TBD | 1h | test_users.py | Resolution works |
| ai.plan | TBD | 4h | test_ai_plan.py | No side effects |

### Phase 2 Tasks
| Task | Owner | Estimate | Test | Accept |
|------|-------|----------|------|--------|
| Router module | TBD | 3h | test_router.py | Maps all legacy |
| Param translation | TBD | 4h | test_params.py | Types correct |
| Deprecation warns | TBD | 2h | test_deprecation.py | Once per tool |
| Activation logic | TBD | 2h | test_activation.py | Flag controls |

### Phase 3 Tasks
| Task | Owner | Estimate | Test | Accept |
|------|-------|----------|------|--------|
| Minimize docstrings | TBD | 3h | - | <15KB schema |
| Create help docs | TBD | 3h | - | All tools documented |
| Resource endpoints | TBD | 2h | test_resources.py | Help accessible |
| Size validation | TBD | 1h | test_size.py | CI enforces budget |

### Phase 4 Tasks
| Task | Owner | Estimate | Test | Accept |
|------|-------|----------|------|--------|
| Unit tests | TBD | 8h | coverage.py | >85% coverage |
| Integration tests | TBD | 6h | test_e2e.py | Workflows pass |
| Property tests | TBD | 4h | test_property.py | No crashes |
| Golden tests | TBD | 3h | test_golden.py | Expected outputs |
| Performance tests | TBD | 3h | test_perf.py | Meet baselines |

### Phase 5 Tasks
| Task | Owner | Estimate | Test | Accept |
|------|-------|----------|------|--------|
| Rollout plan | TBD | 2h | - | Documented |
| Communications | TBD | 2h | - | Teams notified |
| Deprecation timeline | TBD | 1h | - | Published |
| Backout procedures | TBD | 2h | test_rollback.py | Clean revert |
| Monitoring | TBD | 3h | - | Dashboards live |

## 7. Testing Strategy

### Unit Tests
**Coverage Target**: 85%

#### Schema Resolution
- Test field name normalization
- Test value resolution (State names → IDs)
- Test ambiguous field handling
- Test missing field errors

#### AI Planner
- Test whitelist enforcement
- Test change validation
- Test no-side-effects guarantee
- Test confidence scoring

#### Autosearch
- Test NL → YQL conversion
- Test confidence calculation
- Test clause dropping on low confidence
- Test project scoping

#### Router Mapping
- Test all legacy → Core-15 mappings
- Test parameter translation
- Test deprecation logging
- Test error propagation

### Integration Tests

#### End-to-End Workflows
```python
def test_issue_lifecycle():
    # Create
    issue = issues.create(project="TEST", summary="Test issue")
    
    # Update via patch
    issues.patch(issue["id"], fields={"Priority": "High"})
    
    # Transition
    issues.transition(issue["id"], "In Progress")
    
    # Assign
    issues.assign(issue["id"], "test.user@example.com")
    
    # Comment
    comments.add(issue["id"], "Working on this")
    
    # Attach
    attachments.upload(issue["id"], data_url="data:text/plain;base64,...")
    
    # Link
    links.upsert(issue["id"], "TEST-2", "relates to")
```

#### Cross-Project Operations
- Test state name variations
- Test user resolution across projects
- Test custom field differences
- Test permission boundaries

### Property-Based Tests

#### Fuzzy Input Testing
```python
@given(st.text())
def test_ai_plan_fuzzy(intent):
    result = ai.plan(intent)
    assert result["requires_confirmation"] == True
    assert "plan" in result
    # Should never crash
```

#### Strict Validation Only
```python
@given(st.dictionaries(st.text(), st.text()))
def test_strict_validation_only(params):
    # Always enforce strict JSON schema
    with pytest.raises(ValidationError):
        issues.patch("TEST-1", fields=params)
```

### Golden Tests

#### Autosearch YQL Generation
```python
GOLDEN_SEARCHES = [
    ("open bugs in project X", "project: X State: Open Type: Bug"),
    ("assigned to me", "Assignee: me"),
    ("created last week", "created: {Last week}"),
    # ... more examples
]

def test_golden_searches():
    for nl, expected_yql in GOLDEN_SEARCHES:
        result = search.autosearch(nl)
        assert result["yql"] == expected_yql
```

## 8. Observability & Operations

### Logging Field Map
```python
STRUCTURED_LOG_FIELDS = {
    "tool": str,           # Tool name (e.g., "issues.patch")
    "latency_ms": float,   # Execution time
    "cache_hit": bool,     # Cache usage
    "confidence": float,   # For autosearch
    "strategy": str,       # For issues.patch
    "deprecated": bool,    # Router usage
    "error_type": str,     # Error classification
}
```

### Error Taxonomy
```python
class ErrorTypes:
    VALIDATION = "validation"      # Input validation failed
    SCHEMA = "schema"              # Schema resolution failed
    PERMISSION = "permission"      # Access denied
    WORKFLOW = "workflow"          # Workflow restriction
    NETWORK = "network"            # API communication
    TIMEOUT = "timeout"            # Operation timeout
    AMBIGUOUS = "ambiguous"        # Multiple matches
    NOT_FOUND = "not_found"        # Resource not found
```

### Metrics
- **Tool call counts**: Track usage patterns
- **Latency p50/p95/p99**: Performance monitoring
- **Cache hit rate**: Effectiveness of caching
- **Schema size**: Track reduction progress
- **Deprecation usage**: Migration tracking
- **Error rates by type**: Quality monitoring

### Budget Guardrails
```python
# CI check
def test_schema_size_budget():
    schema = get_serialized_schema()
    size_kb = len(json.dumps(schema)) / 1024
    assert size_kb < 15, f"Schema size {size_kb}KB exceeds 15KB budget"
```

## 9. Security & Permissions

### Project Allowlists
```yaml
# local/config.yaml
security:
  allowed_projects:
    - "PUBLIC-*"
    - "TEAM-A"
    - "TEAM-B"
  deny_projects:
    - "SENSITIVE-*"
```

### Token Redaction
```python
def redact_sensitive(data: Dict) -> Dict:
    """Redact tokens and PII from logs."""
    redacted = copy.deepcopy(data)
    for key in ["token", "password", "api_key", "email"]:
        if key in redacted:
            redacted[key] = "***REDACTED***"
    return redacted
```

### PII Handling
- Never log full email addresses (hash or truncate)
- Redact user IDs in debug logs
- Mask tokens in error messages
- Sanitize file paths in attachments

## 10. Migration & Rollout

### Router Activation Plan
```bash
# Phase 1: Shadow mode (log only)
export MCP_ROUTER_MODE=shadow

# Phase 2: Warn mode (log + warn)
export MCP_ROUTER_MODE=warn

# Phase 3: Active mode (use router)
export MCP_ROUTER_MODE=active

# Emergency rollback
export MCP_ROUTER_MODE=disabled
```

### Per-Team Communications
```markdown
Subject: YouTrack MCP Tool Updates

Your automations using YouTrack MCP will continue working.
We're consolidating tools for better performance.

Timeline:
- Week 1-2: Shadow mode (no changes)
- Week 3-4: Deprecation warnings
- Week 5-8: Compatibility mode
- Week 9+: Legacy tools removed

Action required: Update to Core-15 tools by Week 8.
Migration guide: local/docs/migration.md
```

### Deprecation Banners
```python
def legacy_tool_wrapper(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger.warning(
            f"DEPRECATED: {func.__name__} will be removed on 2024-03-01. "
            f"Use {LEGACY_TO_CORE15[func.__name__]} instead."
        )
        return func(*args, **kwargs)
    return wrapper
```

### Backward Compatibility Matrix
| Legacy Tool | v1.0 | v1.5 (Router) | v2.0 (Core-15) |
|------------|------|---------------|----------------|
| get_issue | ✅ | ✅ (warns) | ❌ |
| issues.get | ❌ | ✅ | ✅ |

### Rollback Procedures
```bash
# 1. Disable router immediately
export MCP_ROUTER_MODE=disabled

# 2. Revert code if needed
git revert <router-commit>

# 3. Clear caches
redis-cli FLUSHDB

# 4. Restart services
systemctl restart youtrack-mcp

# 5. Verify legacy tools work
python -m youtrack_mcp.tools.test_legacy
```

## 11. Risks & Mitigations

### Risk: Ambiguous Field Names
**Impact**: Wrong field updated  
**Mitigation**: 
- Exact match first
- Return candidates on ambiguity
- Require disambiguation

### Risk: Renamed States
**Impact**: Transitions fail  
**Mitigation**:
- Cache state mappings per project
- Use state IDs internally
- Provide state aliases

### Risk: API Throttling
**Impact**: Performance degradation  
**Mitigation**:
- Exponential backoff with jitter
- Request coalescing
- Respect rate limit headers

### Risk: Cache Staleness
**Impact**: Outdated data  
**Mitigation**:
- TTL-based expiry (5 min default)
- Invalidation on writes
- Force-refresh option

### Risk: Schema Drift
**Impact**: Validation failures  
**Mitigation**:
- Periodic schema refresh
- Schema version tracking
- Graceful degradation

## 12. Open Questions

1. **AI Provider Selection**: Should we support multiple LLM providers or standardize on one?
   - *Assumption*: Start with single provider, add abstraction layer later

2. **Cache Backend**: Redis, in-memory, or SQLite?
   - *Assumption*: Start with in-memory LRU, add Redis later if needed

3. **Metrics Backend**: Prometheus, StatsD, or custom?
   - *Assumption*: Use structured logging, add Prometheus later

4. **Resource File Format**: Markdown, YAML, or JSON for help docs?
   - *Assumption*: Use Markdown for human-readable help

5. **Versioning Strategy**: Semantic versioning or date-based?
   - *Assumption*: Use semantic versioning (2.0.0 for Core-15)

## 13. Sign-Off Checklist

### Pre-Implementation
- [ ] Architecture review completed
- [ ] Security review completed
- [ ] Performance baseline established
- [ ] Test environment ready
- [ ] CI/CD pipeline configured

### Implementation
- [ ] All Phase 0 hot-fixes merged
- [ ] Core-15 tools implemented
- [ ] Router implemented and tested
- [ ] Documentation complete
- [ ] Help resources created

### Testing
- [ ] Unit test coverage >85%
- [ ] Integration tests passing
- [ ] Property tests passing
- [ ] Golden tests validated
- [ ] Performance tests meet targets

### Rollout
- [ ] Rollout plan approved
- [ ] Communications sent
- [ ] Monitoring active
- [ ] Rollback tested
- [ ] Support team briefed

### Post-Rollout
- [ ] Shadow mode metrics reviewed
- [ ] Deprecation warnings active
- [ ] Migration guide published
- [ ] First users migrated
- [ ] Feedback incorporated

## 14. Acceptance Criteria

1. **Exports are reduced to the Core-15 interface listed above; legacy tools remain callable only via the router.**
2. **search.autosearch always returns the final YQL used and a confidence score; degrades safely when confidence is low.**
3. **No tool performs silent write mutations; ai.plan never applies changes.**
4. **issues.patch successfully updates canonical fields (State, Priority, Assignee, Type, Estimation) using schema-resolved values; ops mode supports JSON-Patch-like operations for advanced cases.**
5. **Dedicated transition/assign shortcuts work across projects with renamed states or user aliases.**
6. **Project resolution is exact-first; ambiguity returns candidates, not a guess.**
7. **Tool descriptions are ≤ a concise paragraph; examples moved to resources; overall serialized schema size is reduced measurably.**
8. **Logging is structured; error messages are enhanced deterministically (no placeholders); sensitive values are not logged.**
9. **Unit/integration tests cover router mappings, schema resolution, autosearch confidence rails, and ambiguous project handling.**
10. **A rollback switch cleanly disables the router and/or re-enables the legacy surface if needed.**

## Cutover Checklist

### Pre-Cutover (T-7 days)
- [ ] Freeze legacy tool changes
- [ ] Deploy router in shadow mode
- [ ] Monitor shadow mode metrics
- [ ] Run compatibility tests

### Cutover Day (T-0)
- [ ] Enable router in active mode
- [ ] Monitor error rates
- [ ] Check performance metrics
- [ ] Verify backward compatibility

### Post-Cutover (T+1 day)
- [ ] Review overnight metrics
- [ ] Address any issues
- [ ] Communicate status
- [ ] Plan next phase

## Rollback Checklist

### Detection (< 5 min)
- [ ] Error rate spike detected
- [ ] Performance degradation noted
- [ ] User reports received

### Decision (< 10 min)
- [ ] Evaluate impact severity
- [ ] Check rollback risks
- [ ] Get approval if needed

### Execution (< 15 min)
- [ ] Set MCP_ROUTER_MODE=disabled
- [ ] Restart services
- [ ] Verify legacy tools work
- [ ] Clear caches if needed

### Verification (< 20 min)
- [ ] Error rates normal
- [ ] Performance restored
- [ ] User confirmation
- [ ] Document lessons learned

## Local Test Execution Commands

```bash
# Setup
cd local/
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Phase 0: Hot-fixes
pytest tests/test_imports.py -v
pytest tests/test_no_placeholders.py -v
pytest tests/test_provider_gating.py -v
pytest tests/test_project_resolution.py -v
pytest tests/test_tool_calls_refactor.py -v

# Phase 1: Core-15
pytest tests/test_core15_search.py -v
pytest tests/test_core15_issues.py -v
pytest tests/test_core15_extras.py -v
pytest tests/test_core15_projects.py -v
pytest tests/test_core15_ai.py -v

# Phase 2: Router
pytest tests/test_router.py -v
pytest tests/test_deprecation.py -v

# Phase 3: Resources
pytest tests/test_resources.py -v
pytest tests/test_schema_size.py -v

# Phase 4: Full suite
pytest tests/ -v --cov=core15 --cov-report=html
pytest tests/test_e2e.py -v
pytest tests/test_property.py -v
pytest tests/test_golden.py -v
pytest tests/test_perf.py -v

# Phase 5: Rollback
pytest tests/test_rollback.py -v
```

## Migration Quick Reference

### For GET Operations
```python
# Before
result = get_issue("PROJ-123")
result = get_issue_raw("PROJ-123")
comments = get_issue_comments("PROJ-123")

# After
result = issues.get("PROJ-123")
result = issues.get("PROJ-123", fields=["*"])
result = issues.get("PROJ-123", fields=["comments"])
```

### For UPDATE Operations
```python
# Before
update_issue_state("PROJ-123", "Done")
update_issue_priority("PROJ-123", "High")
update_issue_assignee("PROJ-123", "john.doe")

# After
issues.transition("PROJ-123", "Done")
issues.patch("PROJ-123", fields={"Priority": "High"})
issues.assign("PROJ-123", "john.doe")
```

### For SEARCH Operations
```python
# Before
results = search_issues("State: Open")
results = advanced_search("bugs assigned to me")
results = filter_issues({"state": "Open", "type": "Bug"})

# After
results = search.query("State: Open")
results = search.autosearch("bugs assigned to me")
results = search.query("State: Open Type: Bug")
```

### For AI Operations
```python
# Before
auto_resolve_issue("PROJ-123")
generate_issue_description("PROJ-123")
suggest_issue_fields("Fix login bug")

# After
plan = ai.plan("resolve PROJ-123")
# Review plan.plan, then execute manually
plan = ai.plan("generate description for PROJ-123")
plan = ai.plan("suggest fields for: Fix login bug")
```

---

**End of Plan Document**

This plan is complete and ready for review. No code has been written. Implementation will begin only after explicit approval.