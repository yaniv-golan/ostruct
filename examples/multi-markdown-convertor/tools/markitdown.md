---
tool: markitdown
kind: office-to-markdown
tool_min_version: "0.1.0"
tool_version_check: "markitdown --version"
recommended_output_format: markdown
installation:
  macos: "pip install markitdown"
  ubuntu: "pip install markitdown"
  windows: "pip install markitdown"
---

# MarkItDown — Office → Markdown Converter

*Pipeline role*: quickest way to obtain **reasonably structured Markdown** from DOCX, PPTX, XLSX **when pandoc mangles tables** or LibreOffice is overkill.
Use it for "good-enough" drafts that a follow-up LLM (`fix_list`) step can polish.

## Why MarkItDown over pandoc / python-docx?

| Need                                               | MarkItDown | pandoc | python-docx |
|----------------------------------------------------|:----------:|:------:|:-----------:|
| Embedded images → local files + Markdown links     | **✅**     | ⚠︎ (base64) | Manual |
| XLSX → pipe-delimited table Markdown               | **✅**     | ❌        | ❌ |
| PPTX text boxes → Markdown paragraphs              | **✅**     | ⚠︎ loses layout | ❌ |
| Deep nested lists (≥3)                             | ⚠︎ *flattens* | ✅ | Manual |
| SmartArt, diagrams                                 | ❌ (image fallback) | ✅ | ❌ |
| Speed (no Java, no UI)                             | **fast**   | moderate | fast |

*Rule of thumb*: start with MarkItDown for DOCX/PPTX unless analysis flags **nested lists depth > 2** or **custom numbering** → then fallback to pandoc.

## Canonical command templates (planner-safe)

| id                | description                          | template |
|-------------------|--------------------------------------|----------|
| `docx2md_quick`   | Word → Markdown, default rules       | `python -m markitdown "{{INPUT_FILE}}" -o "{{OUTPUT_FILE}}" --media-dir "$TEMP_DIR/media"` |
| `pptx2md_slides`  | PPTX → one big `.md`                 | `python -m markitdown "{{INPUT_FILE}}" -o "{{OUTPUT_FILE}}" --media-dir "$TEMP_DIR/slides_media"` |
| `xlsx2md_tables`  | XLSX → Markdown tables               | `python -m markitdown "{{INPUT_FILE}}" -o "{{OUTPUT_FILE}}"` |
| `docx2md_textonly`| DOCX → text-only conversion          | `python -m markitdown "{{INPUT_FILE}}" -o "{{OUTPUT_FILE}}" --no-images` |
| `pdf2md_simple`   | (experimental) PDF → Markdown        | `python -m markitdown "{{INPUT_FILE}}" -o "{{OUTPUT_FILE}}"` |

**Planner guidance**

1. **Always add `--media-dir "$TEMP_DIR/..."` option** so that images are extracted to a temporary folder and referenced with Markdown links (preventing clutter in the output directory).
2. Use `--no-images` if a text-only conversion is desired, to skip embedding images entirely.
3. **MarkItDown uniquely converts spreadsheets to pipe-delimited Markdown tables**, so use it for XLSX → MD table fidelity.
4. **Be aware it flattens deeply nested lists beyond 2 levels** – if analysis finds list depth > 2 or custom numbering, prefer Pandoc or schedule an LLM post-processing step (e.g. a fix_list repair prompt) after MarkItDown.
5. **Avoid using its experimental PDF mode on scanned or complex layout PDFs** – it only handles simple text PDFs and will drop ordering on multi-column pages.
6. **Treat MarkItDown's exit code 2 as a partial success** (some content unsupported, e.g. SmartArt fallback to images) and plan fallbacks or warnings accordingly.

## Option cheat-sheet

| Flag / Arg             | Purpose                         |
|------------------------|---------------------------------|
| `-o FILE.md`           | Write Markdown to file          |
| `--media-dir DIR`      | Extract images here (always use with temp dir) |
| `--overwrite`          | Allow overwriting output        |
| `--no-images`          | Ignore embedded images          |
| `--tab-size N`         | Spaces per tab in code blocks   |
| `--pdf-mode simple`    | Use text layer only, no OCR     |

## Integration notes

* **Post-processing**: run `htmlhint` on rendered HTML → catch unclosed tags from malformed OOXML.
* **Image paths**: MarkItDown writes relative links; when merging into a single mdast, prepend media dir path or move images.
* **Exit codes**: 0 success, **2 for "partial" (unsupported objects, e.g. SmartArt fallback to images)**, >2 fatal. The planner treats code 2 as *success but warn*.
* **Performance**: DOCX 5 MB ≈ 0.7 s on M-series CPU; PPTX 8 MB ≈ 1.1 s.
* **Limitations**: No support for legacy `.doc` / `.xls`; convert via LibreOffice first.

## Strengths / Limitations (pipeline context)

| ✔︎ Strengths                                  | ✖︎ Limitations |
|-----------------------------------------------|---------------|
| Fast, no UI, Python-only install              | Nested lists flatten after level 2 |
| Extracts images to disk with --media-dir      | Custom numbered lists reset to 1 |
| Good for PPTX slides → readable Markdown      | Drops shape order on complex slide layouts |
| XLSX to Markdown table is unique              | Experimental PDF handling, no OCR |
| Works offline                                 | Less battle-tested than pandoc |
| Handles SmartArt gracefully (image fallback)  | Cannot read legacy .doc/.xls formats |

## Sample step emitted by planner

```bash
# id: slides_md
python -m markitdown "{{INPUT_FILE}}" \
       -o "$TEMP_DIR/$(basename "{{INPUT_FILE}}" .pptx).md" \
       --media-dir "$TEMP_DIR/slides_media"
# follow with: ostruct run prompts/nested/fix_list.j2 …
```

Put a list-repair step after PPTX conversions if analysis flagged deep nesting.

## Security Considerations

* ✅ Local processing only
* ✅ No network access required
* ✅ Safe for sensitive documents
* ✅ Python-based, no external dependencies

## Performance

* **Speed**: Very fast - DOCX 5MB ≈ 0.7s, PPTX 8MB ≈ 1.1s
* **Memory**: Low memory usage
* **File Size**: Handles large Office files efficiently

## Best Practices

1. **Always specify `--media-dir` with temp directory** to prevent image clutter in output directory
2. Use `--no-images` for text-only conversions to skip image processing entirely
3. **Plan follow-up list repair** if document analysis shows nested lists depth > 2
4. **Avoid PDF mode for scanned documents** - use OCR pipeline instead
5. **Treat exit code 2 as partial success** - content was converted but some elements (like SmartArt) fell back to images

## When to Use vs When NOT to Use

### When to Use

* Quick conversion of Office documents (DOCX, PPTX, XLSX) to Markdown
* When you need XLSX → Markdown table conversion
* For "good enough" drafts that will be post-processed
* When speed is more important than perfect formatting
* For PPTX slide content extraction

### When NOT to Use

* Documents with deeply nested lists (>2 levels) requiring preservation
* When custom list numbering must be preserved
* For scanned or complex layout PDFs
* Legacy Office formats (.doc, .xls) - use LibreOffice first
* When pixel-perfect formatting is critical

This revision:

* Adds YAML front-matter so the planner and safety checker can parse metadata.
* Provides ready-made, **whitelisted command templates**.
* Calls out exactly when to prefer MarkItDown vs. competing tools.
* Documents known pain-points (nested lists, numbering) the pipeline already has mitigations for.
