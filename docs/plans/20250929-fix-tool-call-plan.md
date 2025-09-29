# YouTrack MCP Server - Tool Call ID Resolution Fix Plan
**Date:** 2025-09-29  
**Author:** Chase Venters / Claude  
**Status:** PROPOSED  
**Priority:** HIGH  

## Executive Summary

The YouTrack MCP server currently fails to create issues when using project short names (e.g., "ACC") instead of numeric IDs (e.g., "63-13"). This is a critical bug that prevents normal operation of the MCP server. All tools that accept ID parameters must be enhanced to support human-friendly variants and automatically perform lookup/resolution to the internal IDs required by the YouTrack API.

## Problem Statement

### Current Failures
1. **Issue Creation Fails with Project Short Names**
   - Using `project="ACC"` results in: `"Invalid structure of entity id: ACC"`
   - YouTrack API requires numeric format: `project={"id": "63-13"}`
   
2. **No Automatic ID Resolution**
   - Tools directly pass user-provided IDs to the API
   - No validation or lookup occurs before API calls
   - Users must manually discover numeric IDs

3. **Poor Error Messages**
   - Generic "validation failed" errors
   - No guidance on correct ID format
   - No suggestion to use numeric IDs

### Root Causes
1. **API Misunderstanding**: Assumption that YouTrack accepts short names in JSON payloads
2. **Missing Resolution Layer**: No intermediate lookup step between tool call and API
3. **Incomplete Testing**: Tools not tested with real-world project structures

## Proposed Solution

### Core Principle
**All MCP tools accepting ID parameters must support human-friendly variants and automatically resolve them to internal IDs**

### Resolution Strategy
1. **Detect ID Format**: Check if provided ID is human-friendly or internal format
2. **Perform Lookup**: If human-friendly, query API to get internal ID
3. **Cache Results**: Store mappings to avoid repeated lookups
4. **Proceed with Internal ID**: Use resolved ID for actual operation

### Caching Requirements

Based on analysis of existing caching infrastructure (`cachetools` v6.2.0 already installed), the ID resolution system requires:

#### Cache Architecture
1. **Hybrid Caching Strategy** (Default)
   - **Memory Layer**: TTLCache for fast in-process lookups (cachetools library)
   - **Persistent Layer**: SQLite for multiprocess-safe storage that survives restarts
   - **Fallback**: Graceful degradation if SQLite unavailable

2. **TTL Enforcement**
   - **Projects**: 1 hour (3600s) - rarely change
   - **Users**: 1 hour (3600s) - relatively stable
   - **Issues**: 30 minutes (1800s) - more dynamic
   - **Bundle Elements**: 2 hours (7200s) - very stable

3. **Backend Options**
   - **Memory-only**: Fast but lost on restart (development)
   - **SQLite**: Persistent, multiprocess-safe, no dependencies (production default)
   - **Redis**: Optional distributed caching if available (enterprise)
   - **Hybrid**: Memory + SQLite (recommended)

4. **Multiprocess Safety**
   - SQLite with WAL (Write-Ahead Logging) mode for concurrent access
   - No file locking issues or race conditions
   - Automatic cleanup of expired entries

5. **Configuration**
   - Environment variables for backend selection
   - Configurable TTLs per entity type
   - Optional cache warming on startup
   - Monitoring and cache hit rate tracking

## Implementation Plan

### Phase 1: Create ID Resolution Infrastructure

#### 1.1 Create ID Resolver Module
**File:** `youtrack_mcp/utils/id_resolver.py`

```python
from enum import Enum
from typing import Optional, Any, Dict
import sqlite3
import json
import time
from pathlib import Path
from cachetools import TTLCache

class CacheBackend(str, Enum):
    MEMORY_ONLY = "memory"      # Fast, process-local
    SQLITE = "sqlite"            # Persistent, multiprocess-safe
    REDIS = "redis"              # Distributed (optional, if available)
    HYBRID = "hybrid"            # Memory + SQLite fallback

class IDResolver:
    """Resolves human-friendly IDs to YouTrack internal IDs with configurable caching"""
    
    def __init__(
        self, 
        client,
        cache_backend: CacheBackend = CacheBackend.HYBRID,
        cache_ttl: int = 3600,  # 1 hour default
        sqlite_path: Optional[Path] = None,
        redis_config: Optional[Dict] = None
    ):
        self.client = client
        self.cache_backend = cache_backend
        self.cache_ttl = cache_ttl
        
        # Always initialize memory cache (fast layer)
        self._memory_cache = {
            'projects': TTLCache(maxsize=100, ttl=cache_ttl),
            'users': TTLCache(maxsize=500, ttl=cache_ttl),
            'issues': TTLCache(maxsize=1000, ttl=cache_ttl // 2)  # Shorter TTL for issues
        }
        
        # Initialize persistent cache if needed
        if cache_backend in [CacheBackend.SQLITE, CacheBackend.HYBRID]:
            self.sqlite_path = sqlite_path or Path.home() / ".youtrack-mcp" / "id_cache.db"
            self._init_sqlite_cache()
            
        # Optional Redis support
        if cache_backend == CacheBackend.REDIS and redis_config:
            self._init_redis_cache(redis_config)
    
    def _init_sqlite_cache(self):
        """Initialize SQLite cache with multiprocess-safe WAL mode"""
        self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.sqlite_path))
        conn.execute("PRAGMA journal_mode=WAL")  # Enable Write-Ahead Logging for multiprocess
        conn.execute("""
            CREATE TABLE IF NOT EXISTS id_cache (
                cache_type TEXT,
                reference TEXT,
                internal_id TEXT,
                created_at REAL,
                expires_at REAL,
                PRIMARY KEY (cache_type, reference)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_expires ON id_cache(expires_at)")
        conn.close()
    
    async def resolve_project_id(self, project_ref: str) -> str:
        """Resolve project reference to numeric ID with caching"""
        # Check if already numeric (e.g., "63-13")
        if self._is_numeric_id(project_ref):
            return project_ref
            
        # Try memory cache first (fastest)
        if project_ref in self._memory_cache['projects']:
            return self._memory_cache['projects'][project_ref]
            
        # Try persistent cache if configured
        if self.cache_backend in [CacheBackend.SQLITE, CacheBackend.HYBRID]:
            cached_id = await self._get_from_sqlite('projects', project_ref)
            if cached_id:
                # Populate memory cache for next access
                self._memory_cache['projects'][project_ref] = cached_id
                return cached_id
        
        # Not in cache, perform API lookup
        project = await self._lookup_project(project_ref)
        if project:
            internal_id = project['id']
            
            # Store in all configured caches
            self._memory_cache['projects'][project_ref] = internal_id
            
            if self.cache_backend in [CacheBackend.SQLITE, CacheBackend.HYBRID]:
                await self._store_in_sqlite('projects', project_ref, internal_id)
                
            return internal_id
            
        raise ValueError(f"Project not found: {project_ref}")
    
    async def resolve_issue_id(self, issue_ref: str) -> str:
        """Resolve issue reference to internal ID"""
        # Handle formats: "ACC-123", "ACC 123", "123" (in project context)
        # Shorter TTL for issues as they change more frequently
        
    async def resolve_user_id(self, user_ref: str) -> str:
        """Resolve user reference to internal ID"""
        # Handle: login names, emails, user IDs
        
    async def _get_from_sqlite(self, cache_type: str, reference: str) -> Optional[str]:
        """Retrieve from SQLite cache with TTL validation"""
        conn = sqlite3.connect(str(self.sqlite_path))
        cursor = conn.execute(
            "SELECT internal_id, expires_at FROM id_cache WHERE cache_type = ? AND reference = ?",
            (cache_type, reference)
        )
        row = cursor.fetchone()
        conn.close()
        
        if row and row[1] > time.time():
            return row[0]
        return None
        
    async def _store_in_sqlite(self, cache_type: str, reference: str, internal_id: str):
        """Store in SQLite cache with TTL"""
        expires_at = time.time() + self.cache_ttl
        conn = sqlite3.connect(str(self.sqlite_path))
        conn.execute(
            "INSERT OR REPLACE INTO id_cache (cache_type, reference, internal_id, created_at, expires_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (cache_type, reference, internal_id, time.time(), expires_at)
        )
        conn.commit()
        conn.close()
        
    async def cleanup_expired(self) -> int:
        """Remove expired cache entries from SQLite"""
        if self.cache_backend not in [CacheBackend.SQLITE, CacheBackend.HYBRID]:
            return 0
            
        conn = sqlite3.connect(str(self.sqlite_path))
        cursor = conn.execute("DELETE FROM id_cache WHERE expires_at < ?", (time.time(),))
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        return deleted
        
    def _is_numeric_id(self, project_ref: str) -> bool:
        """Check if ID is already in numeric format"""
        import re
        return bool(re.match(r'^\d+-\d+$', project_ref))
```

#### 1.2 Integration Points
- Inject resolver into all API client classes
- Add resolution step before API calls
- Maintain backward compatibility

### Phase 2: Update Tool Implementations

#### 2.1 Issues Tools
**Files to Update:**
- `youtrack_mcp/tools/issues_tools.py`
- `youtrack_mcp/api/issues.py`

**Changes Required:**

```python
# In IssuesTools.create()
async def create(self, project: str, summary: str, ...):
    try:
        # NEW: Resolve project ID
        resolved_project_id = await self.resolver.resolve_project_id(project)
        
        # Use resolved ID
        issue = await self.issues_api.create_issue(
            project_id=resolved_project_id,  # Now guaranteed to be numeric
            ...
        )
```

```python
# In IssuesClient.create_issue()
async def create_issue(self, project_id: str, ...):
    # Remove direct pass-through
    # OLD: issue_data = {"project": {"id": project_id}}
    
    # NEW: Validate ID format
    if not self._is_valid_numeric_id(project_id):
        raise ValidationError(f"Invalid project ID format: {project_id}. Use resolver.")
    
    issue_data = {"project": {"id": project_id}}
```

#### 2.2 Projects Tools
**Files to Update:**
- `youtrack_mcp/tools/projects_tools.py`
- `youtrack_mcp/api/projects.py`

**Changes for `projects.get()`:**
```python
async def get(self, project_id: str, ...):
    # Support both "ACC" and "63-13" formats
    resolved_id = await self.resolver.resolve_project_id(project_id)
    return await self.projects_api.get_project(resolved_id, ...)
```

#### 2.3 Custom Field Resolution
**Enhanced Resolution for Custom Fields:**

```python
async def resolve_custom_field_values(self, project_id: str, fields: Dict):
    """Resolve human-friendly custom field values"""
    
    # Get project schema
    schema = await self.get_project_schema(project_id)
    
    resolved = {}
    for field_name, value in fields.items():
        field_def = schema.get_field(field_name)
        
        if field_def.type == 'MultiOwnedIssueCustomField':
            # Resolve bundle elements
            resolved[field_name] = await self.resolve_bundle_values(
                field_def.bundle_id, value
            )
        elif field_def.type == 'MultiUserIssueCustomField':
            # Resolve user references
            resolved[field_name] = await self.resolve_user_refs(value)
        else:
            resolved[field_name] = value
            
    return resolved
```

### Phase 3: Add Comprehensive Error Handling

#### 3.1 Enhanced Error Messages
```python
class IDResolutionError(Exception):
    """Raised when ID resolution fails"""
    
    def __init__(self, ref_type: str, reference: str, suggestions: List[str] = None):
        self.ref_type = ref_type
        self.reference = reference
        self.suggestions = suggestions
        
        message = f"Could not resolve {ref_type} '{reference}'"
        if suggestions:
            message += f"\nDid you mean one of: {', '.join(suggestions[:3])}?"
        
        super().__init__(message)
```

#### 3.2 Fallback Strategies
```python
async def resolve_with_fallback(self, reference: str) -> str:
    """Try multiple resolution strategies"""
    
    # Try exact match
    result = await self.exact_lookup(reference)
    if result:
        return result
        
    # Try case-insensitive
    result = await self.case_insensitive_lookup(reference)
    if result:
        return result
        
    # Try partial match with confirmation
    candidates = await self.partial_match_lookup(reference)
    if len(candidates) == 1:
        return candidates[0]
    elif candidates:
        raise AmbiguousReferenceError(reference, candidates)
        
    raise IDResolutionError('project', reference)
```

### Phase 4: Testing and Validation

#### 4.1 Unit Tests
**File:** `tests/unit/test_id_resolver.py`

```python
class TestIDResolver:
    async def test_resolves_project_short_name(self):
        """Test that ACC resolves to 63-13"""
        
    async def test_passes_through_numeric_ids(self):
        """Test that 63-13 is not looked up"""
        
    async def test_caches_lookups(self):
        """Test that repeated lookups use cache"""
        
    async def test_handles_invalid_references(self):
        """Test error handling for non-existent projects"""
```

#### 4.2 Integration Tests
**File:** `tests/integration/test_issue_creation.py`

```python
async def test_create_issue_with_short_name():
    """Test creating issue using project short name"""
    result = await tools.issues.create(
        project="ACC",  # Human-friendly
        summary="Test Issue",
        custom_fields={
            "System": ["Emergency Vault"],  # Human-friendly
            "Assignee": "cventers"  # Human-friendly
        }
    )
    assert result['issue']['project']['id'] == "63-13"
```

### Phase 5: Documentation Updates

#### 5.1 Update Tool Descriptions
Enhance all tool descriptions to mention ID flexibility:

```python
"description": "Get project details. Accepts project short name (e.g., 'ACC') or numeric ID (e.g., '63-13')."
```

## Implementation Schedule

- [ ] Create ID resolver module with caching
- [ ] Add comprehensive unit tests for resolver
- [ ] Integrate resolver into API client base class
- [ ] Update issues.create() to use resolver
- [ ] Update projects.get() to use resolver
- [ ] Add integration tests for both
- [ ] Extend to all other ID-accepting tools
- [ ] Add custom field value resolution
- [ ] Implement error handling improvements
- [ ] Complete documentation updates
- [ ] Run full test suite
- [ ] Deploy to staging for testing

## Success Criteria

1. **All ID formats work**:
   - `project="ACC"` creates issues successfully
   - `projects.get("DEMO")` returns project data
   - `issues.patch("OPS-123", ...)` updates issues

2. **Performance maintained**:
   - Caching prevents repeated lookups
   - Resolution adds <100ms to first call
   - Subsequent calls use cache

3. **Error messages improved**:
   - Clear indication when ID not found
   - Suggestions for similar IDs
   - Guidance on correct format

4. **Backward compatibility**:
   - Numeric IDs still work directly
   - No breaking changes to API

## Risk Mitigation

### Risk 1: Performance Impact
**Mitigation**: Aggressive caching, batch lookups, async resolution

### Risk 2: Ambiguous References
**Mitigation**: Return candidates list, require exact match or selection

### Risk 3: API Rate Limits
**Mitigation**: Cache aggressively, batch requests, implement exponential backoff

## Monitoring and Rollback

### Monitoring
- Log all resolution attempts and failures
- Track cache hit rates
- Monitor API call volume increase

### Rollback Plan
- Feature flag to disable resolution
- Fallback to direct ID passing
- Clear documentation of numeric ID requirements

## Appendix A: Affected Tools

Tools that accept ID parameters and need updates:

1. **Issue Management**
   - `issues.get(issue_id)`
   - `issues.create(project)`
   - `issues.patch(issue_id)`

2. **Project Management**
   - `projects.get(project_id)`
   - `projects.patch(project_id)`
   - `projects.schema(project_id)`

3. **User Management**
   - `users.get(user_id)`
   - Field assignments with user IDs

4. **Search and Filtering**
   - Query parameters with project/user references
   - Custom field value matching

## Appendix B: ID Format Reference

### Valid ID Formats

| Entity | Human-Friendly | Internal | Example |
|--------|---------------|----------|---------|
| Project | Short name | Numeric ID | ACC → 63-13 |
| Issue | Readable ID | Internal ID | ACC-783 → issue-12345 |
| User | Login/email | User ID | cventers → user-67890 |
| Bundle | Element name | Element ID | Emergency Vault → elem-111 |

### Detection Patterns

```python
# Numeric project ID pattern
NUMERIC_PROJECT_ID = r'^\d+-\d+$'  # e.g., "63-13"

# Readable issue ID pattern
READABLE_ISSUE_ID = r'^[A-Z]+-\d+$'  # e.g., "ACC-783"

# User login pattern
USER_LOGIN = r'^[a-z][a-z0-9._-]*$'  # e.g., "cventers"
```

## Conclusion

This comprehensive fix addresses the critical issue of ID resolution in the YouTrack MCP server. By implementing automatic resolution of human-friendly IDs to internal formats, we will significantly improve usability while maintaining API compatibility. The phased approach ensures minimal disruption while delivering immediate value through the most critical fixes first.