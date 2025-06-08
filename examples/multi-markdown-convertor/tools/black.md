---
tool: black
kind: formatter
tool_min_version: "22.0"
tool_version_check: "black --version"
recommended_output_format: py
---

# Black - Python Code Formatter

## Overview

Black is the uncompromising Python code formatter. It reformats entire files in place and is deterministic - it will always produce the same output for the same input.

**IMPORTANT**: Black is designed exclusively for Python code files (.py, .pyi). It cannot format other file types.

## Installation

- **macOS**: `brew install black` or `pip install black`
- **Ubuntu/Debian**: `pip install black`
- **Windows**: `pip install black`

## Capabilities

- Automatic Python code formatting
- PEP 8 compliance
- Deterministic output
- Fast formatting
- Integration with editors and CI/CD

## Common Usage Patterns

### Format file in place

```bash
black {{INPUT_FILE}}
```

- Formats Python file in place

### Check if file needs formatting

```bash
black --check {{INPUT_FILE}}
```

- `--check`: Exit with error if file needs formatting

### Show diff without changing file

```bash
black --diff {{INPUT_FILE}}
```

- `--diff`: Show what changes would be made

### Format to stdout

```bash
black --code "$(cat {{INPUT_FILE}})"
```

- Format code and output to stdout

### Format with specific line length

```bash
black --line-length 88 {{INPUT_FILE}}
```

- Set maximum line length (default is 88)

## Output Formats

- Python source code (.py)
- Python stub files (.pyi)

## Security Considerations

- ✅ Local processing only
- ✅ No network access required
- ✅ Safe for sensitive documents
- ✅ Only reformats, doesn't execute code
- ✅ No data transmission to external services

## Performance

- **Speed**: Very fast Python formatting
- **Memory**: Low memory usage
- **File Size**: Handles large Python files efficiently

## Best Practices

1. Use `--check` in CI/CD pipelines
2. Configure `pyproject.toml` for project settings
3. Use `--diff` to preview changes
4. Integrate with editor for automatic formatting
5. Run on entire codebase for consistency
