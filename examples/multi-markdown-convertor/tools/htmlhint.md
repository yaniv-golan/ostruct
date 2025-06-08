---
tool: htmlhint
kind: html-validator
tool_min_version: "1.0.0"
tool_version_check: "htmlhint --version"
recommended_output_format: json
installation:
  macos: "npm install -g htmlhint"
  ubuntu: "npm install -g htmlhint"
  windows: "npm install -g htmlhint"
---

# HTMLHint — Local HTML Linter

*Purpose in our pipeline*: after we render Markdown → HTML for QA, run **HTMLHint** to catch broken tags, missing `<title>`, invalid attributes, and common accessibility issues before final hand-off to users or LLM validation.

---

## Why HTMLHint vs. W3C validator?

| Criterion            | HTMLHint | W3C Online |
|----------------------|:--------:|:----------:|
| Offline / air-gapped | ✅       | ❌ (HTTP)  |
| Speed on large docs  | **ms**   | seconds    |
| Custom rule file     | `.htmlhintrc` | limited |
| Structured JSON out  | ✅       | ⚠︎ HTML only |

---

## Quick-start

```bash
# 1) Install once
npm install -g htmlhint

# 2) Validate and emit JSON (best for ostruct safety-check)
htmlhint --format json output/page.html > temp/htmlhint_page1.json
```

**Planner tip**: stick to --format json so downstream jq can count / filter issues.

⸻

## Canonical command templates (planner-safe)

| id | description | template |
|----|-------------|----------|
| `htmlhint_basic` | Basic validation with default rules | `htmlhint "{{INPUT_FILE}}"` |
| `htmlhint_json` | JSON output for machine processing | `htmlhint --format json "{{INPUT_FILE}}" > "{{OUTPUT_FILE}}"` |
| `htmlhint_rules` | Focus on critical conversion rules | `htmlhint --rules tag-pair,attr-lowercase,id-unique,src-not-empty "{{INPUT_FILE}}"` |
| `htmlhint_config` | Use project-specific config | `htmlhint --config .htmlhintrc --format json "{{INPUT_FILE}}" > "{{OUTPUT_FILE}}"` |

**Planner guidance**

* **Use HTMLHint after converting content to HTML** (e.g. after Markdown is rendered to HTML for preview, or after LibreOffice HTML output) to catch structural issues.
* **Always run it with the JSON output format** for machine-readable results: e.g. htmlhint --format json {{INPUT_FILE}} > {{OUTPUT_FILE}} so that the pipeline can parse the results.
* **The prompt should emphasize using --format json** (and possibly a custom .htmlhintrc config file) so that we can filter errors with tools like jq and not rely on just exit codes.
* **Focus on important rules**: for conversion, ensure rules like tag-pair (checks for unclosed tags), id-unique, attr-lowercase, src-not-empty, etc., are enabled, as these catch common conversion errors (e.g., dropped closing tags, duplicate IDs from headings, empty image links).
* **Note that HTMLHint's exit code is not simply "0 = no errors"** – it may always exit 0; you need to inspect the JSON for "error" entries.

⸻

## Key Rules We Care About

| Rule | Why we enable it in conversion QA |
|------|-----------------------------------|
| tag-pair | Detect dropped closing tags during Markdown→HTML |
| id-unique | Ensure no duplicate anchors when headings repeat |
| title-require | Force a `<title>` (helps SEO & a11y) |
| attr-lowercase | Normalise generated HTML attributes |
| src-not-empty | Captures bad image references after extraction |

⸻

## Integration Notes

* **Exit codes**: **HTMLHint's exit code is not simply "0 = no errors" – it may always exit 0; you need to inspect the JSON for "error" entries**. Therefore, the pipeline should interpret the JSON and decide if a fallback or fix is required (e.g. run Tidy to auto-fix, or alert an LLM to address issues).
* **Large files**: handles 5 MB+ HTML in under 200 ms on M-series CPU.
* **Config file**: commit a `.htmlhintrc` alongside docs to keep rules deterministic.
* **Use HTMLHint as a non-blocking checker**: it's there to guide cleanup (the prompt should clarify that it's for QA, not for conversion output).

```json
// ./config/htmlhintrc-strict.json (example)
{
  "tag-pair": true,
  "id-unique": true,
  "title-require": true,
  "attr-lowercase": true,
  "src-not-empty": true
}
```

Invoke with:

```bash
htmlhint --config config/htmlhintrc-strict.json --format json {{INPUT_FILE}} > {{OUTPUT_FILE}}
```

⸻

## Strengths & Limitations

| ✔︎ Strengths | ✖︎ Limitations |
|-------------|---------------|
| Fully offline, zero telemetry | Doesn't parse inline JS / Vue components thoroughly |
| Fast (< 1 ms per 1 K lines) | Cannot auto-fix – lint-only |
| JSON output for jq | HTML5-specific; XML/XHTML quirks may raise false positives |
| Catches common conversion errors | Exit codes don't reliably indicate errors |

⸻

## Security Considerations

* ✅ Local processing only
* ✅ No network access required
* ✅ Safe for sensitive documents
* ✅ Node.js based, no external dependencies

## Performance

* **Speed**: Very fast - < 1ms per 1K lines, handles 5MB+ HTML in under 200ms
* **Memory**: Low memory usage
* **File Size**: Handles large HTML files efficiently

## Best Practices

1. **Always use `--format json`** for machine-readable output that can be parsed by jq
2. **Use custom `.htmlhintrc` config file** to maintain consistent rules across project
3. **Focus on conversion-critical rules** like tag-pair, id-unique, src-not-empty
4. **Parse JSON output, don't rely on exit codes** to determine if errors exist
5. **Use as non-blocking QA step** to guide cleanup, not block conversion

## When to Use vs When NOT to Use

### When to Use

* **After converting content to HTML** (Markdown→HTML, LibreOffice→HTML)
* **Quality assurance** before final output
* **Catching structural issues** from conversion processes
* When you need **fast, offline HTML validation**

### When NOT to Use

* **For auto-fixing HTML** (use Tidy instead)
* When you need W3C-compliant validation
* For XML/XHTML validation (use xmllint)
* **As a blocking step** (treat as QA guidance only)

## Sample step emitted by planner

```bash
# id: html_qa_check
htmlhint --format json "{{INPUT_FILE}}" > "$TEMP_DIR/htmlhint_report.json"
# follow with: jq '.[] | select(.type=="error")' "$TEMP_DIR/htmlhint_report.json" | wc -l
# if errors > 0, consider running tidy to auto-fix
```

Use HTMLHint for QA guidance to improve HTML quality before final Markdown conversion.
