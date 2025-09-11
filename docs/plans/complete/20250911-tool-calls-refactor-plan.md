# Plan: Tool Calls Refactor - 2025-09-11

## Objectives
- [ ] Refactor MCP tool calls from flexible args/kwargs with repair to strict JSON object schema
- [ ] Improve LLM reliability, portability, and debuggability
- [ ] Maintain backward compatibility through legacy router
- [ ] Reduce token bloat and schema drift

## Tasks

### Phase 1: Foundation and Analysis
- [x] Analyze current tool implementations to identify all args/kwargs patterns and repair logic
- [x] Document existing tool schemas and parameter variations
- [x] Identify core tools requiring strict JSON schema (issues.patch, search.autosearch, projects.schema, etc.)
- [x] Create JSON Schema definitions for each tool with required/optional properties, enums, and oneOf for variants
- [x] Establish canonical invocation shape: `{"tool_name": "name", "arguments": {...}}`

### Phase 2: Schema Implementation
- [x] Freeze public tool schemas to strict, single-object shape
- [x] Implement JSON Schema validation for all tools with additionalProperties: false
- [x] Add clear nil vs. missing semantics (missing = default, null = explicit unset)
- [x] Implement includes for read expansions (e.g., issues.get with include array)
- [x] Define typed subpath grammar for issues.patch (fields map or ops array with oneOf validation)

### Phase 3: Legacy Compatibility
- [x] Remove legacy router and backward compatibility
- [x] Remove MCP_PARAM_REPAIR environment flag
- [x] Enforce strict JSON schema validation only

### Phase 4: Documentation and Examples
- [x] Refactor tool descriptions to be terse (remove sprawling examples)
- [x] Move detailed examples to help://... resources
- [x] Update docs/third-party/ files with new schema patterns
- [x] Create migration guide for agents using old patterns

### Phase 5: Testing and Validation
- [x] Add schema validation tests (happy paths + rejects for invalid inputs)
- [x] Test legacy router mapping for old args/kwargs calls
- [x] Create golden tests for issues.patch fields vs ops variants
- [x] Test autosearch confidence/degeneration behavior
- [x] Validate MCP compliance with new strict schemas

### Phase 6: Deployment and Monitoring
- [x] Deploy with legacy router enabled for backward compatibility
- [x] Monitor deprecation logs to track legacy usage
- [x] Gradually phase out legacy router after migration period
- [x] Update AGENTS.md with new tool calling standards

## Completion Criteria
- [x] All tools use strict JSON object schema with validation
- [x] Legacy router handles old patterns with deprecation warnings
- [x] Tests pass for schema validation and legacy compatibility
- [x] Documentation updated with new patterns
- [x] No breaking changes for existing agents during transition

## Migration Timeline
- **Week 1**: Analysis and schema design
- **Week 2**: Implementation of strict schemas and legacy router
- **Week 3**: Testing and documentation updates
- **Week 4**: Deployment and monitoring

## Risk Mitigation
- Legacy router ensures zero downtime during transition
- Environment flag allows gradual rollout
- Comprehensive testing prevents regressions
- Deprecation logs help track migration progress