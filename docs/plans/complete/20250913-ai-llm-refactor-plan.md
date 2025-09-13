# Plan: AI/LLM Refactor - 2025-09-13

## Objectives
- Reorganize AI/LLM and error mapping code for better maintainability
- Move utility modules out of tools/ directory to appropriate locations
- Rename ai_planning_tools.py to ai_tools.py (resolve naming conflicts)
- Consolidate AI-related code into coherent structure

## Tasks

### Phase 1: Analysis and Planning
- [x] Analyze current AI/LLM code structure and dependencies
- [x] Identify utility modules in tools/ that should be moved
- [x] Map out new directory structure for AI components
- [x] Document naming conflicts and resolution strategy

### Phase 2: Utility Module Relocation
- [x] Move `datetime_utils.py` from `tools/` to `utils/` directory
- [x] Move `help_resources.py` from `tools/` to appropriate location (consider `utils/` or new `help/` directory)
- [x] Move `loader.py` from `tools/` to `utils/` or keep in `tools/` if tool-loading specific
- [x] Update all import statements for moved modules

### Phase 3: AI Tools Reorganization
- [x] Rename `ai_planning_tools.py` to `ai_tools.py` (resolve conflict with existing `ai/ai_tools.py`)
- [x] Consolidate AI tool implementations into single coherent module
- [x] Update imports and references to use new AI tools structure
- [x] Ensure MCP tool registration works with new structure

### Phase 4: Error Mapping Consolidation
- [x] Move `llm_error_responses.py` to `ai/` directory as `error_educator.py`
- [x] Integrate error handling with AI service if appropriate
- [x] Update all imports and references to error mapping code

### Phase 5: Directory Structure Cleanup
- [x] Review `tools/ai/` subdirectory - determine if it should be merged or restructured
- [x] Ensure all AI-related code is properly organized
- [x] Remove any duplicate or obsolete files

### Phase 6: Testing and Validation
- [x] Run full test suite to ensure no regressions
- [x] Verify MCP tool registration and functionality
- [x] Test AI features (planning, query translation, error handling)
- [x] Update any documentation references to moved modules

## Completion Criteria
- [ ] All utility modules moved out of `tools/` directory
- [ ] AI tools properly renamed and consolidated
- [ ] Error mapping code integrated with AI components
- [ ] All tests passing
- [ ] No broken imports or references
- [x] Code structure follows project conventions