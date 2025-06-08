---
tool: tesseract
kind: ocr-engine
tool_min_version: "4.0"
tool_version_check: "tesseract --version | head -1"
recommended_output_format: text
installation:
  macos: "brew install tesseract"
  ubuntu: "apt-get install tesseract-ocr"
  windows: "Download from https://github.com/UB-Mannheim/tesseract/wiki"
---

# Tesseract OCR Engine

## Overview

Tesseract is an open-source OCR (Optical Character Recognition) engine that can extract text from images and scanned documents.

**IMPORTANT**: Tesseract requires image input (PNG, JPEG, TIFF, etc.) and cannot directly process PDF files. Use ImageMagick to convert PDF pages to images first.

## Installation

- **macOS**: `brew install tesseract`
- **Ubuntu/Debian**: `apt-get install tesseract-ocr`
- **Windows**: Download from <https://github.com/UB-Mannheim/tesseract/wiki>

## Capabilities

- Text extraction from images
- Multiple language support
- PDF output (searchable)
- HOCR output (HTML with position data)
- Multiple output formats

## Common Usage Patterns

### Basic OCR to Text

```bash
tesseract {{INPUT_FILE}} {{OUTPUT_FILE}} -l eng
```

- `-l eng`: Use English language model
- **Output will be `{{OUTPUT_FILE}}.txt`** (Tesseract automatically appends .txt)

### OCR with Multiple Languages

```bash
tesseract {{INPUT_FILE}} {{OUTPUT_FILE}} -l eng+fra+deu
```

- Supports multiple languages simultaneously (English + French + German)

### OCR to Searchable PDF

```bash
tesseract {{INPUT_FILE}} {{OUTPUT_FILE}} -l eng pdf
```

- Creates searchable PDF with text layer

### OCR with HOCR Output

```bash
tesseract {{INPUT_FILE}} {{OUTPUT_FILE}} -l eng hocr
```

- Outputs HTML with text position information

## Canonical command templates (planner-safe)

| id                | description                          | template |
|-------------------|--------------------------------------|----------|
| `img2txt_eng`     | Image → English text                 | `tesseract "{{INPUT_FILE}}" "$TEMP_DIR/ocr_output" -l eng` |
| `img2txt_multi`   | Image → multi-language text         | `tesseract "{{INPUT_FILE}}" "$TEMP_DIR/ocr_output" -l eng+fra+deu` |
| `img2pdf_search`  | Image → searchable PDF              | `tesseract "{{INPUT_FILE}}" "$TEMP_DIR/searchable" -l eng pdf` |
| `img2hocr_pos`    | Image → HTML with positions         | `tesseract "{{INPUT_FILE}}" "$TEMP_DIR/hocr_output" -l eng hocr` |

**Planner guidance**

- **Ensure the pipeline converts PDFs to images first** (via pdfimages or convert), since Tesseract cannot read PDF files directly.
- **Invoke Tesseract on each page image with an appropriate language pack**: e.g. tesseract page-001.png output_page1 -l eng for English text.
- **Always specify -l with the correct language** (or multiple languages like -l eng+deu for English+German) to improve accuracy.
- **Tesseract outputs a text file by default** (e.g. output_page1.txt in the example above) – the prompt template should reflect that the output will have .txt appended automatically.
- **Plan to concatenate or merge OCR text outputs** if multiple pages are processed individually.
- **For better fidelity: use high-resolution inputs** (300 DPI or higher images) and consider pre-processing images (deskew, noise reduction) before OCR.

## Output Formats

- Plain text (.txt)
- Searchable PDF (.pdf)
- HOCR HTML (.hocr)
- TSV data (.tsv)

## Security Considerations

- ✅ Local processing only
- ✅ No network access required
- ✅ Safe for sensitive documents
- ✅ No data transmission to external services

## Performance

- **Speed**: Moderate, depends on image complexity and size
- **Memory**: Moderate memory usage
- **File Size**: Works best with high-resolution images (300+ DPI)

## Integration Notes

- **PDF preprocessing required**: Always convert PDF pages to images using ImageMagick before OCR
- **Image quality critical**: Use 300+ DPI images for best accuracy
- **Language detection**: Specify correct language models for optimal results
- **Layout preservation**: Tesseract will not preserve layout like tables or columns in Markdown – it outputs plain text lines
- **Post-processing needed**: OCR'd tables might come out as lines of text that require conversion to Markdown tables by an LLM or script
- **Error handling**: Always verify if any page failed (Tesseract returns non-zero status on errors) and handle appropriately

## Best Practices

1. **Use high-resolution images for better accuracy** (300+ DPI recommended)
2. **Preprocess images** (deskew, denoise) with ImageMagick for better results
3. **Specify appropriate language models** with -l flag
4. **Consider image quality and contrast** before OCR
5. **Use appropriate page segmentation modes** for complex layouts
6. **Plan for post-processing** of structured content (tables, lists)
7. **Handle multi-page documents** by processing each page individually then concatenating

## When to Use vs When NOT to Use

### When to Use

- **Scanned PDFs or image-based documents**
- When text extraction fails with pdftotext (indicates scanned content)
- Images containing text that need to be converted to searchable text
- **When analysis shows `requires_ocr=true`**
- Creating searchable PDFs from image documents

### When NOT to Use

- **Text-based PDFs** (use pdftotext instead - much faster)
- When images don't contain readable text
- Very low-quality or heavily distorted images
- When speed is critical and text-based extraction is available

## Sample step emitted by planner

```bash
# id: ocr_page_text
tesseract "$TEMP_DIR/page-001.png" "$TEMP_DIR/page1_text" -l eng
# output: $TEMP_DIR/page1_text.txt
# follow with: concatenate all page texts or convert tables to markdown
```

**Note**: Tesseract will not preserve layout like tables or columns - plan for post-processing structured content.

## Fallback Strategy

If Tesseract's output is very poor (e.g. due to low-quality scans):

1. Retry with different settings (OCR engine modes)
2. Preprocess images with ImageMagick (deskew, enhance contrast)
3. Try different language models
4. Consider manual review for critical content
