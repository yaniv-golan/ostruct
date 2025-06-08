---
tool: exiftool
kind: utility
tool_min_version: "12.0"
tool_version_check: "exiftool -ver"
recommended_output_format: jpg
---

# ExifTool - Metadata Processor

## Overview

ExifTool is a platform-independent library and command-line application for reading, writing and editing meta information in a wide variety of files, including images extracted by ImageMagick.

**IMPORTANT**: ExifTool processes metadata in files. It's essential for removing PII (Personally Identifiable Information) from images before processing.

## Installation

- **macOS**: `brew install exiftool`
- **Ubuntu/Debian**: `apt-get install libimage-exiftool-perl`
- **Windows**: Download from <https://exiftool.org/>

## Capabilities

- Read metadata from images and documents
- Remove metadata for privacy
- Edit and update metadata
- Batch processing of multiple files
- Support for hundreds of file formats

## Common Usage Patterns

### Remove all metadata

```bash
exiftool -all= {{INPUT_FILE}}
```

- `-all=`: Remove all metadata tags

### Remove metadata and create clean copy

```bash
exiftool -all= -o {{OUTPUT_FILE}} {{INPUT_FILE}}
```

- `-o`: Output to new file, preserve original

### View all metadata

```bash
exiftool {{INPUT_FILE}} > {{OUTPUT_FILE}}
```

- Outputs all metadata to text file

### Remove specific PII tags

```bash
exiftool -GPS:all= -EXIF:Artist= -EXIF:Copyright= {{INPUT_FILE}}
```

- Removes GPS location, artist, and copyright info

### Batch process directory

```bash
exiftool -all= $TEMP_DIR/*.jpg
```

- Removes metadata from all JPEG files in directory

### Check for PII before processing

```bash
exiftool -GPS:all -EXIF:Artist -EXIF:Copyright {{INPUT_FILE}}
```

- Shows only potentially sensitive metadata

## Output Formats

- Same as input (metadata modified)
- Text output for metadata viewing
- JSON output with `-json` option

## Security Considerations

- ✅ Local processing only
- ✅ No network access required
- ✅ Essential for removing PII from images
- ✅ Prevents metadata leakage
- ✅ No data transmission to external services

## Performance

- **Speed**: Fast for metadata operations
- **Memory**: Low memory usage
- **File Size**: Handles large image files efficiently

## Best Practices

1. Always remove metadata before sharing extracted images
2. Use `-o` to preserve original files
3. Check for GPS and personal info before processing
4. Batch process entire directories for efficiency
5. Verify metadata removal with `-all` option
