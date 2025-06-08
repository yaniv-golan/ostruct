---
tool: prettier
kind: formatter
tool_min_version: "2.0"
tool_version_check: "prettier --version"
recommended_output_format: auto
---

# Prettier - Code Formatter

## Overview

Prettier is an opinionated code formatter that supports many languages. It enforces a consistent style by parsing code and re-printing it with its own rules.

**IMPORTANT**: Prettier is designed for code files (JavaScript, TypeScript, CSS, HTML, Markdown, etc.). It cannot format binary files or plain text documents.

## Installation

- **macOS**: `brew install prettier` or `npm install -g prettier`
- **Ubuntu/Debian**: `npm install -g prettier`
- **Windows**: `npm install -g prettier`

## Capabilities

- Format JavaScript, TypeScript, CSS, HTML
- Format JSON, YAML, Markdown
- Consistent code style enforcement
- Integration with editors and CI/CD
- Custom configuration support

## Common Usage Patterns

### Format file in place

```bash
prettier --write {{INPUT_FILE}}
```

- `--write`: Modify file in place

### Format to output file

```bash
prettier {{INPUT_FILE}} > {{OUTPUT_FILE}}
```

- Outputs formatted code to new file

### Check if file needs formatting

```bash
prettier --check {{INPUT_FILE}}
```

- `--check`: Exit with error if file needs formatting

### Format with specific parser

```bash
prettier --parser json {{INPUT_FILE}} > {{OUTPUT_FILE}}
```

- Explicitly specify file type parser

### Format multiple files

```bash
prettier --write "*.js" "*.css"
```

- Format multiple files with glob patterns

## Output Formats

- Same as input format (formatted)
- Supports: JS, TS, CSS, HTML, JSON, YAML, MD, and more

## Security Considerations

- ✅ Local processing only
- ✅ No network access required
- ✅ Safe for sensitive documents
- ✅ Only reformats, doesn't execute code
- ✅ No data transmission to external services

## Performance

- **Speed**: Fast for most code files
- **Memory**: Low memory usage
- **File Size**: Handles large code files efficiently

## Best Practices

1. Use `--check` in CI/CD pipelines
2. Configure `.prettierrc` for consistent team settings
3. Use `--write` for batch formatting
4. Specify parser for ambiguous file types
5. Integrate with editor for real-time formatting
