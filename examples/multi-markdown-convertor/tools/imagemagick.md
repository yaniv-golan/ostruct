---
tool: convert
kind: image-utility
tool_min_version: "7.0"
tool_version_check: "convert -version | head -1"
recommended_output_format: png
installation:
  macos: "brew install imagemagick"
  ubuntu: "apt-get install imagemagick"
  windows: "Download from https://imagemagick.org/script/download.php#windows"
---

# ImageMagick `convert`  (invoked as `magick convert` on IM 7)

*Purpose in our pipeline*: turn PDF pages (or embedded images) into **raster PNGs** so downstream OCR or GPT-4V captioning can run.  Also handles quick format swaps (e.g., PNG → JPEG) for web output.

---

## Why `convert` vs. `pdfimages`

| Need | Use `convert` | Use `pdfimages` |
|------|--------------|-----------------|
| Full-page raster (for OCR / vision LLM) | ✅ | — |
| Extract embedded bitmaps losslessly | — | ✅ |
| Crop / resize in one step | ✅ | — |
| Handles non-image PDF vector pages | ✅ | — |

---

## Canonical commands (planner-safe)

| id                  | what it does | template |
|---------------------|--------------|----------|
| `pdf2png_300dpi`    | Rasterize each PDF page to 300 dpi PNG | `magick convert -density 300 "{{INPUT_FILE}}" -background white -alpha remove +repage "$TEMP_DIR/page-%03d.png"` |
| `pdf2jpeg_thumb`    | Quick 150 dpi JPEG thumbnails | `magick convert -density 150 "{{INPUT_FILE}}" -resize 600x -quality 85 "$TEMP_DIR/thumb-%02d.jpg"` |
| `pdf_pages_subset`  | Extract pages 1-5 to PNG | `magick convert -density 300 "{{INPUT_FILE}}[0-4]" -background white -alpha remove +repage "$TEMP_DIR/subset-%02d.png"` |
| `img_resize`        | Down-scale any image | `magick convert "{{INPUT_FILE}}" -strip -resize 1024x "{{OUTPUT_FILE}}"` |
| `format_swap`       | PNG → high-qual JPEG | `magick convert "{{INPUT_FILE}}" -quality 92 "{{OUTPUT_FILE}}"` |

**Planner guidance**

* Always quote paths and pre-create `$TEMP_DIR` so `page-%d.png` lands in scratch space.
* **Always set a DPI density**: e.g. `-density 300` for OCR-quality full-page PNGs (300 DPI yields sharper text for Tesseract), `-density 150` for previews.
* **Flatten transparency with `-background white -alpha remove`** (PDFs with transparent layers will otherwise yield images with missing text or strange layering) and use `+repage` to reset the canvas so each output page image has a proper viewport.
* **For large PDFs, process pages in chunks** (e.g. input.pdf[0-49] for pages 1–50) to avoid excessive memory use.
* You can also downscale or compress images in the same step if needed (for instance, creating lower-res thumbnails with `-resize` or JPEG output for previews).

---

## Key options cheat-sheet

| Option | Purpose | Typical value |
|--------|---------|---------------|
| `-density {dpi}` | Raster DPI (higher = sharper, slower) | 300 for OCR, 150 for preview |
| `-background white -alpha remove` | Flatten transparency to white | always for PDF pages |
| `+repage` | Reset virtual canvas → avoids huge offsets | always after PDF raster |
| `-resize WxH` | Scale output | `-resize 1024x` |
| `[page-spec]` | Zero-based page indices | `input.pdf[10]` or `input.pdf[0-49]` |
| `-quality N` | JPEG compression | 85-92 |
| `-strip` | Remove metadata | for privacy/size reduction |

---

## Integration notes

* **Memory limits**: Use `magick -limit memory 1GiB` for CI runners or resource-constrained environments.
* **Security policies**: Modern ImageMagick disables Ghostscript write. Use only read-mode; we never pipe PDF out.
* **Exit codes**: `0` on success, `1` on any page error (safe for retry logic).
* **Page chunking**: For very large PDFs (600+ pages), process in chunks: `input.pdf[0-99]`, `input.pdf[100-199]`, etc.
* Nesting inside ostruct: treat as deterministic—no further safety approval needed once the command template matches whitelist.

---

## Strengths / Limitations (pipeline context)

| ✔︎ Strengths | ✖︎ Limitations |
|--------------|---------------|
| Handles any PDF (vector or raster) | Cannot extract *text* |
| One-liner page raster & resize | Syntax heavy; easy to mis-quote |
| Works offline, cross-platform | High RAM on 600 dpi multi-page |
| Supports 100+ formats | Security policies may block exotic operators |
| Excellent for OCR preprocessing | Memory intensive with large documents |

---

## Sample `.sh` step injected by planner

```bash
# id: raster_pages
magick convert -density 300 "{{INPUT_FILE}}" -background white -alpha remove \
               +repage "$TEMP_DIR/page-%03d.png"
```

Downstream steps can loop over page-*.png for OCR (tesseract) or GPT-4V captions.

## Security Considerations

* ✅ Local processing only
* ✅ No network access required
* ✅ Safe for sensitive documents
* ⚠️ **Always include `-dSAFER` equivalent protections** - modern ImageMagick policies prevent malicious operations
* ⚠️ Memory intensive - monitor resource usage

## Performance

* **Speed**: Fast for single pages, slower for large multi-page PDFs
* **Memory**: Can consume significant RAM with high DPI or many pages
* **File Size**: Output size depends on DPI and compression settings

## Best Practices

1. **Always quote file paths** and pre-create temp directories
2. **Use `-density 300` for OCR, `-density 150` for previews**
3. **Always include `-background white -alpha remove +repage`** for PDF processing
4. **Process large PDFs in chunks** to avoid memory issues
5. **Monitor memory usage** and set limits in resource-constrained environments
6. Use `-strip` to remove metadata for privacy
7. **Choose appropriate output format**: PNG for OCR, JPEG for previews

## When to Use vs When NOT to Use

### When to Use

* **Full-page capture of PDFs** (e.g. for OCR or visual QA)
* **Handle PDFs that contain vector graphics** (which pdfimages would skip)
* Image format conversions and preprocessing
* Creating thumbnails or previews
* **When you need full-page images** for downstream OCR processing

### When NOT to Use

* **Text extraction** (ImageMagick won't extract text - use pdftotext or OCR)
* When you only need embedded images (use pdfimages instead)
* Very large documents without chunking (memory issues)
* When text-based extraction is sufficient

This doc:

* Mirrors the YAML header used by other tools so the planner can parse metadata.
* Emphasises **exact safe command templates** for ImageMagick tasks relevant to our pipeline.
* Calls out Ghostscript policy quirks, memory limits, and quoting rules to keep the safety-check model informed.
* Keeps marketing fluff out; focuses on actionable integration guidance.
