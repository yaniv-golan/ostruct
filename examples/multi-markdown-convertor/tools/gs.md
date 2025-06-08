---
tool: gs
kind: pdf-utility
tool_min_version: "9.50"
tool_version_check: "gs --version"
recommended_output_format: pdf
installation:
  macos: "brew install ghostscript"
  ubuntu: "apt-get install ghostscript"
  windows: "Download from https://www.ghostscript.com/download/gsdnld.html"
---

# Ghostscript (gs) - PDF Processor

## Overview

Ghostscript is a suite of software for processing PostScript and PDF files. It can optimize, compress, and manipulate PDF files for better processing performance.

**IMPORTANT**: Ghostscript is primarily for PDF optimization and preprocessing. For text extraction, use pdftotext. For image extraction, use pdfimages.

## Installation

- **macOS**: `brew install ghostscript`
- **Ubuntu/Debian**: `apt-get install ghostscript`
- **Windows**: Download from <https://www.ghostscript.com/>

## Capabilities

- PDF compression and optimization
- PDF linearization for web viewing
- Resolution downsampling
- Color space conversion
- PDF/A conversion for archival
- Page extraction and manipulation
- PDF repair and preprocessing

## Common Usage Patterns

### Compress large PDF (Recommended)

```bash
gs -dSAFER -sDEVICE=pdfwrite -dCompatibilityLevel=1.4 -dPDFSETTINGS=/ebook -dNOPAUSE -dBATCH -dQUIET -sOutputFile={{OUTPUT_FILE}} {{INPUT_FILE}}
```

- Compresses PDF for smaller file size with security protection

### Linearize PDF for web

```bash
gs -dSAFER -sDEVICE=pdfwrite -dLinearize -dNOPAUSE -dBATCH -dQUIET -sOutputFile={{OUTPUT_FILE}} {{INPUT_FILE}}
```

- Optimizes PDF for progressive web loading

### Downsample images in PDF

```bash
gs -sDEVICE=pdfwrite -dDownsampleColorImages=true -dColorImageResolution=150 -dNOPAUSE -dQUIET -dBATCH -sOutputFile={{OUTPUT_FILE}} {{INPUT_FILE}}
```

- Reduces image resolution to 150 DPI

### Extract specific pages

```bash
gs -dSAFER -sDEVICE=pdfwrite -dFirstPage=1 -dLastPage=5 -dNOPAUSE -dBATCH -dQUIET -sOutputFile={{OUTPUT_FILE}} {{INPUT_FILE}}
```

- Extracts pages 1-5 to new PDF

### Repair problematic PDF

```bash
gs -dSAFER -sDEVICE=pdfwrite -dNOPAUSE -dBATCH -dQUIET -sOutputFile={{OUTPUT_FILE}} {{INPUT_FILE}}
```

- Repairs corrupted PDFs or removes encryption (if password provided)

## Canonical command templates (planner-safe)

| id                | description                          | template |
|-------------------|--------------------------------------|----------|
| `pdf_compress`    | Compress PDF for smaller size        | `gs -dSAFER -sDEVICE=pdfwrite -dPDFSETTINGS=/ebook -dNOPAUSE -dBATCH -dQUIET -sOutputFile="{{OUTPUT_FILE}}" "{{INPUT_FILE}}"` |
| `pdf_linearize`   | Linearize PDF for web                | `gs -dSAFER -sDEVICE=pdfwrite -dLinearize -dNOPAUSE -dBATCH -dQUIET -sOutputFile="{{OUTPUT_FILE}}" "{{INPUT_FILE}}"` |
| `pdf_extract_pages`| Extract specific page range         | `gs -dSAFER -sDEVICE=pdfwrite -dFirstPage=1 -dLastPage=10 -dNOPAUSE -dBATCH -dQUIET -sOutputFile="{{OUTPUT_FILE}}" "{{INPUT_FILE}}"` |
| `pdf_repair`      | Repair/flatten problematic PDF       | `gs -dSAFER -sDEVICE=pdfwrite -dNOPAUSE -dBATCH -dQUIET -sOutputFile="{{OUTPUT_FILE}}" "{{INPUT_FILE}}"` |

**Planner guidance**

- **Use Ghostscript for tasks like PDF compression, conversion, or pre-processing** before text extraction.
- **For example, to reduce PDF size or simplify a complex PDF**, you can run a command with -sDEVICE=pdfwrite and appropriate settings (e.g., -dPDFSETTINGS=/ebook for medium-quality compression) to produce a streamlined PDF.
- **In a Markdown pipeline, this can be a pre-step** if a PDF is too large or problematic for tools like Pandoc/pdftotext (Ghostscript can sometimes repair corrupted PDFs or remove encryption if password is provided).
- **Always include -dSAFER** in prompts to prevent Ghostscript from executing any malicious PostScript in untrusted PDFs.
- **Also use -dNOPAUSE -dBATCH -dQUIET** to make it run non-interactively and quietly.
- **Consider Ghostscript as a fallback** if other PDF tools fail: for instance, if pdftotext cannot read a PDF due to PDF version issues or if we need to flatten transparency or layers.

## Output Formats

- PDF (optimized)
- PDF/A (archival format)
- PostScript
- Various image formats (PNG, JPEG, TIFF)

## Security Considerations

- ✅ Local processing only
- ✅ No network access required
- ✅ Safe for sensitive documents
- **✅ Always use `-dSAFER`** to prevent execution of malicious PostScript in untrusted PDFs
- ✅ No data transmission to external services

## Performance

- **Speed**: Moderate, depends on optimization level
- **Memory**: Can be memory intensive for large files
- **File Size**: Excellent for reducing PDF file sizes

## Integration Notes

- **PDF preprocessing**: Use before other tools when PDFs are too large or problematic
- **Repair functionality**: Can fix corrupted PDFs or PDF version issues that block other tools
- **Security first**: Always include -dSAFER for untrusted PDFs
- **Non-interactive operation**: Use -dNOPAUSE -dBATCH -dQUIET for automated processing
- **Not for conversion**: Ghostscript is not used for text or markdown conversion directly – it's purely a utility to prep PDFs

## Best Practices

1. **Always use `-dSAFER`** for untrusted PDFs to prevent malicious PostScript execution
2. **Use `-dNOPAUSE -dBATCH -dQUIET`** to make it run non-interactively and quietly
3. Choose appropriate `-dPDFSETTINGS` for use case (/screen, /ebook, /printer, /prepress)
4. **Use as preprocessing step** when other PDF tools fail
5. **Specify output file** with -sOutputFile since gs won't simply print to stdout for PDF output
6. Test compression settings on sample files first
7. **Consider as fallback** for PDF version issues or corruption

## When to Use vs When NOT to Use

### When to Use

- **PDF is too large** or problematic for other tools (Pandoc/pdftotext)
- **PDF has version issues** or corruption that blocks other tools
- **Need to flatten transparency or layers** (printing the PDF to itself via Ghostscript can resolve such issues)
- When PDF compression is needed before processing
- **As a fallback** when pdftotext cannot read a PDF
- For extracting specific pages to a new PDF before processing those pages separately

### When NOT to Use

- **For text or markdown conversion directly** (use pdftotext, then other tools)
- When PDF is already working fine with other tools
- For image extraction (use pdfimages instead)
- When file size is not an issue

## Sample step emitted by planner

```bash
# id: pdf_preprocess
gs -dSAFER -sDEVICE=pdfwrite -dPDFSETTINGS=/ebook -dNOPAUSE -dBATCH -dQUIET \
   -sOutputFile="$TEMP_DIR/optimized.pdf" "{{INPUT_FILE}}"
# follow with: pdftotext "$TEMP_DIR/optimized.pdf" "{{OUTPUT_FILE}}"
```

Use Ghostscript to prep PDFs (optimize, split, etc.) to improve downstream conversion fidelity.
