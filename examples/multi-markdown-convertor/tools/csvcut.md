---
tool: csvcut
kind: utility
tool_min_version: "1.0"
tool_version_check: "csvcut --version"
recommended_output_format: csv
---

# csvcut - CSV Column Extractor

## Overview

csvcut is part of the csvkit suite of tools for working with CSV data. It allows you to extract specific columns from CSV files by name or position.

**IMPORTANT**: csvcut is designed for CSV/TSV files. For other tabular formats, convert to CSV first.

## Installation

- **macOS**: `brew install csvkit`
- **Ubuntu/Debian**: `apt-get install csvkit`
- **Windows**: `pip install csvkit`

## Capabilities

- Extract specific columns by name or number
- Reorder columns
- Exclude unwanted columns
- Handle various CSV dialects
- Unicode support

## Common Usage Patterns

### Extract columns by name

```bash
csvcut -c "name,email,phone" {{INPUT_FILE}} > {{OUTPUT_FILE}}
```

- `-c`: Specify columns by name

### Extract columns by position

```bash
csvcut -c 1,3,5 {{INPUT_FILE}} > {{OUTPUT_FILE}}
```

- Extract columns 1, 3, and 5

### Exclude specific columns

```bash
csvcut -C "unwanted_column" {{INPUT_FILE}} > {{OUTPUT_FILE}}
```

- `-C`: Exclude specified columns

### List available columns

```bash
csvcut -n {{INPUT_FILE}}
```

- `-n`: Show column names and numbers

### Extract range of columns

```bash
csvcut -c 2-5 {{INPUT_FILE}} > {{OUTPUT_FILE}}
```

- Extract columns 2 through 5

## Output Formats

- CSV (default)
- Custom delimiter output with `-d` option

## Security Considerations

- ✅ Local processing only
- ✅ No network access required
- ✅ Safe for sensitive documents
- ✅ No data transmission to external services

## Performance

- **Speed**: Fast for CSV processing
- **Memory**: Efficient streaming processing
- **File Size**: Handles large CSV files well

## Best Practices

1. Use `-n` to inspect column structure first
2. Quote column names with spaces or special characters
3. Use column numbers for consistent results
4. Combine with other csvkit tools for complex workflows
5. Specify encoding with `--encoding` for non-UTF8 files
