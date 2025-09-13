# Advanced Search Features

The YouTrack MCP server includes a sophisticated advanced search engine that provides intelligent query building, result caching, performance analytics, and search optimization capabilities.

## Overview

The advanced search system consists of several components:

- **Intelligent Search**: Natural language-like search with smart query building
- **Query Builder**: Structured search with complex conditions and operators
- **Result Caching**: In-memory caching for improved performance
- **Search Analytics**: Performance monitoring and usage statistics
- **Query Suggestions**: Auto-completion and query recommendations

## Search Tools

### 1. Intelligent Search

The `intelligent_search` tool provides a user-friendly interface for complex searches:

```python
# Example: Find critical bugs assigned to me, created in the last week
result = await intelligent_search(
    query_text="critical bug",
    assignee="me",
    priority="Critical",
    created_after="-7d",
    sort_by="created",
    sort_order="desc",
    limit=25
)
```

**Parameters:**
- `query_text`: Free text search across summary and description
- `project`: Project name or short name
- `assignee`: Assignee login ('unassigned' for unassigned issues)
- `state`: Issue state (e.g., 'Open', 'Fixed', 'Verified')
- `priority`: Issue priority (e.g., 'Critical', 'High', 'Normal', 'Low')
- `created_after`: Date filter with relative dates (`-7d`, `-1w`, `-1m`)
- `created_before`: Created before date (YYYY-MM-DD)
- `updated_after`: Updated after date with relative dates
- `updated_before`: Updated before date (YYYY-MM-DD)
- `sort_by`: Sort field (created, updated, priority, summary)
- `sort_order`: Sort direction ('asc' or 'desc')
- `limit`: Maximum results (1-1000)
- `offset`: Pagination offset
- `include_resolved`: Include resolved/closed issues
- `include_archived`: Include issues from archived projects

**Response:**
```json
{
  "issues": [...],
  "total_count": 42,
  "execution_time_ms": 150,
  "query_used": "project: TEST and assignee: me and Priority: Critical",
  "cache_hit": false,
  "suggested_queries": [
    "project: TEST and assignee: me and Priority: Critical State: Open",
    "project: TEST and assignee: me and Priority: Critical created: -7d .. *"
  ],
  "facets": {
    "project": {"TEST": 25, "PROJ": 17},
    "assignee": {"user1": 30, "user2": 12}
  },
  "pagination": {
    "limit": 50,
    "offset": 0,
    "has_more": false
  }
}
```

### 2. Query Builder Search

The `search_by_query_builder` tool allows precise control over search conditions:

```python
# Example: Complex search with multiple conditions
conditions = [
    {"field": "project", "operator": ":", "value": "TEST"},
    {"field": "assignee", "operator": "!:", "value": "Unassigned"},
    {"field": "Priority", "operator": "in", "value": ["High", "Critical"]},
    {"field": "created", "operator": ">", "value": "2024-01-01"}
]

result = await search_by_query_builder(
    conditions=conditions,
    sort_field="updated",
    sort_order="desc",
    limit=100
)
```

**Supported Operators:**
- `:` - Equals
- `!:` - Not equals
- `~` - Contains
- `!~` - Does not contain
- `>` - Greater than
- `<` - Less than
- `>=` - Greater than or equal
- `<=` - Less than or equal
- `in` - In list of values
- `not in` - Not in list of values
- `has` - Has field/value
- `!has` - Does not have field/value

### 3. Search Suggestions

Get intelligent query suggestions as you type:

```python
# Get suggestions for partial query
suggestions = await search_suggestions("proj", limit=5)
# Returns: ["project:", "project: TEST", "project: SAMPLE"]
```

### 4. Search Analytics

Monitor search performance and usage patterns:

```python
analytics = await search_analytics()
```

**Response:**
```json
{
  "analytics": {
    "total_searches": 1250,
    "unique_query_patterns": 45,
    "average_execution_time": 0.125,
    "max_execution_time": 2.1,
    "popular_queries": {
      "project: test": 230,
      "assignee: me": 180,
      "state: open": 150
    },
    "popular_fields": {
      "project": 890,
      "assignee": 650,
      "state": 540
    },
    "error_counts": {
      "Invalid syntax": 12,
      "Permission denied": 3
    },
    "uptime_seconds": 86400
  },
  "cache": {
    "entries": 85,
    "max_entries": 1000,
    "ttl_seconds": 300,
    "hit_rate": 0.68
  }
}
```

### 5. Cache Management

Clear the search cache to force fresh results:

```python
result = await clear_search_cache()
# Returns: {"status": "success", "message": "Search cache cleared"}
```

## Advanced Features

### Relative Date Parsing

The intelligent search supports relative date formats:

- `-7d` - 7 days ago
- `-1w` - 1 week ago
- `-1m` - 1 month ago (30 days)
- `-1y` - 1 year ago (365 days)

### Query Optimization

The search engine automatically optimizes queries:

1. **Field Selection**: Only requests necessary fields from the API
2. **Query Caching**: Caches results for frequently used queries
3. **Result Pagination**: Efficiently handles large result sets
4. **Smart Sorting**: Optimizes sort operations

### Search Caching

Results are cached in memory with configurable settings:

- **TTL (Time To Live)**: Default 5 minutes
- **LRU Eviction**: Removes least recently used entries when cache is full
- **Cache Hit Tracking**: Monitors cache effectiveness

### Performance Analytics

The system tracks comprehensive performance metrics:

- Query execution times
- Popular search patterns
- Field usage statistics
- Error rates and patterns
- Cache hit rates

## Configuration

### Environment Variables

Configure advanced search behavior:

```bash
# Cache settings
export YOUTRACK_SEARCH_CACHE_TTL=300  # 5 minutes
export YOUTRACK_SEARCH_CACHE_SIZE=1000  # Max cached queries

# Analytics settings
export YOUTRACK_SEARCH_ANALYTICS=true
export YOUTRACK_SEARCH_ANALYTICS_FILE=/var/log/search-analytics.json
```

### Programmatic Configuration

```python
from youtrack_mcp.search_advanced import AdvancedSearchEngine

# Create with custom settings
search_engine = AdvancedSearchEngine(
    client=youtrack_client,
    enable_cache=True,
    enable_analytics=True
)

# Configure cache
search_engine.cache.max_entries = 2000
search_engine.cache.ttl_seconds = 600  # 10 minutes
```

## Usage Examples

### Find Recent Issues in Multiple Projects

```python
result = await intelligent_search(
    project=None,  # Search all projects
    created_after="-3d",  # Last 3 days
    state="Open",
    sort_by="created",
    sort_order="desc",
    limit=50
)
```

### Search for Unassigned Critical Issues

```python
result = await intelligent_search(
    assignee="unassigned",
    priority="Critical",
    include_resolved=False,
    sort_by="created",
    limit=20
)
```

### Complex Multi-Condition Search

```python
conditions = [
    {"field": "project", "operator": "in", "value": ["PROJ1", "PROJ2"]},
    {"field": "assignee", "operator": "!:", "value": "Unassigned"},
    {"field": "State", "operator": ":", "value": "Open"},
    {"field": "Priority", "operator": "in", "value": ["High", "Critical"]},
    {"field": "updated", "operator": ">", "value": "2024-01-01"}
]

result = await search_by_query_builder(
    conditions=conditions,
    sort_field="priority",
    sort_order="asc",
    limit=100
)
```

### Search with Text and Filters

```python
result = await intelligent_search(
    query_text="authentication error",
    project="AUTH",
    state="Open",
    created_after="-14d",
    sort_by="updated"
)
```

## Performance Optimization

### Best Practices

1. **Use Specific Projects**: Limit searches to specific projects when possible
2. **Set Reasonable Limits**: Don't request more results than needed
3. **Use Date Ranges**: Limit searches to relevant time periods
4. **Leverage Caching**: Repeated searches will be served from cache
5. **Monitor Analytics**: Use analytics to identify slow queries

### Cache Tuning

Monitor cache performance and adjust settings:

```python
# Check cache statistics
stats = await search_analytics()
hit_rate = stats["cache"]["hit_rate"]

if hit_rate < 0.5:
    # Consider increasing cache size or TTL
    pass
```

### Query Optimization Tips

1. **Field Selection**: Exclude unnecessary fields to reduce response size
2. **Pagination**: Use offset and limit for large result sets
3. **Sorting**: Sort by indexed fields when possible
4. **Filtering**: Apply filters early in the query

## Troubleshooting

### Common Issues

#### Slow Query Performance

```python
# Check analytics for slow queries
analytics = await search_analytics()
slow_queries = [q for q, time in analytics["execution_times"] if time > 1.0]
```

**Solutions:**
- Add more specific filters
- Reduce result limit
- Use indexed fields for sorting
- Check YouTrack server performance

#### Cache Not Working

```python
# Verify cache is enabled
stats = await search_analytics()
if stats["cache"]["entries"] == 0:
    # Cache might be disabled or cleared too frequently
    pass
```

**Solutions:**
- Check cache configuration
- Increase cache TTL
- Verify sufficient memory

#### Poor Search Relevance

**Solutions:**
- Use more specific search terms
- Combine multiple conditions
- Use field-specific searches instead of text search
- Check field names and values

### Error Handling

The search engine handles various error conditions:

```python
try:
    result = await intelligent_search(query_text="test")
except Exception as e:
    # Handle search errors
    logger.error(f"Search failed: {e}")
```

Common error types:
- Invalid query syntax
- Permission denied
- API timeout
- Network errors

## API Reference

### Search Query Language

The advanced search engine supports the full YouTrack query language with enhancements:

#### Basic Syntax
```
field: value
field: "quoted value"
field: {value with spaces}
```

#### Operators
```
field: value          # equals
field: !value         # not equals
field: >value         # greater than
field: <value         # less than
field: value1, value2 # multiple values (OR)
```

#### Logical Operators
```
condition1 and condition2
condition1 or condition2
not condition
(condition1 or condition2) and condition3
```

#### Date Formats
```
created: 2024-01-01
created: 2024-01-01 .. 2024-01-31
created: -7d .. *     # last 7 days
updated: * .. -1w     # until 1 week ago
```

#### Special Values
```
assignee: Unassigned
assignee: me
assignee: {current user}
project: *            # any project
state: Unresolved
```

For complete YouTrack query language documentation, see the [YouTrack documentation](https://www.jetbrains.com/help/youtrack/standalone/search-and-command-attributes.html).