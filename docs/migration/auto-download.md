# Migrating from auto_download Config to --ci-download Flag

## What Changed

**Breaking Change**: Code Interpreter file downloads are now **disabled by default** for better performance and faster execution.

### Before (v0.x.x)

```yaml
# ostruct.yaml
tools:
  code_interpreter:
    auto_download: true  # Default behavior
```

```bash
# Files were downloaded automatically
ostruct run template.j2 schema.json --enable-tool code-interpreter
```

### After (v0.x.x+)

```yaml
# ostruct.yaml - no auto_download needed
tools:
  code_interpreter:
    output_directory: "./downloads"  # Optional: configure download location
```

```bash
# Explicit flag required for file downloads
ostruct run template.j2 schema.json --enable-tool code-interpreter --ci-download
```

## Why This Change?

1. **Performance**: Most Code Interpreter usage is for **computation** (analysis, calculations, data processing) where the JSON response contains the actual value, not generated files.

2. **Simplicity**: Eliminates the complex two-pass sentinel workaround by default, resulting in faster single-pass execution.

3. **Explicit Intent**: Users now explicitly opt-in to file downloads when needed, making the behavior predictable.

4. **API Reliability**: Avoids OpenAI API bugs related to structured output + file downloads unless explicitly needed.

## Migration Steps

### 1. Update Configuration Files

**Remove** the deprecated `auto_download` setting:

```yaml
# ❌ OLD - Remove this
tools:
  code_interpreter:
    auto_download: true
    output_directory: "./downloads"

# ✅ NEW - Keep only what you need
tools:
  code_interpreter:
    output_directory: "./downloads"  # Optional
```

### 2. Update CLI Commands

Add `--ci-download` flag to commands that need file downloads:

```bash
# ❌ OLD - Files downloaded automatically
ostruct run analysis.j2 schema.json --enable-tool code-interpreter

# ✅ NEW - Explicit flag for file downloads
ostruct run analysis.j2 schema.json --enable-tool code-interpreter --ci-download
```

### 3. Update Scripts and Automation

Update any shell scripts, CI/CD pipelines, or automation:

```bash
#!/bin/bash
# ❌ OLD
ostruct run template.j2 schema.json \
  --file ci:data dataset.csv \
  --enable-tool code-interpreter

# ✅ NEW - Add --ci-download for charts/visualizations
ostruct run template.j2 schema.json \
  --file ci:data dataset.csv \
  --enable-tool code-interpreter \
  --ci-download
```

### 4. Update Programmatic Usage

For Python scripts using subprocess:

```python
# ❌ OLD
cmd = [
    "ostruct", "run", "template.j2", "schema.json",
    "--enable-tool", "code-interpreter"
]

# ✅ NEW - Add --ci-download when files needed
cmd = [
    "ostruct", "run", "template.j2", "schema.json",
    "--enable-tool", "code-interpreter",
    "--ci-download"  # For charts, reports, data files
]
```

## When to Use --ci-download

### ✅ Use --ci-download when you need

- **Charts and visualizations** (PNG, SVG, PDF)
- **Generated reports** (HTML, CSV, Excel)
- **Processed data files** (cleaned datasets, exports)
- **Analysis artifacts** (models, outputs, summaries)

### ❌ Skip --ci-download when you only need

- **Statistical calculations** (returned in JSON)
- **Data analysis results** (metrics, insights in response)
- **Validation checks** (pass/fail, scores, recommendations)
- **Quick computations** (math, transformations, aggregations)

## Examples by Use Case

### Data Analysis (Usually needs --ci-download)

```bash
# Generates charts and visualizations
ostruct run analysis.j2 schema.json \
  --file ci:sales data.csv \
  --enable-tool code-interpreter \
  --ci-download
```

### Statistical Computation (Usually no --ci-download)

```bash
# Only returns calculated statistics in JSON
ostruct run stats.j2 schema.json \
  --file ci:data metrics.csv \
  --enable-tool code-interpreter
```

### Security Scanning (Usually no --ci-download)

```bash
# Returns vulnerability report in JSON
ostruct run security_audit.j2 schema.json \
  --file ci:code app.py \
  --enable-tool code-interpreter
```

## Backward Compatibility

During the transition period:

- **Deprecation Warning**: Existing `auto_download: true` configs will show a warning but continue to work
- **CLI Override**: `--ci-download` flag takes precedence over config settings
- **Legacy Support**: Old configs are honored until removed in a future version

## Troubleshooting

### "No files downloaded" after migration

**Solution**: Add `--ci-download` flag to your command.

### "Two-pass execution not triggered"

**Solution**: This is expected! Single-pass execution is now the default for better performance.

### Scripts failing after upgrade

**Solution**: Add `--ci-download` to any commands that generate files (charts, reports, data exports).

### Performance seems slower

**Solution**: If you're not using `--ci-download`, execution should be **faster**. Check if you have legacy `auto_download: true` config.

## Need Help?

- **Examples**: See updated examples in `examples/` directory
- **Documentation**: Check the CLI reference for all `--ci-*` options
- **Issues**: Report problems at <https://github.com/yaniv-golan/ostruct/issues>

This migration optimizes for the common case (computation over file generation) while maintaining full backward compatibility during the transition period.
