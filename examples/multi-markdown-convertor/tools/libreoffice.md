---
tool: libreoffice
kind: office-converter
tool_min_version: "7.0"
tool_version_check: "libreoffice --version"
recommended_output_format: html
installation:
  macos: "brew install --cask libreoffice"
  ubuntu: "apt-get install libreoffice"
  windows: "Download from https://www.libreoffice.org/download/download/"
---

# LibreOffice

## Overview

Full-featured office suite that can run in headless mode for document conversion. Excellent compatibility with Microsoft Office formats and reliable conversion capabilities.

**IMPORTANT**: LibreOffice is designed for Office documents (DOCX, PPTX, XLSX) and cannot process PDF files or plain text effectively.

## Installation

- **macOS**: `brew install --cask libreoffice`
- **Ubuntu/Debian**: `apt-get install libreoffice`
- **Windows**: Download from <https://www.libreoffice.org/>

## Capabilities

- Converts Office documents (DOCX, PPTX, XLSX) to various formats
- Headless operation for server environments
- Batch processing capabilities
- Preserves complex formatting and layouts
- Supports many input and output formats
- High-fidelity conversion with complex tables, embedded media, and advanced formatting

## Common Usage Patterns

### Convert DOCX to HTML (Recommended for Markdown Pipeline)

```bash
libreoffice --headless --convert-to html --outdir $TEMP_DIR {{INPUT_FILE}}
```

- HTML output retains styles, images, and layout for subsequent Pandoc conversion
- Use `--outdir $TEMP_DIR` to collect conversion output in controlled location

### Convert PPTX to HTML

```bash
libreoffice --headless --convert-to html --outdir $TEMP_DIR {{INPUT_FILE}}
```

- Preserves slide layouts and embedded media

### Convert DOCX to PDF

```bash
libreoffice --headless --convert-to pdf --outdir $TEMP_DIR {{INPUT_FILE}}
```

### Convert XLSX to CSV

```bash
libreoffice --headless --convert-to csv --outdir $TEMP_DIR {{INPUT_FILE}}
```

### Convert multiple files

```bash
libreoffice --headless --convert-to html --outdir $TEMP_DIR *.docx
```

## Canonical command templates (planner-safe)

| id                | description                          | template |
|-------------------|--------------------------------------|----------|
| `docx2html_hifi`  | DOCX → HTML preserving formatting    | `libreoffice --headless --convert-to html --outdir "$TEMP_DIR" "{{INPUT_FILE}}"` |
| `pptx2html_slides`| PPTX → HTML with slide layouts       | `libreoffice --headless --convert-to html --outdir "$TEMP_DIR" "{{INPUT_FILE}}"` |
| `xlsx2csv_data`   | XLSX → CSV for data extraction       | `libreoffice --headless --convert-to csv --outdir "$TEMP_DIR" "{{INPUT_FILE}}"` |
| `office2pdf_hifi` | Office → high-fidelity PDF           | `libreoffice --headless --convert-to pdf --outdir "$TEMP_DIR" "{{INPUT_FILE}}"` |

**Planner guidance**

- **Use LibreOffice in headless mode** to convert Office documents to an intermediary format that preserves formatting (e.g. HTML or PDF).
- **For Markdown pipelines, converting DOCX/PPTX to HTML is recommended** (libreoffice --headless --convert-to html), since the HTML will retain styles, images, and layout which can then be fed to Pandoc for Markdown conversion.
- **Always specify an output directory with --outdir $TEMP_DIR** to collect conversion output in a controlled location.
- **Because LibreOffice produces very faithful output** (including complex tables, embedded media, and advanced formatting), use it when Pandoc or MarkItDown output is missing nuances.
- **It's resource-intensive and slower**, so reserve it as a secondary step: for example, if Pandoc mangles a document's formatting or when handling older formats (e.g. .doc, .xls that MarkItDown cannot open).
- **After HTML conversion, run an HTML cleaner (Tidy)** to fix any structural issues (LibreOffice HTML can be verbose or have some quirks).
- **LibreOffice cannot read PDFs or plain text well**, so do not use it for those inputs.

## Output Formats

- **HTML** (preserves layout, recommended for Markdown pipeline)
- PDF (high-fidelity)
- CSV (for spreadsheets)
- ODT, ODS, ODP (native formats)
- RTF, TXT (basic formats)

## Security Considerations

- ✅ Local processing only
- ✅ No network access required
- ✅ Safe for sensitive documents
- ⚠️ Resource intensive - may consume significant CPU and memory

## Performance

- **Speed**: Slower than specialized tools but high quality
- **Memory**: Resource intensive, especially for large documents
- **File Size**: Handles large Office files well

## Integration Notes

- **HTML as intermediary**: Converting to HTML first preserves maximum fidelity, then use Pandoc for final Markdown conversion
- **Resource management**: Monitor CPU and memory usage, especially with large or complex documents
- **Cleanup required**: LibreOffice HTML output may need Tidy cleanup before further processing
- **Legacy format support**: Best choice for older formats (.doc, .xls) that other tools cannot handle

## When to Use

- Converting Office documents with complex formatting
- When you need high-fidelity conversion
- **When Pandoc or MarkItDown output is missing nuances**
- **Handling older formats (e.g. .doc, .xls that MarkItDown cannot open)**
- **Preserving complex table layouts, tracked changes, or SmartArt (which Pandoc might lose)**
- When dealing with password-protected documents
- **Maximum fidelity is needed, such as preserving complex table layouts, tracked changes, or SmartArt**

## When NOT to Use

- When speed is critical (use pandoc or markitdown)
- For simple text extraction (use specialized tools)
- In resource-constrained environments
- **For PDF input files (LibreOffice cannot read PDFs well)**
- **For plain text input (not LibreOffice's strength)**
- When quick "good enough" conversion is acceptable

## Best Practices

1. **Use `--headless` flag for server environments** and automated processing
2. **Always specify `--outdir $TEMP_DIR`** to control output location
3. Monitor resource usage with large files
4. **Use for high-fidelity conversions when quality matters** more than speed
5. **Consider as fallback when Pandoc or MarkItDown lose formatting**
6. **Follow with HTML cleanup (Tidy) when converting to HTML**
7. **Reserve for secondary processing** - use faster tools first, LibreOffice when needed

## Sample step emitted by planner

```bash
# id: office_to_html_hifi
libreoffice --headless --convert-to html --outdir "$TEMP_DIR" "{{INPUT_FILE}}"
# follow with: tidy -q -m "$TEMP_DIR/$(basename "{{INPUT_FILE}}" .docx).html"
# then: pandoc --from=html --to=gfm "$TEMP_DIR/output.html" -o "{{OUTPUT_FILE}}"
```

Use LibreOffice when maximum fidelity is required and other tools lose important formatting.
