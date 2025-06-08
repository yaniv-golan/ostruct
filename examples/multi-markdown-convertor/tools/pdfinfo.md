---
tool: pdfinfo
kind: utility
tool_min_version: "0.86"
tool_version_check: "pdfinfo -v"
recommended_output_format: txt
---

# pdfinfo - PDF Information Extractor

## Overview

pdfinfo is part of the Poppler PDF utilities that extracts metadata and structural information from PDF files without processing the content.

**IMPORTANT**: pdfinfo only extracts metadata. For text extraction, use pdftotext. For image extraction, use pdfimages.

## Installation

- **macOS**: `brew install poppler`
- **Ubuntu/Debian**: `apt-get install poppler-utils`
- **Windows**: Download Poppler utilities

## Capabilities

- Extract PDF metadata (title, author, creation date)
- Get page count and dimensions
- Check PDF version and encryption status
- Determine file size and optimization
- Identify form fields and annotations

## Common Usage Patterns

### Basic PDF information

```bash
pdfinfo {{INPUT_FILE}} > {{OUTPUT_FILE}}
```

- Extracts all basic metadata and structure info

### Get page count only

```bash
pdfinfo {{INPUT_FILE}} | grep "Pages:" | awk '{print $2}' > {{OUTPUT_FILE}}
```

- Extracts just the page count for processing decisions

### Check encryption status

```bash
pdfinfo {{INPUT_FILE}} | grep "Encrypted:"
```

- Determines if PDF is password-protected

### Get page dimensions

```bash
pdfinfo {{INPUT_FILE}} | grep "Page size:"
```

- Extracts page dimensions for layout analysis

### Extract creation metadata

```bash
pdfinfo {{INPUT_FILE}} | grep -E "(Title|Author|Creator|Producer):"
```

- Gets document creation metadata

## Output Formats

- Plain text metadata
- Structured key-value pairs
- Shell-parseable format

## Security Considerations

- ✅ Local processing only
- ✅ No network access required
- ✅ Safe for sensitive documents
- ✅ Does not extract actual content
- ✅ No data transmission to external services

## Performance

- **Speed**: Very fast metadata extraction
- **Memory**: Minimal memory usage
- **File Size**: Works efficiently with any PDF size

## Best Practices

1. Use for quick page count checks before processing
2. Check encryption status before attempting text extraction
3. Parse output with grep/awk for specific values
4. Combine with other poppler tools for complete analysis
5. Use to determine optimal processing strategy for large PDFs
