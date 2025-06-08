---
tool: pandoc
kind: universal-converter
tool_min_version: "3.1"
tool_version_check: "pandoc --version | head -1"
recommended_output_format: markdown
installation:
  macos: "brew install pandoc"
  ubuntu: "apt-get install pandoc"
  windows: "choco install pandoc"
---

# Pandoc — "Swiss-army knife" document converter

*Pipeline role*: first-choice **DOCX→Markdown** engine when we need rich, *Git-friendly* Markdown and can tolerate small formatting losses. Also acts as fallback HTML↔DOCX ↔EPUB bridge.

---

## Why Pandoc vs. MarkItDown / LibreOffice?

| Feature / Need                               | Pandoc | MarkItDown | LibreOffice |
|----------------------------------------------|:------:|:----------:|:-----------:|
| 140+ formats in / out                        | **✅** | ❌ | ❌ |
| Custom filters & Lua pre-processors          | **✅** | ❌ | ❌ |
| Preserves footnotes, citations, metadata     | **✅** | ⚠︎ | ⚠︎ |
| Fast start-up (single static binary)         | **✅** | ✅ | ❌ |
| Perfect list start numbers                   | ⚠︎ needs `+startnum` | ❌ | ✅ |
| Pixel-perfect layout                         | ❌ | ⚠︎ | **✅** |

Rule of thumb: **Use Pandoc** for narrative docs, academic papers, and Word reports; switch to LibreOffice for heavy layout fidelity, and MarkItDown for quick PPTX slide dumps.

---

## Canonical command templates (planner-safe)

| id                 | description                       | template |
|--------------------|-----------------------------------|----------|
| `docx2md_strict`   | DOCX → GFM, keep list numbers     | `pandoc --from=docx+startnum --to=gfm --wrap=none --extract-media "$TEMP_DIR/media" "{{INPUT_FILE}}" -o "{{OUTPUT_FILE}}"` |
| `pptx2md_simple`   | PPTX → Markdown (text only)       | `pandoc --extract-media "$TEMP_DIR/media" "{{INPUT_FILE}}" -o "{{OUTPUT_FILE}}"` |
| `text2md_clean`    | Plain text → clean Markdown         | `pandoc --to=gfm --wrap=none "{{INPUT_FILE}}" -o "{{OUTPUT_FILE}}"` |
| `md2docx_template` | Markdown → styled DOCX            | `pandoc "{{INPUT_FILE}}" --reference-doc "templates/wordref.docx" -o "{{OUTPUT_FILE}}"` |
| `html2md_clean`    | HTML → clean Markdown             | `pandoc --from=html --to=gfm --wrap=none "{{INPUT_FILE}}" -o "{{OUTPUT_FILE}}"` |

**Planner guidance**

* For Office → MD **always** add `--extract-media "$TEMP_DIR/media"` to save embedded images as separate files with Markdown links instead of base64-encoding them.
* Use `--from=docx+startnum` to preserve custom list numbering and `--to=gfm` (GitHub-Flavored Markdown) for maximum compatibility.
* Add `--wrap=none` to avoid inserting line breaks, preserving original paragraph wrapping for better diff fidelity.
* **IMPORTANT: Pandoc CANNOT read PDF files directly** - it can only write TO PDF, not read FROM PDF. For PDF conversion, use pdftotext first, then pipe to Pandoc.
* For large text files, use `--chunk-size=<N>` to split processing and avoid memory errors.
* If Pandoc output loses list nesting or formatting, plan a follow-up fix (e.g. run MarkItDown or an LLM-based cleanup) as needed.

---

## High-signal option cheat-sheet

| Option                            | Purpose / Tip |
|-----------------------------------|---------------|
| `--from=docx+startnum`            | Preserve custom list numbering |
| `--to=gfm` / `--to=markdown_strict` | GitHub MD vs strict MD (no fenced divs) |
| `--wrap=none`                     | Keep long lines intact (better diff) |
| `--extract-media DIR`             | Save images to DIR and link relative paths (prevents base64 bloat) |
| `-M pagetitle="My Title"`         | Inject metadata into output |
| `--chunk-size=N`                  | Paginate huge PDFs (≥ 3.1) to avoid memory errors |
| `--lua-filter scripts/fix_tables.lua` | Post-process output for table alignment issues |

---

## Integration notes

* **Performance**: DOCX→MD ≈ 0.4 s per MB. **Note: Pandoc cannot import PDFs** - use pdftotext for PDF extraction first.
* **Filters**: If planner needs manual tweaks (e.g., table alignment), add Lua filter step:
  `pandoc --lua-filter scripts/fix_tables.lua …`
* **List bug**: If downstream validation flags lost list depth, re-run MarkItDown or an LLM `fix_list` step.
* **Exit codes**: 0 success; >0 fatal. Warnings print to stderr but still exit 0. Capture stderr for QA.
* **PDF handling**: **Pandoc cannot read PDF files**. For PDF conversion, use pdftotext to extract text first, then use Pandoc to convert the extracted text to Markdown.

---

## Strengths / Limitations (pipeline context)

| ✔︎ Strengths                              | ✖︎ Limitations |
|-------------------------------------------|---------------|
| Single static binary → easy CI packaging  | Loses SmartArt / text boxes → plain text |
| Rich set of output extensions & filters   | Resets list start # unless `+startnum` |
| Extracts images cleanly, keeps EPUB/Citeproc | Large PDFs can OOM (use --chunk-size) |
| Fast for Word documents                   | Strips precise column layout |
| Excellent for academic/narrative documents | **Cannot read PDF files directly** |

---

## Sample step emitted by planner

```bash
# id: word_to_md
pandoc --from=docx+startnum --to=gfm --wrap=none \
       --extract-media "$TEMP_DIR/media" \
       "{{INPUT_FILE}}" -o "{{OUTPUT_FILE}}"
```

Next steps: run htmlhint on rendered HTML → catch any tag errors, then summary validation.

## Security Considerations

* ✅ Local processing only
* ✅ No network access required (unless templates pull remote images)
* ✅ Safe for sensitive documents
* ⚠️ Large PDFs may cause memory issues - use `--chunk-size` for files >100MB

## Performance

* **Speed**: DOCX→MD ≈ 0.4s per MB, PDF import ≈ 6s per 10 pages
* **Memory**: Can consume significant memory with large PDFs
* **File Size**: Use `--chunk-size` for PDFs >100MB

## Best Practices

1. Always quote file paths in commands
2. **Always include `--extract-media` flag** to save embedded images to separate files with Markdown image links instead of base64-encoding them
3. Add `+startnum` extension for preserving list numbering
4. Use `--wrap=none` for better Git diffs and preserved paragraph wrapping
5. Monitor memory usage with large PDF files and use `--chunk-size` for files >100MB
6. For tables or alignment issues, leverage Pandoc's filter capability (e.g. a Lua filter) to post-process the output
7. Only use for digital text PDFs - skip if OCR is required

## When to Use vs When NOT to Use

### When to Use

* Converting Office documents (DOCX, PPTX) to Markdown
* Converting plain text or HTML to Markdown
* When you need to preserve footnotes, citations, and metadata
* Academic papers and narrative documents
* When custom filters or Lua preprocessing is needed

### When NOT to Use

* **PDF files (Pandoc cannot read PDFs)** - use pdftotext first
* When pixel-perfect layout preservation is critical (use LibreOffice)
* For quick PPTX slide dumps (MarkItDown is faster)
* When dealing with complex SmartArt or text boxes that need preservation
