---
tool: iconv
kind: utility
tool_min_version: "2.0"
tool_version_check: "iconv --version"
recommended_output_format: txt
---

# iconv - Character Encoding Converter

## Overview

iconv converts text from one character encoding to another. It's essential for fixing encoding issues before OCR processing or when dealing with files from different systems.

**IMPORTANT**: iconv only processes text files. It cannot convert binary files or fix encoding issues in images.

## Installation

- **macOS**: Built-in
- **Ubuntu/Debian**: Built-in (part of glibc)
- **Windows**: Available through WSL or Cygwin

## Capabilities

- Convert between character encodings
- Fix encoding issues
- Detect encoding problems
- Handle various text formats
- Batch processing support

## Common Usage Patterns

### Convert encoding

```bash
iconv -f ISO-8859-1 -t UTF-8 {{INPUT_FILE}} > {{OUTPUT_FILE}}
```

- `-f`: From encoding
- `-t`: To encoding

### Auto-detect and convert to UTF-8

```bash
iconv -f $(file -bi {{INPUT_FILE}} | cut -d= -f2) -t UTF-8 {{INPUT_FILE}} > {{OUTPUT_FILE}}
```

- Uses `file` command to detect encoding

### List available encodings

```bash
iconv -l
```

- Shows all supported character encodings

### Convert with error handling

```bash
iconv -f ISO-8859-1 -t UTF-8//IGNORE {{INPUT_FILE}} > {{OUTPUT_FILE}}
```

- `//IGNORE`: Skip invalid characters

### Convert with transliteration

```bash
iconv -f ISO-8859-1 -t UTF-8//TRANSLIT {{INPUT_FILE}} > {{OUTPUT_FILE}}
```

- `//TRANSLIT`: Transliterate unsupported characters

## Output Formats

- UTF-8 (recommended for modern systems)
- ASCII
- ISO-8859-1 (Latin-1)
- Windows-1252
- And many others

## Security Considerations

- ✅ Local processing only
- ✅ No network access required
- ✅ Safe for sensitive documents
- ✅ No data transmission to external services

## Performance

- **Speed**: Very fast for text conversion
- **Memory**: Efficient streaming processing
- **File Size**: Handles large text files efficiently

## Best Practices

1. Always convert to UTF-8 for modern compatibility
2. Use `//IGNORE` or `//TRANSLIT` for problematic files
3. Check file encoding with `file -bi` before conversion
4. Test conversion on small samples first
5. Use before OCR processing to ensure clean text input
