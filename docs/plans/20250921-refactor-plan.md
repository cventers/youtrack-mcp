# YouTrack MCP Comprehensive Refactoring Plan

**Date:** 2025-09-21
**Version:** 1.0
**Status:** READY FOR EXECUTION
**Priority:** High

## Executive Summary

This refactoring plan addresses code quality, maintainability, and consistency issues in the YouTrack MCP codebase following the v3 LLM implementation. The plan focuses on removing dead code, eliminating backward compatibility cruft, ensuring Python best practices, and improving documentation accuracy.

## Tool Usage Instructions

**IMPORTANT**: This plan is designed to be executed by AI coding agents using specific tools:
- **Use `serena` for codebase search and analysis** - Activate project with `mcp__serena__activate_project`
- **Use `morphllm` for file editing** - Utilize `mcp__morphllm-fast-apply__edit_file` for modifications
- **Always test changes after each section** with `pytest -xvs`

## Refactoring Agent Guidance

Based on the refactoring-specialist and python-expert agents, this plan follows these principles:

### Code Smell Detection Priority
1. **Long methods** - Extract methods for any function >20 lines
2. **Large classes** - Split classes with >7 methods or >100 lines
3. **Long parameter lists** - Replace with parameter objects for >3 params
4. **Duplicate code** - Consolidate any repeated code blocks
5. **Complex conditionals** - Extract to well-named methods

### Safety Practices (CRITICAL)
- **Zero behavior changes** - Verify with existing tests
- **Small incremental changes** - One refactoring at a time
- **Test after each change** - Run `pytest` after every modification
- **Commit frequently** - Git commit after each successful refactoring
- **Measure metrics** - Track complexity reduction and coverage

### Python-Specific Standards
- **Type hints**: All functions must have complete type annotations
- **Formatting**: Apply `black` (line length 88) and `isort`
- **Linting**: Pass `pylint` and `flake8` checks
- **Type checking**: Pass `mypy` in strict mode
- **Test coverage**: Maintain >80% coverage, aim for >90%

### Refactoring Workflow (Per Task)
1. **Identify smell** - Use metrics and patterns
2. **Write/verify tests** - Ensure behavior is captured
3. **Make ONE change** - Single refactoring at a time
4. **Run tests** - Verify no behavior change
5. **Check metrics** - Confirm improvement
6. **Commit** - Save working state
7. **Document** - Update docstrings/comments if needed

## Identified Issues

### 1. Backward Compatibility Cruft
- `QueryTranslationResult` dataclass still defined in `youtrack_mcp/ai/__init__.py`
- `ErrorEnhancementResult` in `youtrack_mcp/utils.py` and `utils/__init__.py` (duplicate)
- Multiple references to "backward compatibility" in comments
- Old import patterns in `youtrack_mcp/ai/__init__.py`

### 2. Type Hints Inconsistencies
- Missing return type hints on `__init__` methods (should be `-> None`)
- Inconsistent type hint usage in utility functions
- Several methods missing return type annotations

### 3. Import Organization
- Some files have imports scattered between module docstrings and code
- Duplicate utility modules (`utils.py` and `utils/__init__.py`)

### 4. Dead Code
- Unused backward compatibility exports in `ai/models.py`
- Legacy field getters in projects API

### 5. Documentation Issues
- CLAUDE.md still references old tool naming conventions
- Missing documentation for v3 LLM changes
- Outdated references in docstrings

## Refactoring Tasks

### Phase 1: Remove Backward Compatibility Code

#### Task 1.1: Clean up AI module
**File:** `youtrack_mcp/ai/__init__.py`
**Using:** `morphllm`

```python
# REMOVE:
- QueryTranslationResult dataclass definition (lines 18-26)
- QueryTranslationResult from __all__ export

# KEEP ONLY:
- Essential imports for current architecture
- Models that are actively used
```

#### Task 1.2: Remove duplicate ErrorEnhancementResult
**Files:** `youtrack_mcp/utils.py`, `youtrack_mcp/utils/__init__.py`
**Using:** `serena` to identify which is canonical, then `morphllm` to consolidate

```python
# ACTION:
1. Determine which file is the primary utils module
2. Remove duplicate definitions
3. Update all imports to use single source
```

#### Task 1.3: Remove backward compatibility comments
**Using:** `serena` search, then `morphllm` edit

```bash
# Search pattern:
"backward.?compat|deprecated|legacy|old.?format"

# Remove or update:
- Line comments mentioning backward compatibility
- Docstrings referencing deprecated features
- Alias methods that exist only for compatibility
```

### Phase 2: Fix Type Hints

#### Task 2.1: Add missing return types for __init__ methods
**Using:** `morphllm` with batch editing

```python
# Pattern to fix:
def __init__(self):  # Missing -> None
# Should be:
def __init__(self) -> None:
```

**Files to update:**
- `youtrack_mcp/tools/users_admin_tools.py:23`
- `youtrack_mcp/tools/issues_tools.py:38`
- `youtrack_mcp/tools/resources.py:36`
- `youtrack_mcp/tools/issues/dedicated_updates.py:26`
- `youtrack_mcp/tools/issues/diagnostics.py:24`
- `youtrack_mcp/tools/issues/__init__.py:42`
- `youtrack_mcp/tools/issues/comments.py:24`
- `youtrack_mcp/tools/issues/utilities.py:21`
- `youtrack_mcp/tools/issues/custom_fields.py:25`
- `youtrack_mcp/tools/issues/linking.py:25`

#### Task 2.2: Add missing return types for methods
**Using:** `serena` to find, `morphllm` to fix

```python
# Methods missing return types should specify:
-> Dict[str, Any]  # For dictionary returns
-> str            # For string returns
-> None           # For procedures
-> bool           # For boolean returns
```

### Phase 3: Clean Up Imports

#### Task 3.1: Organize imports consistently
**Using:** `morphllm` with isort pattern

```python
# Standard library imports
import json
import logging
from typing import Any, Dict, Optional

# Third-party imports
from pydantic import BaseModel

# Local imports
from youtrack_mcp.api.client import YouTrackClient
```

#### Task 3.2: Remove unused imports
**Using:** `serena` to identify, `morphllm` to remove

```bash
# Run flake8 to identify unused imports:
flake8 youtrack_mcp --select=F401
```

### Phase 4: Remove Dead Code

#### Task 4.1: Remove unused re-exports
**File:** `youtrack_mcp/ai/models.py:151`
**Using:** `morphllm`

```python
# Remove:
# Re-export for backward compatibility
__all__ = [...]  # If these aren't used externally
```

### Phase 5: Clean Up Versioned and Enhanced Naming

#### Task 5.1: Remove version suffixes from files and symbols
**Using:** `serena` to find, `morphllm` to rename

```bash
# Search patterns for versioned names:
"_v[0-9]|_v3|_enhanced|_refactored|_new|_old|_legacy"

# Files/symbols that need renaming:
- Any files ending with _v2.py, _v3.py, etc.
- Classes/functions with Enhanced, Refactored, New prefixes/suffixes
- Variables with version numbers in names
```

**Specific files and imports to fix:**
```python
# In youtrack_mcp/tools/ai_tools.py:
from youtrack_mcp.tools.ai_tools_v3 import AITools as AIToolsImpl
# Should be: from youtrack_mcp.tools.ai_tools_impl import AITools as AIToolsImpl
# OR just merge the implementation directly

# In youtrack_mcp/ai/registry.py:
from .service_v3 import AIService
from ..config_v3 import Settings  
# Should be: from .service import AIService
# Should be: from ..config import Settings

# In youtrack_mcp/api/issues.py:
def _create_enhanced_field_object(...)
# Should be: def _create_field_object(...)
```

**Common renames needed:**
```python
# Examples of what to fix:
SomethingEnhanced -> Something
something_v3() -> something()
new_implementation() -> implementation()
enhanced_error_handler() -> error_handler()
RefactoredClient -> Client
_create_enhanced_field_object() -> _create_field_object()
```

**Comments to clean up:**
```python
# Remove or rephrase comments like:
"Enhanced search tools with intelligent features" -> "Search tools with intelligent features"
"Enhanced error handling" -> "Error handling"
"Dedicated Updates (Enhanced)" -> "Dedicated Updates"
"Enhanced approach with proper YouTrack objects" -> "Using YouTrack objects"
```

#### Task 5.2: Normalize module and file names
**Using:** `morphllm` to rename files and update imports

```python
# Ensure all files follow consistent naming:
- No version numbers in filenames
- No "enhanced", "new", "refactored" prefixes
- Use descriptive names that reflect actual functionality
```

#### Task 5.3: Update all imports after renaming
**Using:** `serena` to find all imports, `morphllm` to update

```python
# After renaming files/symbols, update all imports:
from module_v3 import Enhanced -> from module import Component
from enhanced_utils import new_func -> from utils import func
```

### Phase 6: Update Documentation

#### Task 6.1: Update CLAUDE.md
**File:** `CLAUDE.md`
**Using:** `morphllm`

```markdown
# Update:
- Remove references to old tool naming conventions
- Add v3 LLM architecture documentation
- Update tool list to reflect current state
- Add section on LiteLLM/Instructor usage
```

#### Task 6.2: Update docstrings
**Using:** `serena` to find outdated references, `morphllm` to update

```python
# Update docstrings that reference:
- Deprecated methods
- Old architecture
- Removed features
```

### Phase 7: Testing and Validation

#### Task 7.1: Run comprehensive tests
**Using:** Shell commands

```bash
# Run all tests
pytest -xvs

# Run with coverage
pytest --cov=youtrack_mcp --cov-report=term-missing

# Run linting
flake8 youtrack_mcp
mypy youtrack_mcp

# Check imports
isort --check-only youtrack_mcp
```

#### Task 7.2: Create missing tests
**Using:** `morphllm` to create test files

```python
# Priority test areas:
- v3 LLM client functionality
- Template rendering
- Async AI service methods
- Error handling paths
```

## Execution Order

1. **Backup current state**
   ```bash
   git checkout -b refactor/cleanup-20250921
   git add -A && git commit -m "chore: checkpoint before refactoring"
   ```

2. **Execute Phase 1** - Remove backward compatibility (highest priority)
3. **Execute Phase 2** - Fix type hints
4. **Execute Phase 3** - Clean up imports
5. **Execute Phase 4** - Remove dead code
6. **Execute Phase 5** - Clean up versioned and enhanced naming
7. **Execute Phase 6** - Update documentation
8. **Execute Phase 7** - Test everything

## Success Criteria

- [ ] No references to backward compatibility remain (except where truly needed)
- [ ] All functions have proper type hints
- [ ] All imports are organized consistently
- [ ] No duplicate code or modules exist
- [ ] Documentation accurately reflects current implementation
- [ ] All tests pass with >80% coverage
- [ ] Linting produces no errors
- [ ] Type checking (mypy) produces no errors

## Code Metrics and Quality Gates

### Metrics to Track
**Before and after each phase, measure:**
- **Cyclomatic Complexity**: Target <10 per function
- **Cognitive Complexity**: Target <15 per function
- **Lines per Function**: Target <20 lines
- **Lines per Class**: Target <100 lines
- **Parameters per Function**: Target ≤3 parameters
- **Test Coverage**: Maintain >80%, target >90%
- **Code Duplication**: Target <5% duplication

### Quality Gate Checklist
**Before committing any changes:**
- [ ] `pytest` - All tests pass
- [ ] `pytest --cov=youtrack_mcp --cov-report=term-missing` - Coverage >80%
- [ ] `black youtrack_mcp` - Code formatted
- [ ] `isort youtrack_mcp` - Imports sorted
- [ ] `flake8 youtrack_mcp` - No linting errors
- [ ] `pylint youtrack_mcp` - Score >8.0/10
- [ ] `mypy youtrack_mcp` - No type errors
- [ ] `bandit -r youtrack_mcp` - No security issues

### Automated Tools Setup
```bash
# Install quality tools
pip install black isort flake8 pylint mypy bandit pytest-cov

# Run all checks
black youtrack_mcp --check
isort youtrack_mcp --check-only
flake8 youtrack_mcp
pylint youtrack_mcp
mypy youtrack_mcp
bandit -r youtrack_mcp
pytest --cov=youtrack_mcp
```

## Risk Mitigation

1. **Create feature branch** before starting
2. **Test after each phase** to catch breaking changes early
3. **Commit frequently** with descriptive messages
4. **Document any API changes** that might affect users
5. **Keep backward compatibility** only where external tools depend on it

## Tools Configuration

### For AI Agents Using This Plan

```python
# Serena activation
mcp__serena__activate_project("youtrack-mcp")

# Search pattern examples
mcp__serena__search_for_pattern(
    substring_pattern="backward|deprecated|legacy",
    context_lines_before=2,
    context_lines_after=2
)

# Morphllm edit example
mcp__morphllm-fast-apply__edit_file(
    path="youtrack_mcp/ai/__init__.py",
    code_edit="Remove QueryTranslationResult class",
    instruction="Remove the deprecated dataclass and its export"
)
```

## Estimated Timeline

- **Phase 1:** 2 hours
- **Phase 2:** 1 hour
- **Phase 3:** 1 hour
- **Phase 4:** 1 hour
- **Phase 5:** 1 hour
- **Phase 6:** 2 hours

**Total:** ~8 hours of focused work

## Post-Refactoring Tasks

1. Update CHANGELOG.md with refactoring details
2. Create PR with clear description of changes
3. Request code review focusing on:
   - Breaking changes
   - Type safety improvements
   - Documentation accuracy
4. Update version number if breaking changes exist
5. Consider creating migration guide if API changed

## Notes for Implementers

- **Prioritize removing backward compatibility cruft** - It adds confusion and maintenance burden
- **Be aggressive about dead code removal** - If it's not used, delete it
- **Ensure consistency** - Same patterns throughout the codebase
- **Test frequently** - Catch issues early
- **Document why, not what** - Remove obvious comments, keep architectural decisions

## Appendix: Specific Code Patterns to Remove

### Pattern 1: Backward Compatibility Aliases
```python
# REMOVE patterns like:
def old_method_name(self, *args, **kwargs):
    """Alias for new_method_name for backward compatibility."""
    return self.new_method_name(*args, **kwargs)
```

### Pattern 2: Deprecated Imports
```python
# REMOVE patterns like:
try:
    from old_module import OldClass
except ImportError:
    from new_module import NewClass as OldClass
```

### Pattern 3: Legacy Comments
```python
# REMOVE comments like:
# TODO: Remove in v2.0
# DEPRECATED: Use new_function instead
# BACKWARD COMPATIBILITY: Keep until migration complete
# NOTE: This is for legacy support
```

### Pattern 4: Unused Type Definitions
```python
# REMOVE if not used:
@dataclass
class LegacyResult:
    """Old result format, kept for compatibility."""
    ...
```

## Verification Checklist

After completing all phases, verify:

- [ ] `grep -r "backward" youtrack_mcp/` returns no results (except valid uses)
- [ ] `grep -r "deprecated" youtrack_mcp/` returns no results
- [ ] `grep -r "legacy" youtrack_mcp/` returns no results
- [ ] `grep -r "TODO" youtrack_mcp/` returns only valid future tasks
- [ ] `mypy youtrack_mcp` runs without errors
- [ ] `flake8 youtrack_mcp` runs without errors
- [ ] `pytest` achieves >80% code coverage
- [ ] Documentation is accurate and complete

---

**END OF REFACTORING PLAN**

*This plan should be executed systematically, with careful attention to testing after each phase. The goal is a cleaner, more maintainable codebase that follows Python best practices and is easier for future developers (human or AI) to work with.*