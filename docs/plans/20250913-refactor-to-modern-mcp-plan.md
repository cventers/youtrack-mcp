# Plan: Refactor to Modern MCP Server - 2025-09-13

## Objectives
- Remove all legacy args/kwargs compatibility shims
- Consolidate to ONE FastMCP server with typed tools and resources
- Publish real input schemas via FastMCP (from type hints / Pydantic)
- Make tools return structured results; no pre-json-dumping
- Update tests to call tools the canonical MCP way

## Constraints
- Do not introduce new features; this is a behavior-preserving refactor where possible
- All MCP tool calls must use standard arguments (no "args"/"kwargs" wrappers)
- The input schema must describe only the tool arguments, not an envelope
- Keep module names / public tool names stable (e.g., "search.query", "search.autosearch"), unless a name is actually unsafe
- Prefer Pydantic models for complex inputs; otherwise, use explicit typed parameters
- Keep resource URIs and names stable

## Tasks

### Phase 1: Delete Compatibility Layers
- [ ] Remove youtrack_mcp/mcp_wrappers.py and youtrack_mcp/api/mcp_wrappers.py
- [ ] Remove all imports of these modules from tools/ and elsewhere
- [ ] In youtrack_mcp/tools/*, change any wrapped exports to plain typed functions with explicit parameters

### Phase 2: Replace Server Implementations with FastMCP
- [ ] Create youtrack_mcp/server_fastmcp.py that:
  - constructs FastMCP("youtrack")
  - registers tools using @mcp.tool() with typed signatures:
    - search_query(query: str, limit: int = 50) -> list[dict]
    - search_autosearch(data: AutoSearchInput) -> list[dict], where AutoSearchInput is a Pydantic BaseModel with fields: natural_language_query: str; project_context: str | None = None; limit: int = 50
    - projects_list(fields: str | None = None) -> list[dict]
    - issues_get(issue_id: str, include: list[str] | None = None) -> dict
    - issues_create(project: str, summary: str, description: str | None = None, **any other minimal required fields**) -> dict
  - registers resources using @mcp.resource(...) (migrating any existing resource handlers)
  - runs mcp.run_stdio() when executed as __main__
- [ ] Remove youtrack_mcp/server.py and youtrack_mcp/strict_server.py (or leave stubs that import and run server_fastmcp.py for backwards import compatibility)

### Phase 3: Fix Schemas
- [ ] Delete youtrack_mcp/schemas.py or rewrite it to ONLY define argument-level JSON Schemas (no "tool_name"/"arguments" envelope)
- [ ] If any tool needs bespoke constraints not expressed via type hints, attach a dict input_schema to the tool registration using the low-level API; otherwise rely on auto-generated schemas from FastMCP

### Phase 4: Update API Clients
- [ ] In youtrack_mcp/api/* clients, ensure methods consume explicit parameters (no kwargs parsing)
- [ ] Remove any string-to-dict guessing of parameters

### Phase 5: Update Tests
- [ ] Replace any tests that pass {"kwargs": "..."} with direct arguments that match the typed signatures
- [ ] Add a test that exercises listing tools and verifies that each tool has a non-empty inputSchema with expected properties
- [ ] Add a test that calls tools via the canonical shape: tools/call with { "name": "<tool>", "arguments": { ... } } and verifies success

### Phase 6: Cleanups & DX
- [ ] Remove any "fast handshake" stdout hacks; rely on the SDK's stdio transport
- [ ] Ensure tool functions return dict/list primitives; do not json.dumps tool results

## Acceptance Criteria
- [ ] Grep for "process_parameters(", "async_wrapper", "sync_wrapper", or '"kwargs"' returns no call sites in the server/tool path
- [ ] tools/list returns tools with inputSchema describing argument properties (no "tool_name" field)
- [ ] Calling search.autosearch with {"natural_language_query": "...", "project_context": "OPS"} works. Calling search.query with {"query": "...", "limit": 10} works. Calling projects.list with {} or {"fields": "id,name,shortName"} works
- [ ] Unit tests pass; any legacy-shape tests are removed or updated
- [ ] The server runs under stdio mode and responds to MCP Inspector correctly

## Notes
- Prefer Pydantic models for nested/complex payloads
- Expose optional output schemas only if you annotate return types with Pydantic models; otherwise let FastMCP return structuredContent automatically