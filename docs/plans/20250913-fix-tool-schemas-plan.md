# Plan: Fix Tool Schemas and Enable Strict Server - 2025-09-13

## Objectives
- Enable strict JSON-schema validation as the default for all MCP tools
- Align published tool schemas with current implementations
- Remove ambiguity in parameter handling (no args/kwargs repair in default path)
- Update tests and documentation to reflect canonical invocation shape
- Implement pagination for projects.list
- Add support for comments/links expansions in issues.get

## Non-Goals
- Introduce new tools or expand the default tool surface
- Large behavioral changes in API clients
- Immediate removal of wrapper modules (follow in Phase 2 after adoption)

## Background
Current runtime uses wrappers and server-level repair to accept args/kwargs and alias parameters. Docs claim strict JSON schemas, but main.py wires the flexible server by default. A strict server exists but isn't default.

## Decisions
- Make StrictYouTrackMCPServer the default in both stdio and http modes
- Validate HTTP tool calls using schemas prior to execution
- Adjust schemas to match current tool signatures/behavior
- Keep wrappers temporarily (Phase 1) — they will be no-ops under strict validation; remove in Phase 2
- **YES to pagination**: Add $top/$skip support in ProjectsClient.get_projects and keep limit/offset in schema instead of include_archived
- **YES to comment fetching**: Support comments/links expansions in issues.get schema and implementation

## Work Plan

### Phase 1: Enable Strict Server + Align Schemas + Implement Enhancements
- [ ] Switch main.py to StrictYouTrackMCPServer for stdio and http; register tools via register_tools_from_loader
  - Update imports and server instantiation
  - Change registration method
- [ ] Add HTTP validation for /api/tools/{tool} calls against JSON schemas before execution
  - Import validate_tool_call from schemas
  - Add validation in execute_tool method
- [ ] Update schemas in youtrack_mcp/schemas.py to match actual tool signatures/behavior
  - issues.get: Expand include_enum to include comments, links, work_items, history, activities, time_tracking (full support)
  - issues.patch: Keep ops with set operation, maintain fields{} or ops[] oneOf
  - projects.list: Add limit/offset parameters for pagination, keep include_archived
  - projects.get: Expand include_enum to include versions, builds, subsystems, assignees, fields
  - projects.patch: Keep ops approach with set operation
  - projects.create: Use lead_id parameter
  - projects.schema: Remove field_name parameter
  - search.autosearch: Keep natural_language_query and project_context only
  - ai.plan: Add context parameter as object with additionalProperties: true
- [ ] Implement pagination support in ProjectsClient.get_projects
  - Add $top/$skip query parameters
  - Update method signature to accept limit/offset
- [ ] Implement comments/links expansions in issues.get
  - Update IssuesClient.get_issue to support additional expansions
  - Ensure reliable fetching of comments, links, work_items, history, activities, time_tracking
- [ ] Clean tool descriptions to remove function-style examples; reference help:// resources
  - Remove inline "Example: tool(arg=...)" from descriptions
  - Ensure help resources have canonical JSON examples
- [ ] Update tests to reflect aligned schemas
  - Modify test_tool_calls_refactor.py for new schemas
  - Add tests for pagination and new expansions
- [ ] Update documentation (AGENTS.md, README) with strict-by-default behavior and canonical JSON examples
  - Emphasize no positional args, additionalProperties: false, exact parameter names
  - Confirm strict validation is default

### Phase 2: Remove Legacy Repair Wrappers
- [ ] Remove args/kwargs repair from mcp_wrappers.py and server._wrap_tool_function
- [ ] Simplify registration paths; ensure only validated kwargs reach tool methods
- [ ] Finalize documentation by removing legacy pattern references

## Rollout Strategy
- Default to strict server immediately
- Optionally gate with env flag MCP_STRICT=false for emergency revert (remove in Phase 2)
- Clear schema validation errors will guide users to correct usage

## Acceptance Criteria
- main.py uses StrictYouTrackMCPServer in both stdio and http modes
- HTTP endpoint rejects invalid calls with schema-derived messages
- Schemas match tool signatures and enforced behavior
- Pagination works in projects.list with limit/offset
- Comments/links expansions work reliably in issues.get
- Tests updated and passing locally
- Tool descriptions reference help:// resources for examples
- Documentation reflects strict-by-default behavior

## Timeline
- Phase 1: 2-3 days (code + schemas + tests + docs + new features)
- Phase 2: 1 day after bake period

## Owner
core-maintainers

## Reviewers
- architecture
- tooling
- docs
- QA