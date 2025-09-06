# YouTrack Query Language (YQL) Reference

**Sources**: 
- https://www.jetbrains.com/help/youtrack/devportal/api-query-syntax.html
- https://www.jetbrains.com/help/youtrack/server/search-and-command-attributes.html  
**Extracted**: 2025-06-13

## Basic Syntax

### Attribute-Value Pairs
The foundation of YouTrack queries is the attribute-value syntax:
```
attribute: value
```

### Special Characters and Symbols

| Symbol | Purpose | Example |
|--------|---------|---------|
| `:` | Separates attribute from value | `project: MyProject` |
| `#` | Indicates single value without attribute | `#Unresolved` |
| `,` | Separates multiple values | `state: Open, In Progress` |
| `..` | Defines value ranges | `created: 2025-01-01 .. 2025-01-31` |
| `*` | Wildcard character | `summary: bug*` |
| `{ }` | Encloses values with spaces | `project: {Sample Project}` |
| `-` | Excludes values | `-assignee: john.doe` |

## Logical Operators

### AND (Default)
```
project: MyProject assignee: john.doe
project: MyProject AND assignee: john.doe
```

### OR
```
state: Open OR state: {In Progress}
```

### Parentheses for Grouping
```
(state: Open OR state: {In Progress}) AND assignee: john.doe
```

## Date and Time Formats

### Absolute Dates
```
YYYY-MM-DD
created: 2025-06-13
updated: 2025-01-01 .. 2025-01-31
```

### Relative Date Parameters
```
{Today}
{Yesterday} 
{Last week}
{This week}
{Last month}
{This month}
```

### Custom Date Ranges
```
created: {minus 7d} .. Today
updated: {minus 1w} .. *
created: * .. {plus 1d}
```

### Time Units
- `d` - days
- `w` - weeks  
- `m` - months
- `y` - years

## Common Attributes

### Project and Issue Identification
```
project: ProjectKey
id: PROJECT-123
summary: "bug report"
description: "database error"
```

### User Attributes
```
assignee: john.doe
reporter: jane.smith
for: john.doe              # alias for assignee
```

### Status and Priority
```
state: Open
state: {In Progress}
priority: Critical
type: Bug
```

### Date Attributes
```
created: 2025-06-13
updated: {Last week} .. *
resolved: {minus 30d} .. *
```

### Custom Fields
```
{Custom Field Name}: value
{Priority}: High
{Due Date}: 2025-06-20
```

## Advanced Query Examples

### Complex User and Status Filter
```
for: john.doe #Unresolved summary: bug
```

### Multi-Project Search
```
project: ProjectA OR project: ProjectB
```

### Date Range with Exclusions
```
created: {minus 30d} .. * -state: Resolved
```

### Tag-Based Search
```
tag: {Next build} AND tag: {to be tested}
```

### Custom Field Combinations
```
{Priority}: High AND {Component}: Backend AND state: Open
```

## API Query Usage

### URL Encoding Requirements
When using queries in API requests, HTML symbols must be escaped for URIs:
- Spaces: `%20` or `+`
- Colons: `%3A`
- Curly braces: `%7B` and `%7D`

### API Query Examples
```
GET /api/issues?query=project%3A%20%7BSample%20Project%7D
GET /api/issues?query=for%3A%20john.doe%20%23Unresolved
```

## Best Practices

### 1. Use Specific Attributes
```
# Good
project: MyProject state: Open assignee: john.doe

# Less specific  
john.doe Open MyProject
```

### 2. Quote Values with Spaces
```
project: {My Project Name}
summary: {bug in login system}
```

### 3. Combine Filters Efficiently
```
# Efficient - narrow first
project: MyProject state: Open created: {minus 7d} .. *

# Less efficient - broad terms first
created: {minus 7d} .. * project: MyProject state: Open
```

### 4. Use Wildcards Sparingly
```
# Good for specific patterns
summary: login*

# Avoid overly broad wildcards
summary: *bug*
```

## Error Prevention

### Common Mistakes
1. **Missing quotes for multi-word values**: Use `{Multi Word Value}`
2. **Wrong date format**: Use `YYYY-MM-DD` format
3. **Case sensitivity**: Project names and custom fields are case-sensitive
4. **Invalid operators**: Use `:` not `=` for attribute-value pairs

### Validation Tips
- Test queries in YouTrack UI before using in API
- Check field names in project settings
- Verify date formats and ranges
- Use URL encoding for special characters in API calls