---
tool: awk
kind: utility
tool_min_version: "4.0"
tool_version_check: "awk --version"
recommended_output_format: txt
---

# awk - Text Processing Tool

## Overview

awk is a powerful pattern-scanning and data extraction language. It's excellent for quick text transformations and data extraction without the overhead of starting Python or other interpreters.

**IMPORTANT**: awk is designed for text files. It processes files line by line and is ideal for structured text data.

## Installation

- **macOS**: Built-in (or `brew install gawk` for GNU awk)
- **Ubuntu/Debian**: Built-in (or `apt-get install gawk`)
- **Windows**: Available through WSL or Cygwin

## Capabilities

- Pattern matching and text extraction
- Field and record processing
- Mathematical operations
- String manipulation
- Report generation

## Common Usage Patterns

### Extract specific columns

```bash
awk '{print $1, $3}' {{INPUT_FILE}} > {{OUTPUT_FILE}}
```

- Prints first and third columns (space-separated)

### Filter lines by pattern

```bash
awk '/pattern/ {print}' {{INPUT_FILE}} > {{OUTPUT_FILE}}
```

- Prints lines containing "pattern"

### Process CSV files

```bash
awk -F',' '{print $2}' {{INPUT_FILE}} > {{OUTPUT_FILE}}
```

- `-F','`: Use comma as field separator

### Calculate column sum

```bash
awk '{sum += $1} END {print sum}' {{INPUT_FILE}} > {{OUTPUT_FILE}}
```

- Sums values in first column

### Add line numbers

```bash
awk '{print NR ": " $0}' {{INPUT_FILE}} > {{OUTPUT_FILE}}
```

- `NR`: Current line number

### Replace text patterns

```bash
awk '{gsub(/old/, "new"); print}' {{INPUT_FILE}} > {{OUTPUT_FILE}}
```

- Replaces "old" with "new" globally

## Output Formats

- Plain text
- Structured data (columns, CSV)
- Custom formatted output

## Security Considerations

- ✅ Local processing only
- ✅ No network access required
- ✅ Safe for sensitive documents
- ✅ No data transmission to external services

## Performance

- **Speed**: Very fast for text processing
- **Memory**: Efficient memory usage
- **File Size**: Handles large text files well

## Best Practices

1. Use single quotes to protect awk scripts from shell
2. Specify field separator with `-F` for structured data
3. Use `BEGIN` and `END` blocks for initialization/cleanup
4. Test patterns on small samples first
5. Combine with other Unix tools for complex workflows
