---
tool: tidy
kind: html-validator
tool_min_version: "5.6"
tool_version_check: "tidy --version"
recommended_output_format: html
installation:
  macos: "brew install tidy-html5"
  ubuntu: "apt-get install tidy"
  windows: "Download from http://binaries.html-tidy.org/"
---

# Tidy HTML5 Validator

## Overview

Tidy is a local HTML validation and cleanup tool that can validate HTML syntax, fix common errors, and ensure standards compliance without requiring external network calls.

**IMPORTANT**: Tidy is designed exclusively for HTML and XHTML files. It cannot validate or process other file formats like PDF, Word documents, or plain text files.

## Installation

- **macOS**: `brew install tidy-html5`
- **Ubuntu/Debian**: `apt-get install tidy`
- **Windows**: Download from <https://www.html-tidy.org/>

## Capabilities

- HTML syntax validation
- XHTML validation
- HTML cleanup and formatting
- Error reporting and warnings
- Standards compliance checking
- Automatic fixing of common HTML issues

## Common Usage Patterns

### Clean HTML in Place (Recommended)

```bash
tidy -q -m {{INPUT_FILE}}
```

- `-q`: Quiet mode (suppress verbose messages)
- `-m`: Modify file in place
- **Fixes common HTML issues automatically**

### Clean HTML to New File

```bash
tidy -q -o {{OUTPUT_FILE}} {{INPUT_FILE}}
```

- `-o`: Output cleaned HTML to new file
- Preserves original file

### Validate Only (No Changes)

```bash
tidy -q -e {{INPUT_FILE}}
```

- `-e`: Show only errors and warnings
- No modifications made to file

### Format HTML with Indentation

```bash
tidy -q --indent auto --wrap 80 -o {{OUTPUT_FILE}} {{INPUT_FILE}}
```

- `--indent auto`: Auto-indent HTML for readability
- `--wrap 80`: Wrap lines at 80 characters

## Canonical command templates (planner-safe)

| id                | description                          | template |
|-------------------|--------------------------------------|----------|
| `tidy_clean_inplace` | Clean HTML file in place          | `tidy -q -m "{{INPUT_FILE}}"` |
| `tidy_clean_output` | Clean HTML to new file             | `tidy -q -o "{{OUTPUT_FILE}}" "{{INPUT_FILE}}"` |
| `tidy_validate_only` | Validate without changes           | `tidy -q -e "{{INPUT_FILE}}"` |
| `tidy_format_pretty` | Clean and format with indentation | `tidy -q --indent auto --wrap 80 -o "{{OUTPUT_FILE}}" "{{INPUT_FILE}}"` |

**Planner guidance**

- **Use Tidy to automatically fix and format HTML content** before conversion to Markdown or final output.
- **For instance, after LibreOffice produces HTML or after Pandoc** (if Pandoc produced HTML as an intermediate), run tidy -q -m {{INPUT_FILE}} to quietly clean the file in place.
- **The prompt template should use -q (quiet)** to suppress verbose messages and either -m to modify in place or -o {{OUTPUT_FILE}} to write cleaned output to a new file.
- **Tidy will correct common issues** (unclosed tags, bad nesting) and can also pretty-print the HTML.
- **Check Tidy's exit code**: 0 means no errors, 1 means warnings, 2 means errors were found. In automated chaining, treat exit code 2 as an indicator that the HTML had issues (even if Tidy fixed them).
- **After running Tidy, it's often useful to re-run HTMLHint** to ensure no errors remain.
- **Tidy is aggressive and may drop unknown elements or complex CSS**, so use it primarily on HTML that is purely for structural conversion.

## Output Formats

- Error reports (stderr)
- Cleaned HTML (stdout or file)
- **Exit codes**: 0 = no errors, 1 = warnings, 2 = errors found

## Security Considerations

- ✅ Local processing only
- ✅ No network access required
- ✅ Safe for sensitive documents
- ✅ No data transmission to external services

## Performance

- **Speed**: Very fast for local validation and cleanup
- **Memory**: Low memory usage
- **File Size**: Handles large HTML files efficiently

## Integration Notes

- **HTML cleanup pipeline**: Use after LibreOffice HTML conversion or other tools that produce verbose HTML
- **Exit code interpretation**: 0 = clean, 1 = warnings (usually acceptable), 2 = errors found but likely fixed
- **Follow-up validation**: Run HTMLHint after Tidy to verify cleanup was successful
- **Aggressive cleaning**: May drop unknown elements or complex CSS - use for structural conversion only

## Best Practices

1. **Use `-q` flag** to suppress verbose output in automated pipelines
2. **Use `-m` for in-place cleaning** or `-o` for new file output
3. **Check exit codes** for validation results (0=clean, 1=warnings, 2=errors)
4. **Follow with HTMLHint** to verify cleanup was successful
5. **Use primarily for structural HTML** that will be converted to other formats
6. **Combine with other validators** for comprehensive checking

## When to Use vs When NOT to Use

### When to Use

- **After LibreOffice HTML conversion** to clean verbose output
- **Before Pandoc HTML→Markdown conversion** to ensure clean input
- **Fixing structural HTML issues** automatically
- When you need **automatic HTML cleanup** without manual intervention
- **After any tool that produces potentially malformed HTML**

### When NOT to Use

- **On complex CSS or JavaScript-heavy HTML** (may drop important elements)
- When preserving exact HTML structure is critical
- **For non-HTML content** (Tidy only works with HTML/XHTML)
- When you only need validation without changes (use HTMLHint instead)

## Sample step emitted by planner

```bash
# id: clean_html_output
tidy -q -m "{{INPUT_FILE}}"
# follow with: htmlhint --format json "{{INPUT_FILE}}" > "$TEMP_DIR/validation.json"
# then: pandoc --from=html --to=gfm "{{INPUT_FILE}}" -o "{{OUTPUT_FILE}}"
```

By cleaning HTML, you improve Markdown conversion fidelity (Pandoc will get well-formed input) and reduce the chance of broken Markdown.
