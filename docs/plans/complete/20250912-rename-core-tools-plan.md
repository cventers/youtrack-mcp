# Plan: Rename Core Tools - 2025-09-12

## Objectives
- [x] Rename all `core_*` tool files to more descriptive names
- [x] Update all import statements across the codebase
- [x] Ensure backward compatibility during transition
- [x] Update documentation references
- [x] Verify all tests pass after renaming

## Tasks

### Phase 1: Analysis and Planning
- [x] Identify all `core_*` files in `youtrack_mcp/tools/` directory
- [x] Analyze import dependencies and usage patterns
- [x] Choose new naming convention (e.g., `issues_tools.py`, `projects_tools.py`, etc.)
- [x] Create mapping of old names to new names

### Phase 2: File Renaming
- [x] Rename `core_issues.py` → `issues_tools.py`
- [x] Rename `core_projects.py` → `projects_tools.py`
- [x] Rename `core_projects_admin.py` → `projects_admin_tools.py`
- [x] Rename `core_search.py` → `search_tools.py`
- [x] Rename `core_users.py` → `users_tools.py`
- [x] Rename `core_users_admin.py` → `users_admin_tools.py`
- [x] Rename `core_ai.py` → `ai_tools.py`
- [x] Rename `core_resources.py` → `resources_tools.py`

### Phase 3: Import Updates
- [x] Update imports in `loader.py`
- [x] Update imports in `mcp_server.py`
- [x] Update imports in test files
- [x] Update imports in other tool files
- [x] Update any documentation files referencing core_* files

### Phase 4: Testing and Validation
- [x] Run full test suite to ensure no broken imports
- [x] Test MCP tool functionality
- [x] Verify Claude CLI compatibility
- [x] Check for any missed references

### Phase 5: Cleanup
- [x] Remove any backup files if created
- [x] Update AGENTS.md with new naming convention
- [x] Move plan to docs/plans/complete/

## Completion Criteria
- [x] All `core_*` files successfully renamed
- [x] Zero import errors in codebase
- [x] All tests passing
- [x] Documentation updated
- [x] No functionality regressions

## Risk Mitigation
- Create backups before renaming
- Test incrementally after each rename
- Keep old files temporarily if needed for rollback