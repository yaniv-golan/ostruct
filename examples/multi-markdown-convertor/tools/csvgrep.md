---
tool: csvgrep
kind: utility
tool_min_version: "1.0"
tool_version_check: "csvgrep --version"
recommended_output_format: csv
---

# csvgrep - CSV Row Filter

## Overview

csvgrep is part of the csvkit suite that allows you to filter CSV rows based on pattern matching, similar to grep but CSV-aware.

**IMPORTANT**: csvgrep is designed for CSV/TSV files. For other tabular formats, convert to CSV first.

## Installation

- **macOS**: `brew install csvkit`
- **Ubuntu/Debian**: `apt-get install csvkit`
- **Windows**: `pip install csvkit`

## Capabilities

- Filter rows based on column values
- Regular expression matching
- Exact string matching
- Numeric comparisons
- Multiple column filtering

## Common Usage Patterns

### Filter by exact match

```bash
csvgrep -c "status" -m "active" {{INPUT_FILE}} > {{OUTPUT_FILE}}
```

- `-c`: Column name to search
- `-m`: Exact match pattern

### Filter with regex

```bash
csvgrep -c "email" -r ".*@company\.com$" {{INPUT_FILE}} > {{OUTPUT_FILE}}
```

- `-r`: Regular expression pattern

### Filter by column number

```bash
csvgrep -c 3 -m "value" {{INPUT_FILE}} > {{OUTPUT_FILE}}
```

- Use column number instead of name

### Invert match (exclude rows)

```bash
csvgrep -c "status" -m "inactive" -i {{INPUT_FILE}} > {{OUTPUT_FILE}}
```

- `-i`: Invert match (exclude matching rows)

### Filter multiple patterns

```bash
csvgrep -c "category" -m "urgent|high" -r {{INPUT_FILE}} > {{OUTPUT_FILE}}
```

- Use regex with alternation for multiple values

## Output Formats

- CSV (default)
- Custom delimiter output with `-d` option

## Security Considerations

- ✅ Local processing only
- ✅ No network access required
- ✅ Safe for sensitive documents
- ✅ No data transmission to external services

## Performance

- **Speed**: Fast for CSV filtering
- **Memory**: Efficient streaming processing
- **File Size**: Handles large CSV files well

## Best Practices

1. Use exact matches (`-m`) when possible for better performance
2. Quote patterns containing special characters
3. Use column numbers for consistent results across files
4. Combine with csvcut for column selection after filtering
5. Test regex patterns on small samples first
