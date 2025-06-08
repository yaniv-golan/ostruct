---
tool: sed
kind: utility
tool_min_version: "4.0"
tool_version_check: "echo 'BSD sed' || sed --version 2>/dev/null"
recommended_output_format: txt
---

# sed - Stream Editor

## Overview

sed is a stream editor for filtering and transforming text. It's perfect for quick text substitutions and transformations without the overhead of starting Python or other interpreters.

**IMPORTANT**: sed processes text files line by line. It's ideal for simple text transformations and pattern replacements.

## Installation

- **macOS**: Built-in (or `brew install gnu-sed` for GNU sed)
- **Ubuntu/Debian**: Built-in
- **Windows**: Available through WSL or Cygwin

## Capabilities

- Text substitution and replacement
- Line deletion and insertion
- Pattern matching
- Regular expression support
- In-place file editing

## Common Usage Patterns

### Simple text replacement

```bash
sed 's/old/new/g' {{INPUT_FILE}} > {{OUTPUT_FILE}}
```

- `s/old/new/g`: Replace "old" with "new" globally

### Replace in place

```bash
sed -i 's/old/new/g' {{INPUT_FILE}}
```

- `-i`: Edit file in place

### Delete lines matching pattern

```bash
sed '/pattern/d' {{INPUT_FILE}} > {{OUTPUT_FILE}}
```

- `/pattern/d`: Delete lines containing "pattern"

### Extract lines between patterns

```bash
sed -n '/start/,/end/p' {{INPUT_FILE}} > {{OUTPUT_FILE}}
```

- `-n`: Suppress default output
- `/start/,/end/p`: Print lines between "start" and "end"

### Add text at beginning of lines

```bash
sed 's/^/prefix: /' {{INPUT_FILE}} > {{OUTPUT_FILE}}
```

- `^`: Beginning of line anchor

### Remove empty lines

```bash
sed '/^$/d' {{INPUT_FILE}} > {{OUTPUT_FILE}}
```

- `^$`: Empty line pattern

## Output Formats

- Plain text
- Modified text files
- Filtered content

## Security Considerations

- ✅ Local processing only
- ✅ No network access required
- ✅ Safe for sensitive documents
- ✅ No data transmission to external services

## Performance

- **Speed**: Very fast for text processing
- **Memory**: Efficient streaming processing
- **File Size**: Handles large text files efficiently

## Best Practices

1. Use single quotes to protect regex from shell interpretation
2. Test substitutions on small samples first
3. Use `-i.bak` to create backup when editing in place
4. Escape special characters in patterns
5. Combine with other Unix tools for complex workflows
