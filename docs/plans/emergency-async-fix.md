# Emergency Fix for Broken Async/Sync Architecture

**Date**: 2025-09-09  
**Priority**: 🚨 CRITICAL - System is non-functional  
**Time to Fix**: 30 minutes

## Current Situation

The codebase is in a **broken state** where:
1. Someone added `await` keywords to sync methods (causing SyntaxError)
2. Sync methods are calling async API methods without proper handling
3. The system cannot function in this state

## Immediate Fix Options

### Option 1: Make Everything Async (Recommended) ✅

**Time**: 20 minutes

```python
# In core_projects.py - Change ALL methods to async

from youtrack_mcp.mcp_wrappers import async_wrapper  # Change import

class CoreProjectsTools:
    
    @async_wrapper  # Change decorator
    async def list(self, include_archived: bool = False) -> str:  # Add async
        try:
            projects = await self.projects_api.get_projects(include_archived=include_archived)  # await works now!
            # ...
    
    @async_wrapper  # Change decorator
    async def get(self, project_id: str, include: Optional[List[str]] = None) -> str:  # Add async
        try:
            project = await self.projects_api.get_project(project_id)  # Add await
            # ...
            if "customFields" in include:
                fields = await self.projects_api.get_custom_fields(project_id)  # Add await
            # ...
    
    @async_wrapper  # Change decorator
    async def patch(self, project_id: str, ops: Optional[List[Dict[str, Any]]] = None) -> str:  # Add async
        try:
            current_project = await self.projects_api.get_project(project_id)  # Add await
            # ...
            await self.client.post(f"admin/projects/{project_id}", data=updates)  # Add await
            updated_project = await self.projects_api.get_project(project_id)  # Add await
            # ...
    
    @async_wrapper  # Change decorator
    async def create(self, name: str, short_name: str, lead_id: str) -> str:  # Add async
        try:
            project = await self.projects_api.create_project(  # Add await
                name=name,
                short_name=short_name,
                lead_id=lead_id
            )
            # ...
```

### Option 2: Remove All Awaits (Quick but Wrong) ❌

**Time**: 5 minutes  
**Result**: Code will compile but won't work - will return coroutine objects

```python
# Remove all 'await' keywords from sync methods
# This will make the code compile but it won't actually work!
```

### Option 3: Add Sync Bridge to sync_wrapper 🔧

**Time**: 10 minutes

```python
# In mcp_wrappers.py - Update sync_wrapper to handle coroutines

import asyncio

def sync_wrapper(func: Callable) -> Callable:
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            result = func(*processed_args, **processed_kwargs)
            
            # NEW: Handle coroutines
            if asyncio.iscoroutine(result):
                # Create new event loop if needed
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # Use nest_asyncio if available
                        import nest_asyncio
                        nest_asyncio.apply()
                    result = loop.run_until_complete(result)
                except RuntimeError:
                    # No event loop, create one
                    result = asyncio.run(result)
            
            return result
        except Exception as e:
            # ...
```

## Recommended Action Plan

### Step 1: Fix Syntax Errors (5 min)
```bash
# Revert the broken changes
git checkout -- youtrack_mcp/tools/core_projects.py

# Or fix them properly by adding async/await everywhere
```

### Step 2: Apply Option 1 - Make Everything Async (15 min)

1. **Update core_projects.py**:
   - Change all `@sync_wrapper` to `@async_wrapper`
   - Add `async` to all method definitions
   - Keep the `await` keywords that were added

2. **Update other core tools** (same pattern):
   - core_search.py
   - core_users.py
   - core_ai.py
   - core_resources.py
   - core_projects_admin.py
   - core_users_admin.py

3. **Test the changes**:
```python
# Quick test script
import asyncio
from youtrack_mcp.tools.core_projects import CoreProjectsTools

async def test():
    tools = CoreProjectsTools()
    result = await tools.list()
    print("Success!" if result else "Failed")

asyncio.run(test())
```

### Step 3: Update Tests (10 min)

```python
# Update all tests to be async
@pytest.mark.asyncio
async def test_projects_list():
    tools = CoreProjectsTools()
    result = await tools.list()
    assert isinstance(result, str)
```

## Files to Modify

### Priority 1 (Broken - Fix First):
- [x] `youtrack_mcp/tools/core_projects.py` - Has syntax errors with await in sync functions

### Priority 2 (Convert to Async):
- [ ] `youtrack_mcp/tools/core_search.py`
- [ ] `youtrack_mcp/tools/core_users.py`
- [ ] `youtrack_mcp/tools/core_ai.py`
- [ ] `youtrack_mcp/tools/core_resources.py`
- [ ] `youtrack_mcp/tools/core_projects_admin.py`
- [ ] `youtrack_mcp/tools/core_users_admin.py`

### Priority 3 (Already Fixed):
- [x] `youtrack_mcp/tools/core_issues.py` - Already async ✅
- [x] `youtrack_mcp/mcp_wrappers.py` - Has async_wrapper ✅

## Testing Commands

```bash
# Run tests
pytest tests/unit/tools/test_core_*.py -v

# Quick manual test
python -c "
import asyncio
from youtrack_mcp.tools import load_all_tools
tools = load_all_tools()
print(f'Loaded {len(tools)} tools')
for name, func in tools.items():
    print(f'{name}: {'async' if asyncio.iscoroutinefunction(func) else 'sync'}')
"
```

## Why This Happened

1. **API Layer is Async**: All `youtrack_mcp/api/*.py` files use async methods
2. **Tools Layer was Sync**: Core tools were using sync_wrapper
3. **Mismatch**: Sync methods can't call async methods without special handling
4. **Partial Fix**: Someone started adding `await` but didn't finish the conversion

## Long-term Solution

After the emergency fix, implement the full migration plan from `async-architecture-analysis.md`:
1. All tools should be async
2. Remove sync_wrapper entirely
3. Use asyncio.gather() for concurrent operations
4. Add proper error handling for async operations

## Verification

After applying the fix:

```python
# This should work without errors
import asyncio
from youtrack_mcp.tools.core_projects import CoreProjectsTools
from youtrack_mcp.tools.core_issues import CoreIssuesTools

async def verify():
    projects = CoreProjectsTools()
    issues = CoreIssuesTools()
    
    # All these should return JSON strings, not coroutines
    p_result = await projects.list()
    i_result = await issues.get("TEST-1")
    
    assert isinstance(p_result, str)
    assert isinstance(i_result, str)
    print("✅ All tools working correctly!")

asyncio.run(verify())
```

---

**Action Required**: Apply Option 1 immediately to restore functionality.