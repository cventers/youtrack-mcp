# Async Migration Plan - YouTrack MCP Server

**Date**: 2025-09-09  
**Priority**: 🚨 CRITICAL  
**Estimated Time**: 2-3 days  
**Current Status**: Partially broken (2/8 core modules functional)

## Executive Summary

This plan outlines the complete migration of the YouTrack MCP server from a broken sync/async hybrid to a fully async architecture. Currently, only `CoreIssuesTools` works correctly. The remaining 7 core tool modules are calling async API methods without proper handling, causing runtime failures.

## Current State Assessment

### Working ✅
- `CoreIssuesTools` - 3 async methods with `@async_wrapper`

### Broken ❌
- `CoreProjectsTools` - 4 sync methods calling async APIs
- `CoreSearchTools` - 2 sync methods calling async APIs  
- `CoreUsersTools` - 1 sync method calling async APIs
- `CoreAITools` - 1 sync method calling async APIs
- `CoreResourcesTools` - 1 sync method calling async APIs
- `CoreProjectsAdminTools` - 3 sync methods calling async APIs
- `CoreUsersAdminTools` - 3 sync methods calling async APIs

**Total**: 15 broken methods across 7 modules

## Migration Phases

### Phase 0: Emergency Stabilization (30 minutes) 🚨
**Goal**: Make the system minimally functional  
**Owner**: Lead Developer  
**Status**: URGENT

#### Option A: Quick Fix sync_wrapper (Recommended for immediate relief)
```python
# In youtrack_mcp/mcp_wrappers.py
import asyncio
import nest_asyncio
nest_asyncio.apply()

def sync_wrapper(func: Callable) -> Callable:
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            result = func(*processed_args, **processed_kwargs)
            
            # Handle coroutines returned by sync functions calling async methods
            if asyncio.iscoroutine(result):
                try:
                    loop = asyncio.get_event_loop()
                    result = loop.run_until_complete(result)
                except RuntimeError:
                    result = asyncio.run(result)
            
            # Ensure JSON string output
            if not isinstance(result, str):
                result = json.dumps(result)
                
            return result
        except Exception as e:
            logger.exception(f"Error in {func.__name__}: {str(e)}")
            return json.dumps({
                "error": str(e),
                "status": "error"
            })
    
    return wrapper
```

#### Option B: Revert all changes
```bash
git stash  # Save current work
git checkout -- youtrack_mcp/tools/core_projects.py
git checkout -- youtrack_mcp/tools/core_search.py
# etc...
```

### Phase 1: Core Tools Migration (1 day)
**Goal**: Convert all core tool modules to async  
**Priority**: High  
**Dependencies**: Phase 0 complete

#### 1.1 CoreProjectsTools Migration
```python
# File: youtrack_mcp/tools/core_projects.py

# Step 1: Update imports
from youtrack_mcp.mcp_wrappers import async_wrapper  # Change from sync_wrapper

# Step 2: Convert each method
@async_wrapper  # Change decorator
async def list(self, include_archived: bool = False) -> str:  # Add async
    try:
        projects = await self.projects_api.get_projects(include_archived)  # Add await
        # ... rest of method

@async_wrapper
async def get(self, project_id: str, include: Optional[List[str]] = None) -> str:
    try:
        project = await self.projects_api.get_project(project_id)  # Add await
        # Handle expansions
        if include and "customFields" in include:
            fields = await self.projects_api.get_custom_fields(project_id)  # Add await
        # ...

@async_wrapper
async def patch(self, project_id: str, ops: Optional[List[Dict[str, Any]]] = None) -> str:
    try:
        current_project = await self.projects_api.get_project(project_id)  # Add await
        # Apply updates
        await self.client.post(f"admin/projects/{project_id}", data=updates)  # Add await
        updated_project = await self.projects_api.get_project(project_id)  # Add await
        # ...

@async_wrapper
async def create(self, name: str, short_name: str, lead_id: str) -> str:
    try:
        project = await self.projects_api.create_project(  # Add await
            name=name,
            short_name=short_name,
            lead_id=lead_id
        )
        # ...
```

#### 1.2 CoreSearchTools Migration
```python
# File: youtrack_mcp/tools/core_search.py

from youtrack_mcp.mcp_wrappers import async_wrapper

@async_wrapper
async def query(self, query: str, limit: int = 10) -> str:
    try:
        results = await self.search_api.search_issues(query, limit)  # Add await
        # ...

@async_wrapper
async def autosearch(self, natural_language_query: str) -> str:
    try:
        # Use AI processor for translation
        result = await self.ai_processor.translate_natural_query(natural_language_query)  # Add await
        # Execute search
        issues = await self.search_api.search_issues(result.yql_query)  # Add await
        # ...
```

#### 1.3 CoreUsersTools Migration
```python
# File: youtrack_mcp/tools/core_users.py

from youtrack_mcp.mcp_wrappers import async_wrapper

@async_wrapper
async def search(self, query: str, limit: int = 10) -> str:
    try:
        users = await self.users_api.search_users(query, limit)  # Add await
        # ...
```

#### 1.4 CoreAITools Migration
```python
# File: youtrack_mcp/tools/core_ai.py

from youtrack_mcp.mcp_wrappers import async_wrapper

@async_wrapper
async def plan(self, intent: str) -> str:
    try:
        # Process with AI
        result = await self.ai_processor.process_intent(intent)  # Add await
        # ...
```

#### 1.5 CoreResourcesTools Migration
```python
# File: youtrack_mcp/tools/core_resources.py

from youtrack_mcp.mcp_wrappers import async_wrapper

@async_wrapper
async def read(self, uri: str) -> str:
    try:
        # Fetch resource
        content = await self.client.get(uri)  # Add await
        # ...
```

#### 1.6 Admin Tools Migration
Same pattern for `core_projects_admin.py` and `core_users_admin.py`

### Phase 2: Testing & Validation (4 hours)
**Goal**: Ensure all tools work correctly with complete test coverage  
**Priority**: Critical  
**Dependencies**: Phase 1 complete

#### 2.1 Complete Test Coverage Requirements
**MANDATORY**: The AI coding agent MUST ensure 100% test coverage of the tool surface before proceeding.

**Test Coverage Strategy**:
1. **Use Serena for code search** - Use Serena tool to search for existing tests and identify coverage gaps
2. **Use Morph LLM for refactoring** - Use Morph LLM tool for any test file refactoring or bulk updates
3. **Coverage validation** - Run coverage reports to verify all tool methods are tested
4. **Failed behavior tests** - Create additional tests for error conditions and edge cases

```bash
# Coverage validation command
pytest tests/ --cov=youtrack_mcp --cov-report=html --cov-report=term-missing

# Ensure minimum coverage threshold
pytest tests/ --cov=youtrack_mcp --cov-fail-under=95
```

#### 2.2 Unit Tests Update
```python
# Update all test files to use async
import pytest

@pytest.mark.asyncio
async def test_projects_list():
    tools = CoreProjectsTools()
    result = await tools.list()
    assert isinstance(result, str)
    data = json.loads(result)
    assert "projects" in data

@pytest.mark.asyncio
async def test_projects_list_error_handling():
    """Test error conditions."""
    tools = CoreProjectsTools()
    # Mock API failure
    with pytest.raises(Exception):
        result = await tools.list_with_error()

@pytest.mark.asyncio
async def test_search_query():
    tools = CoreSearchTools()
    result = await tools.query("project: TEST")
    assert isinstance(result, str)
    # ...
```

#### 2.3 Integration Tests
```python
# New file: tests/integration/test_async_tools.py

@pytest.mark.asyncio
async def test_all_tools_async():
    """Verify all tools are properly async."""
    from youtrack_mcp.tools import load_all_tools
    
    tools = load_all_tools()
    for name, func in tools.items():
        assert asyncio.iscoroutinefunction(func), f"{name} is not async!"

@pytest.mark.asyncio
async def test_concurrent_operations():
    """Test concurrent API calls."""
    projects = CoreProjectsTools()
    issues = CoreIssuesTools()
    
    # Should execute concurrently
    results = await asyncio.gather(
        projects.list(),
        issues.get("TEST-1"),
        issues.get("TEST-2"),
    )
    
    assert all(isinstance(r, str) for r in results)

@pytest.mark.asyncio
async def test_error_propagation():
    """Test that errors are properly propagated in async context."""
    # Test various error scenarios
    pass
```

#### 2.4 Test Execution and Bug Fixing
**Process**:
1. **Run all tests** - Execute full test suite
2. **Fix failures** - Debug and fix any failing tests
3. **Add missing tests** - Create tests for uncovered code paths
4. **Validate coverage** - Ensure coverage meets requirements

#### 2.5 Manual Testing Script
```bash
#!/bin/bash
# test_async_migration.sh

echo "Testing YouTrack MCP Async Migration"

# Test 1: Load all tools
python -c "
import asyncio
from youtrack_mcp.tools import load_all_tools

tools = load_all_tools()
print(f'✅ Loaded {len(tools)} tools')

# Check all are async
for name, func in tools.items():
    if not asyncio.iscoroutinefunction(func):
        print(f'❌ {name} is not async!')
        exit(1)
print('✅ All tools are async')
"

# Test 2: Run each tool
python -c "
import asyncio
import json
from youtrack_mcp.tools.projects_tools import ProjectsTools
from youtrack_mcp.tools.search_tools import SearchTools
from youtrack_mcp.tools.users_tools import UsersTools

async def test():
    try:
        # Test projects
        projects = CoreProjectsTools()
        result = await projects.list()
        assert isinstance(result, str)
        print('✅ projects.list works')
        
        # Test search
        search = CoreSearchTools()
        result = await search.query('project: TEST')
        assert isinstance(result, str)
        print('✅ search.query works')
        
        # Test users
        users = CoreUsersTools()
        result = await users.search('admin')
        assert isinstance(result, str)
        print('✅ users.search works')
        
        print('\\n✅ All core tools working!')
    except Exception as e:
        print(f'❌ Test failed: {e}')
        exit(1)

asyncio.run(test())
"
```

### Phase 3: Performance Optimization (1 day)
**Goal**: Leverage async for better performance  
**Priority**: Medium  
**Dependencies**: Phase 2 complete

#### 3.1 Add Concurrent Operations
```python
# Example: Fetch multiple issues concurrently
@async_wrapper
async def get_multiple(self, issue_ids: List[str]) -> str:
    """Get multiple issues concurrently."""
    try:
        # Concurrent fetching
        issues = await asyncio.gather(*[
            self.issues_api.get_issue(issue_id) 
            for issue_id in issue_ids
        ])
        
        return format_json_response({
            "issues": issues,
            "count": len(issues)
        })
    except Exception as e:
        # ...
```

#### 3.2 Connection Pooling
```python
# In api/client.py
class YouTrackClient:
    def __init__(self):
        # Use connection pooling
        self.client = httpx.AsyncClient(
            limits=httpx.Limits(
                max_keepalive_connections=20,
                max_connections=100,
            ),
            timeout=30.0,
        )
```

#### 3.3 Background Caching
```python
# Add caching with background refresh
class CachedProjectsTools(CoreProjectsTools):
    def __init__(self):
        super().__init__()
        self._cache = {}
        self._cache_task = None
    
    async def _refresh_cache(self):
        """Background cache refresh."""
        while True:
            try:
                projects = await self.projects_api.get_projects()
                self._cache['projects'] = projects
                await asyncio.sleep(300)  # Refresh every 5 min
            except Exception as e:
                logger.error(f"Cache refresh failed: {e}")
                await asyncio.sleep(60)  # Retry in 1 min
```

### Phase 4: Documentation & Cleanup (2 hours)
**Goal**: Update docs and remove old code  
**Priority**: Low  
**Dependencies**: Phase 3 complete

#### 4.1 Update Documentation
- [ ] Update README with async examples
- [ ] Update API documentation
- [ ] Add migration guide for users
- [ ] Document performance improvements

#### 4.2 Remove Old Code
- [ ] Remove sync_wrapper if no longer needed
- [ ] Clean up old test files
- [ ] Remove compatibility shims

#### 4.3 Update Examples
```python
# docs/examples/async_usage.py
import asyncio
from youtrack_mcp.tools import load_all_tools

async def main():
    tools = load_all_tools()
    
    # All tools are now async
    projects_tool = tools['projects.list']
    result = await projects_tool()
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
```

## Task Checklist

### Immediate (Today)
- [ ] Apply Phase 0 emergency fix
- [ ] Test that basic functionality works
- [ ] Commit stabilization changes

### Day 1
- [ ] Convert CoreProjectsTools to async (4 methods)
- [ ] Convert CoreSearchTools to async (2 methods)
- [ ] Convert CoreUsersTools to async (1 method)
- [ ] Convert CoreAITools to async (1 method)
- [ ] Convert CoreResourcesTools to async (1 method)
- [ ] Run basic tests after each conversion

### Day 2
- [ ] Convert CoreProjectsAdminTools to async (3 methods)
- [ ] Convert CoreUsersAdminTools to async (3 methods)
- [ ] Update all unit tests to async
- [ ] Create integration tests
- [ ] Run full test suite

### Day 3
- [ ] Implement concurrent operations
- [ ] Add connection pooling
- [ ] Performance testing
- [ ] Documentation updates
- [ ] Final cleanup

## Verification Steps

### After Each Module Conversion
```bash
# Quick test
python -c "
import asyncio
from youtrack_mcp.tools.[module]_tools import [Module]Tools

async def test():
    tools = Core[Module]Tools()
    # Test each method
    result = await tools.[method]()
    assert isinstance(result, str)
    print('✅ [method] works')

asyncio.run(test())
"
```

### After Full Migration
```bash
# Run full test suite
pytest tests/ -v --asyncio-mode=auto

# Check no sync methods remain
grep -r "@sync_wrapper" youtrack_mcp/tools/core_*.py
# Should return nothing

# Verify all async
python -c "
from youtrack_mcp.tools import load_all_tools
import asyncio

tools = load_all_tools()
sync_tools = [name for name, func in tools.items() 
              if not asyncio.iscoroutinefunction(func)]
if sync_tools:
    print(f'❌ Still sync: {sync_tools}')
else:
    print('✅ All tools are async!')
"
```

## Risk Mitigation

### Rollback Plan
```bash
# If migration fails, rollback to last working state
git stash  # Save current work
git checkout feature/async-migration-backup
```

### Incremental Migration
- Convert one module at a time
- Test after each conversion
- Commit working state frequently
- Keep old sync_wrapper as fallback

### Testing Strategy
- Unit tests for each method
- Integration tests for tool interactions
- Performance benchmarks
- Manual testing with real API

## Success Criteria

### Functional
- [ ] All 8 core tool modules work without errors
- [ ] No "coroutine not iterable" errors
- [ ] All tests pass
- [ ] MCP server handles all tools correctly

### Performance
- [ ] 3x faster for bulk operations
- [ ] Concurrent API calls work
- [ ] Memory usage stable
- [ ] No blocking I/O

### Code Quality
- [ ] Consistent async pattern throughout
- [ ] No sync/async mixing
- [ ] Clear error handling
- [ ] Comprehensive documentation

## Timeline

### Day 0 (Today)
- **Morning**: Apply emergency fix (Phase 0)
- **Afternoon**: Start Phase 1 conversions

### Day 1
- **Morning**: Complete Phase 1 (all conversions)
- **Afternoon**: Start Phase 2 (testing)

### Day 2
- **Morning**: Complete Phase 2 testing
- **Afternoon**: Phase 3 optimizations

### Day 3
- **Morning**: Phase 4 documentation
- **Afternoon**: Final review and deployment

## Communication Plan

### Stakeholders
- Development Team: Daily updates
- QA Team: Test plans by Day 1
- Users: Migration notice with timeline

### Status Updates
```markdown
## Migration Status (Updated: DATE)

### Completed ✅
- [x] CoreIssuesTools (3 methods)

### In Progress 🔄
- [ ] CoreProjectsTools (0/4 methods)

### Pending ⏳
- [ ] CoreSearchTools (0/2 methods)
- [ ] CoreUsersTools (0/1 methods)
- [ ] CoreAITools (0/1 methods)
- [ ] CoreResourcesTools (0/1 methods)
- [ ] CoreProjectsAdminTools (0/3 methods)
- [ ] CoreUsersAdminTools (0/3 methods)

**Total Progress**: 3/18 methods (17%)
```

## Post-Migration Tasks

1. **Performance Benchmarking**
   - Compare before/after metrics
   - Document improvements
   - Identify further optimization opportunities

2. **User Migration Guide**
   - Update examples
   - Provide migration scripts
   - FAQ for common issues

3. **Monitoring**
   - Set up async-specific monitoring
   - Track coroutine performance
   - Monitor memory usage

4. **Future Improvements**
   - Consider AsyncIO alternatives (Trio, AnyIO)
   - Implement WebSocket support
   - Add streaming responses

---

**Note**: This migration is critical. The system is currently broken and will not function correctly until this migration is complete. Priority should be given to Phase 0 and Phase 1 to restore basic functionality as quickly as possible.