---
tool: pdftotext
kind: pdf-extractor
tool_min_version: "4.0"
tool_version_check: "pdftotext -v 2>&1 | head -1"
recommended_output_format: text
installation:
  macos: "brew install poppler"
  ubuntu: "apt-get install poppler-utils"
  windows: "Download from https://blog.alivate.com.au/poppler-windows/"
---

# PDFtoText - PDF Text Extractor

## Overview

PDFtoText is a command-line utility for extracting text from PDF files. It's part of the Poppler PDF utilities and excels at extracting text from text-based PDFs.

**IMPORTANT**: PDFtoText only works with text-based PDFs. For scanned PDFs or image-based documents, use OCR tools like Tesseract instead.

## Installation

- **macOS**: `brew install poppler`
- **Ubuntu/Debian**: `apt-get install poppler-utils`
- **Windows**: Download Poppler utilities

## Capabilities

- Fast text extraction from PDF files
- Layout preservation options
- Page range selection
- Encoding specification
- Raw text or formatted output

## Common Usage Patterns

### Basic Text Extraction

```bash
pdftotext {{INPUT_FILE}} {{OUTPUT_FILE}}
```

- Extracts all text to output file with text reflow

### Extract with Layout Preservation

```bash
pdftotext -layout {{INPUT_FILE}} {{OUTPUT_FILE}}
```

- `-layout`: Maintains original text layout and spacing (useful for columns or fixed-width formatting)
- **Caution**: Layout mode preserves column spacing but may require downstream adjustments in Markdown

### Extract Specific Page Range

```bash
pdftotext -f 1 -l 10 {{INPUT_FILE}} {{OUTPUT_FILE}}
```

- `-f 1`: Start from page 1
- `-l 10`: End at page 10
- Useful for large PDFs to manage memory and enable partial processing

### Extract to Standard Output

```bash
pdftotext -layout {{INPUT_FILE}} -
```

- `-`: Output to stdout instead of file

### Extract with Encoding Specification

```bash
pdftotext -enc UTF-8 {{INPUT_FILE}} {{OUTPUT_FILE}}
```

- Ensures proper character encoding for international text

## Canonical command templates (planner-safe)

| id                | description                          | template |
|-------------------|--------------------------------------|----------|
| `pdf2txt_reflow`  | PDF → text with reflow               | `pdftotext "{{INPUT_FILE}}" "{{OUTPUT_FILE}}"` |
| `pdf2txt_layout`  | PDF → text preserving layout         | `pdftotext -layout "{{INPUT_FILE}}" "{{OUTPUT_FILE}}"` |
| `pdf2txt_pages`   | PDF → text for specific page range   | `pdftotext -f 1 -l 10 "{{INPUT_FILE}}" "{{OUTPUT_FILE}}"` |
| `pdf2txt_utf8`    | PDF → UTF-8 encoded text             | `pdftotext -enc UTF-8 "{{INPUT_FILE}}" "{{OUTPUT_FILE}}"` |
| `pdf2md_pipeline` | PDF → Markdown (via text extraction) | `pdftotext -layout "{{INPUT_FILE}}" "$TEMP_DIR/extracted.txt" && pandoc --to=gfm --wrap=none "$TEMP_DIR/extracted.txt" -o "{{OUTPUT_FILE}}"` |

**Planner guidance**

- **Use pdftotext as the first choice for PDFs that contain real text**.
- Include the `-layout` flag when you need to preserve the original text layout and spacing (useful if the PDF has columns or fixed-width formatting).
- **Be cautious with -layout**: it will keep column layout spacing, which might require downstream adjustments in Markdown. By default (without -layout), pdftotext attempts to reflow text, which can simplify paragraphs but may mix columns.
- **Always direct output to a .txt or .md file** (plain UTF-8 text) for the next step.
- **If the PDF is large, consider extracting in segments** (using -f and -l to specify page ranges) to manage memory and enable partial processing.
- **For PDF → Markdown conversion**: Use the `pdf2md_pipeline` template which combines pdftotext + pandoc in a single command.
- **Fallback logic**: If pdftotext produces no output (common with scanned/image PDFs) or garbled text, that signals the need to fall back to OCR (Tesseract) instead.

## Output Formats

- Plain text (.txt)
- UTF-8 encoded text
- Layout-preserved text

## Security Considerations

- ✅ Local processing only
- ✅ No network access required
- ✅ Safe for sensitive documents
- ✅ No data transmission to external services

## Performance

- **Speed**: Very fast for text-based PDFs
- **Memory**: Low memory usage
- **File Size**: Handles large PDF files efficiently

## Best Practices

1. **Use as first choice for text-based PDFs** - fastest and most reliable for digital text
2. Use `-layout` flag to preserve document structure when needed
3. Specify page ranges for large documents to manage memory
4. Check if PDF is text-based before using (avoid for scanned documents)
5. Consider encoding issues with special characters - use `-enc UTF-8` when needed
6. **Always output to plain UTF-8 text** for downstream processing
7. **Monitor output quality** - no output or garbled text indicates need for OCR fallback

## Integration Notes

- **Fallback strategy**: If pdftotext produces no output or garbled text, switch to OCR pipeline (ImageMagick + Tesseract)
- **Layout decisions**: Choose between `-layout` (preserves spacing) and default reflow based on document analysis
- **Page segmentation**: For large PDFs, extract in chunks to avoid memory issues
- **Encryption handling**: If PDF is encrypted, may need Ghostscript preprocessing or password handling

## When to Use vs When NOT to Use

### When to Use

- Text-based PDFs with embedded text layer
- When fast text extraction is needed
- Digital documents created from word processors
- PDFs with simple or complex layouts that need text extraction
- When you need to preserve original text layout

### When NOT to Use

- Scanned PDFs or image-based documents (use OCR instead)
- When images need to be extracted (use pdfimages)
- Encrypted PDFs without password access
- When visual layout preservation is critical (consider other tools)

## Sample step emitted by planner

```bash
# id: extract_pdf_text
pdftotext -layout "{{INPUT_FILE}}" "{{OUTPUT_FILE}}"
# fallback: if no output, switch to OCR pipeline
```

Images won't be captured by this step - use pdfimages separately if needed.
