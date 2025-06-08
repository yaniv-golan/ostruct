---
tool: xmllint
kind: xml-validator
tool_min_version: "2.9"
tool_version_check: "xmllint --version"
recommended_output_format: xml
---

# XMLLint XML Validator

## Overview

XMLLint is a command-line XML validation tool that can validate XML syntax, check against DTDs and XML Schemas, and format XML documents.

**IMPORTANT**: XMLLint is designed exclusively for XML files. It cannot process HTML, PDF, Word documents, or other non-XML formats.

## Installation

- **macOS**: `brew install libxml2` (includes xmllint)
- **Ubuntu/Debian**: `apt-get install libxml2-utils`
- **Windows**: Available through various XML tool packages

## Capabilities

- XML syntax validation
- DTD validation
- XML Schema (XSD) validation
- XML formatting and pretty-printing
- XPath queries

## Common Usage Patterns

### Basic XML Validation

```bash
xmllint --noout {{INPUT_FILE}}
```

- `--noout`: Only validate, don't output content

### Validate with DTD

```bash
xmllint --valid --noout {{INPUT_FILE}}
```

- `--valid`: Validate against DTD

### Validate with XML Schema

```bash
xmllint --schema schema.xsd --noout {{INPUT_FILE}}
```

- `--schema`: Validate against XSD schema

### Format XML Output

```bash
xmllint --format {{INPUT_FILE}} -o {{OUTPUT_FILE}}
```

- `--format`: Pretty-print XML with proper indentation

## Output Formats

- Validation results (stderr)
- Formatted XML (stdout or file)
- Exit codes (0 = valid, non-zero = invalid)

## Security Considerations

- ✅ Local processing only
- ✅ No network access required
- ✅ Safe for sensitive documents
- ⚠️ Can resolve external entities - use `--nonet` for security

## Performance

- **Speed**: Very fast for XML validation
- **Memory**: Low memory usage
- **File Size**: Handles large XML files efficiently

## Best Practices

1. Use `--noout` for validation-only operations
2. Use `--nonet` to prevent external entity resolution
3. Validate against schemas when available
4. Use `--format` for readable XML output
