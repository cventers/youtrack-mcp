# ID Resolution Enhancement Plan
**Date:** 2025-10-22
**Branch:** feature/refactor-tools
**Status:** In Progress

## Executive Summary

The YouTrack MCP server currently exposes internal YouTrack IDs (like "63-2" for projects) to MCP clients, forcing them to use these cryptic identifiers instead of human-readable names (like "CLUSTER"). This plan outlines the implementation to transparently accept and work with logical names/IDs throughout the system.

## Current State Analysis

### Existing Infrastructure
1. **ID Resolver EXISTS** at `youtrack_mcp/utils/id_resolver.py`
   - Comprehensive implementation with caching via UnifiedCacheManager
   - Supports project, user, issue, and custom field resolution
   - Has TTL-based caching (1 hour for projects/users, 30 min for issues)
   - Includes cache warming and invalidation methods

2. **Client Support EXISTS** in `youtrack_mcp/api/client.py`
   - YouTrackClient accepts optional `id_resolver` parameter
   - However, it defaults to None and is not being used

3. **Tools NOT Using ID Resolution**
   - All tools modules directly pass IDs without resolution
   - No imports or usage of IDResolver found in any tools/*.py files
   - This is why clients must use internal IDs like "63-2"

### Problem Areas

| Location | Issue | Example |
|----------|-------|---------|
| `issues_tools.py:create()` | Directly passes project param | `project="CLUSTER"` fails, needs `"63-2"` |
| `issues_tools.py:get()` | No issue ID resolution | Accepts readable IDs but doesn't resolve |
| `issues_tools.py:patch()` | No issue ID resolution | Same as get() |
| `projects_tools.py:get()` | No project ID resolution | Should accept "CLUSTER" |
| All tools | No user ID resolution | Should accept "cventers" instead of numeric IDs |

## Proposed Solution

### Architecture
```
MCP Client Request → Tool Method → ID Resolution → YouTrack API
                                   ↓
                              Cache Check
                                   ↓
                           API Lookup if needed
                                   ↓
                              Cache Update
```

### Implementation Strategy

1. **Initialize ID Resolver in Tools**
   - Create shared IDResolver instance with cache manager
   - Pass to YouTrackClient initialization
   - Ensure singleton pattern for efficiency

2. **Add Resolution Layer to All ID Parameters**
   - Resolve project IDs before API calls
   - Resolve user IDs in assignee/reporter fields
   - Keep issue IDs as-is (YouTrack accepts readable format)

3. **Transparent Bidirectional Handling**
   - Input: Accept human-readable IDs
   - Output: Return human-readable IDs in responses
   - Never expose internal IDs to MCP clients

## Implementation Steps

### Phase 1: Initialize ID Resolver (Priority: CRITICAL)

**Files to Modify:**
- `youtrack_mcp/tools/issues_tools.py`
- `youtrack_mcp/tools/projects_tools.py`
- `youtrack_mcp/tools/users_tools.py`
- `youtrack_mcp/tools/search_tools.py`

**Changes:**
```python
# In each tools module __init__
from youtrack_mcp.cache.manager import UnifiedCacheManager
from youtrack_mcp.utils.id_resolver import IDResolver

class IssuesTools:
    def __init__(self):
        cache_manager = UnifiedCacheManager()
        id_resolver = IDResolver(None, cache_manager)  # Will set client later
        self.client = YouTrackClient(id_resolver=id_resolver)
        id_resolver.client = self.client  # Set client reference
        self.issues_api = IssuesClient(self.client)
```

### Phase 2: Add Resolution to Tool Methods

**Issues Tools:**
```python
async def create(self, project: str, summary: str, ...):
    # Resolve project ID
    if self.client.id_resolver:
        project_id = await self.client.id_resolver.resolve_project_id(project)
    else:
        project_id = project

    # Use resolved ID for API call
    issue = await self.issues_api.create_issue(
        project_id=project_id,
        ...
    )
```

**Projects Tools:**
```python
async def get(self, project_id: str, ...):
    # Resolve project ID
    if self.client.id_resolver:
        internal_id = await self.client.id_resolver.resolve_project_id(project_id)
    else:
        internal_id = project_id

    # Use resolved ID
    project = await self.client.projects.get_project(internal_id)
```

### Phase 3: Handle Custom Fields with User References

**Custom Field Resolution:**
```python
# In issues_tools.py patch method
if custom_fields_dict:
    resolved_fields = {}
    for field_name, value in custom_fields_dict.items():
        # Check if field is user type and resolve
        if field_name in ["Assignee", "Reporter"] and self.client.id_resolver:
            if isinstance(value, list):
                resolved_value = []
                for user_ref in value:
                    resolved_id = await self.client.id_resolver.resolve_user_id(user_ref)
                    resolved_value.append(resolved_id)
            else:
                resolved_value = await self.client.id_resolver.resolve_user_id(value)
            resolved_fields[field_name] = resolved_value
        else:
            resolved_fields[field_name] = value
```

### Phase 4: Singleton Pattern for Efficiency

Create a shared resolver registry to avoid multiple instances:

**New File:** `youtrack_mcp/utils/resolver_registry.py`
```python
from typing import Optional
from youtrack_mcp.cache.manager import UnifiedCacheManager
from youtrack_mcp.utils.id_resolver import IDResolver

class ResolverRegistry:
    _instance: Optional[IDResolver] = None
    _cache_manager: Optional[UnifiedCacheManager] = None

    @classmethod
    def get_resolver(cls, client=None) -> IDResolver:
        if cls._instance is None:
            if cls._cache_manager is None:
                cls._cache_manager = UnifiedCacheManager()
            cls._instance = IDResolver(client, cls._cache_manager)
        elif client and cls._instance.client is None:
            cls._instance.client = client
        return cls._instance

resolver_registry = ResolverRegistry()
```

### Phase 5: Cache Warming on Startup

Add to main.py or server initialization:
```python
async def warm_resolver_cache():
    resolver = resolver_registry.get_resolver()
    if resolver.client:
        counts = await resolver.warm_cache()
        logger.info(f"Warmed ID resolution cache: {counts}")
```

## Testing Strategy

### Unit Tests
1. **Test Resolution Functions**
   - Mock API responses for project/user lookups
   - Verify correct ID mapping
   - Test cache hit/miss scenarios

2. **Test Error Handling**
   - Invalid project names
   - Ambiguous user references
   - Network failures during resolution

### Integration Tests
1. **End-to-End ID Resolution**
   - Create issue with project shortName "CLUSTER"
   - Update issue with assignee login "cventers"
   - Verify internal IDs used in API calls
   - Confirm human-readable IDs in responses

2. **Performance Tests**
   - Measure resolution overhead
   - Verify cache effectiveness
   - Test concurrent resolutions

### Manual Testing Checklist
- [ ] Create issue with `project="CLUSTER"` instead of `"63-2"`
- [ ] Get project with `project_id="DSO"` instead of internal ID
- [ ] Assign issue to `"cventers"` instead of numeric user ID
- [ ] Create issue with readable project in custom fields
- [ ] Verify all responses show readable IDs, not internal ones

## Risk Assessment

### Performance Impact
- **Risk:** Additional API calls for resolution
- **Mitigation:** Aggressive caching with 1-hour TTL for stable entities
- **Monitoring:** Log cache hit/miss ratios

### Cache Invalidation
- **Risk:** Stale cache entries for renamed projects/users
- **Mitigation:** TTL-based expiry + manual invalidation methods
- **Monitoring:** Track resolution failures

### Backward Compatibility
- **Risk:** Breaking existing clients using internal IDs
- **Mitigation:** ID resolver detects numeric patterns and passes through
- **Testing:** Verify both ID formats continue to work

### Error Handling
- **Risk:** Resolution failures blocking operations
- **Mitigation:** Fallback to pass-through on resolution errors
- **Logging:** Comprehensive error logging for debugging

## Success Metrics

1. **Zero Internal IDs in MCP Responses**
   - All project IDs shown as shortNames (CLUSTER, DSO)
   - All issue IDs shown as readable (DSO-5, CLUSTER-123)
   - All user IDs shown as logins or names

2. **Transparent Input Handling**
   - Accept "CLUSTER" everywhere project ID expected
   - Accept "cventers" everywhere user ID expected
   - Accept "DSO-5" everywhere issue ID expected

3. **Performance Targets**
   - Cache hit rate > 90% after warmup
   - Resolution overhead < 50ms for cached entries
   - No noticeable latency increase for end users

4. **Error Rate**
   - Resolution failure rate < 1%
   - Graceful degradation on failures
   - Clear error messages for ambiguous references

## Timeline

- **Day 1 (Today):**
  - Implement Phase 1-2 (Initialize resolver, add to issues/projects tools)
  - Test with manual tool calls

- **Day 2:**
  - Implement Phase 3-4 (Custom fields, singleton pattern)
  - Add comprehensive logging

- **Day 3:**
  - Implement Phase 5 (Cache warming)
  - Write unit and integration tests
  - Performance testing and optimization

## Next Steps

1. Start with issues_tools.py as proof of concept
2. Test with CLUSTER project creation
3. Extend to all tools modules
4. Add comprehensive test coverage
5. Document ID resolution behavior in README

## Notes

- The ID resolver implementation is solid and feature-complete
- Main work is integration into existing tools
- Cache manager already handles Redis/in-process caching
- Consider adding OpenAPI schema updates to reflect accepting both ID formats