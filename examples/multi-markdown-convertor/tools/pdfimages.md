---
tool: pdfimages
kind: pdf-extractor
tool_min_version: "0.86"
tool_version_check: "pdfimages -v 2>&1 | head -1"
recommended_output_format: png
installation:
  macos: "brew install poppler"
  ubuntu: "apt-get install poppler-utils"
  windows: "Download from https://blog.alivate.com.au/poppler-windows/"
---

# pdfimages - PDF Image Extractor

## Overview

pdfimages is part of the Poppler PDF utilities that extracts images from PDF files in their original format without quality loss.

**IMPORTANT**: pdfimages only extracts embedded images. For text extraction, use pdftotext. For full page rendering, use ImageMagick convert.

## Installation

- **macOS**: `brew install poppler`
- **Ubuntu/Debian**: `apt-get install poppler-utils`
- **Windows**: Download Poppler utilities

## Capabilities

- Extract images in original format (JPEG, PNG, etc.)
- Lossless image extraction
- Batch extraction from multiple pages
- Image metadata preservation
- Various output formats

## Common Usage Patterns

### Extract all images (Recommended)

```bash
pdfimages {{INPUT_FILE}} $TEMP_DIR/image
```

- Extracts all images with prefix "image" (image-000.jpg, image-001.png, etc.)
- **Preserves original formats** (JPEG stays JPEG, etc.) for highest fidelity

### Extract images as PNG

```bash
pdfimages -png {{INPUT_FILE}} $TEMP_DIR/image
```

- `-png`: Convert all images to PNG format
- **Note**: This will transcode images (JPEGs to PNG) with potential size increase

### Extract from specific pages

```bash
pdfimages -f 1 -l 5 {{INPUT_FILE}} $TEMP_DIR/image
```

- `-f 1`: Start from page 1
- `-l 5`: End at page 5

### List images without extracting (Recommended first step)

```bash
pdfimages -list {{INPUT_FILE}}
```

- `-list`: Show image information without extraction
- **Use first to list images and their types** without extracting for conditional logic

### Extract JPEG images in original format

```bash
pdfimages -j {{INPUT_FILE}} $TEMP_DIR/image
```

- `-j`: Extract JPEG images in original format

## Canonical command templates (planner-safe)

| id                | description                          | template |
|-------------------|--------------------------------------|----------|
| `pdf_list_images` | List images without extracting       | `pdfimages -list "{{INPUT_FILE}}"` |
| `pdf_extract_orig`| Extract images in original format    | `pdfimages "{{INPUT_FILE}}" "$TEMP_DIR/image"` |
| `pdf_extract_png` | Extract all images as PNG            | `pdfimages -png "{{INPUT_FILE}}" "$TEMP_DIR/image"` |
| `pdf_extract_jpeg`| Extract JPEG images only             | `pdfimages -j "{{INPUT_FILE}}" "$TEMP_DIR/image"` |
| `pdf_extract_pages`| Extract from specific page range    | `pdfimages -f 1 -l 10 "{{INPUT_FILE}}" "$TEMP_DIR/image"` |

**Planner guidance**

- **Use pdfimages alongside text extraction** to retrieve all embedded images from a PDF without loss of quality.
- **Specify an output filename prefix in the temp directory**, e.g. $TEMP_DIR/image – the tool will append page and image numbers and appropriate extensions automatically (e.g. image-000.png, image-001.jpg).
- **This preserves original formats** (JPEG stays JPEG, etc.) for fidelity. If consistent format is needed (for example, all PNG), use the -png flag, though note this will transcode images (JPEGs to PNG) with potential size increase.
- **It's often best to extract in original format for highest fidelity**.
- **Use pdfimages -list {{INPUT_FILE}} first** to list images and their types without extracting – this can inform the pipeline whether images are present and their count, which is useful for conditional logic (e.g. skipping OCR on text-only PDFs or planning image OCR if the images might contain text).
- **When integrating into Markdown, ensure the pipeline captures the generated image filenames** and inserts appropriate markdown image tags (e.g. ![](image-001.png)).

## Output Formats

- **Original format** (JPEG, PNG, TIFF, etc.) - **Recommended for highest fidelity**
- PNG (with `-png` option)
- PPM (with `-ppm` option)
- JPEG (with `-j` option)

## Security Considerations

- ✅ Local processing only
- ✅ No network access required
- ✅ Safe for sensitive documents
- ✅ Preserves original image quality
- ✅ No data transmission to external services

## Performance

- **Speed**: Fast image extraction
- **Memory**: Efficient memory usage
- **File Size**: Handles large PDFs with many images

## Integration Notes

- **Conditional extraction**: Use `-list` first to determine if images are present before extraction
- **Markdown integration**: Pipeline must capture generated filenames and create appropriate markdown image links
- **Format preservation**: Extract in original format unless specific format consistency is required
- **Fallback/alternatives**: pdfimages only grabs existing images; it won't create an image of text. For full-page capture of PDFs (e.g. for scanned pages), use ImageMagick instead

## Best Practices

1. **Use `-list` first** to see what images are available and their count for conditional logic
2. **Specify output directory** to organize extracted images in temp space
3. **Extract in original format** for highest fidelity unless format consistency is needed
4. **Extract page ranges** for large documents to manage processing
5. **Combine with text extraction** (pdftotext) for complete document processing
6. **Plan for Markdown integration** - capture filenames for image link generation

## When to Use vs When NOT to Use

### When to Use

- **Extracting embedded images** from PDFs without quality loss
- When you need images in their original format and quality
- **Alongside text extraction** to get complete document content
- When you need to know image count/types before processing

### When NOT to Use

- **For full-page capture of PDFs** (use ImageMagick convert instead)
- **For text extraction** (use pdftotext)
- When you need to create images of text content (use rasterization tools)
- For PDFs that contain only vector graphics (pdfimages would skip these)

## Sample step emitted by planner

```bash
# id: extract_pdf_images
pdfimages -list "{{INPUT_FILE}}" > "$TEMP_DIR/image_list.txt"
if [ -s "$TEMP_DIR/image_list.txt" ]; then
    pdfimages "{{INPUT_FILE}}" "$TEMP_DIR/image"
    # follow with: generate markdown image links for extracted files
fi
```

**Note**: pdfimages only grabs existing embedded images; for full-page capture use ImageMagick convert.
