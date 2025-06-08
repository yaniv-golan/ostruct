---
tool: jq
kind: utility
tool_min_version: "1.6"
tool_version_check: "jq --version"
recommended_output_format: json
---

# jq - JSON Processor

## Overview

jq is a lightweight and flexible command-line JSON processor. It's like sed for JSON data - you can use it to slice, filter, map and transform structured data.

**IMPORTANT**: jq only processes JSON data. For other data formats, convert to JSON first or use appropriate tools.

## Installation

- **macOS**: `brew install jq`
- **Ubuntu/Debian**: `apt-get install jq`
- **Windows**: Download from <https://stedolan.github.io/jq/>

## Capabilities

- JSON parsing and validation
- Data filtering and transformation
- Array and object manipulation
- Complex queries and aggregations
- Pretty-printing JSON

## Common Usage Patterns

### Pretty-print JSON

```bash
jq '.' {{INPUT_FILE}} > {{OUTPUT_FILE}}
```

- `.`: Identity filter (pretty-prints input)

### Extract specific fields

```bash
jq '.field_name' {{INPUT_FILE}} > {{OUTPUT_FILE}}
```

- Extracts a specific field from JSON objects

### Filter arrays

```bash
jq '.[] | select(.status == "active")' {{INPUT_FILE}} > {{OUTPUT_FILE}}
```

- Filters array elements based on conditions

### Transform data structure

```bash
jq 'map({name: .name, id: .id})' {{INPUT_FILE}} > {{OUTPUT_FILE}}
```

- Transforms array elements to new structure

### Extract table data for LLMs

```bash
jq '.data[] | [.column1, .column2, .column3] | @csv' {{INPUT_FILE}} > {{OUTPUT_FILE}}
```

- Converts JSON table data to CSV format for LLM processing

## Output Formats

- JSON (default)
- CSV (@csv formatter)
- TSV (@tsv formatter)
- Raw text (@text formatter)
- HTML (@html formatter)

## Security Considerations

- ✅ Local processing only
- ✅ No network access required
- ✅ Safe for sensitive documents
- ✅ No data transmission to external services

## Performance

- **Speed**: Very fast for JSON processing
- **Memory**: Efficient memory usage
- **File Size**: Handles large JSON files well

## Best Practices

1. Use `.` for simple pretty-printing
2. Quote complex filters to avoid shell interpretation
3. Use `@csv` or `@tsv` for tabular data extraction
4. Test filters on small samples first
5. Use `--raw-output` for plain text extraction
