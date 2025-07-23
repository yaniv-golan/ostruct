# Template Troubleshooting Guide

This guide helps you diagnose and fix common template issues using ostruct's debugging features.

## 🔄 File Download Migration (v0.8.1+)

### Template Migration for Code Interpreter File Downloads

If you're updating templates that use Code Interpreter file downloads, follow this migration guide:

#### Before (Old Format)

```jinja2
# Old template format - DON'T USE
Return your analysis as JSON with this structure:
{
  "analysis": "...",
  "download_link": "link_to_file"
}
```

```json
// Old schema - DON'T USE
{
  "type": "object",
  "properties": {
    "analysis": {"type": "string"},
    "download_link": {"type": "string"}
  }
}
```

#### After (New Format)

```jinja2
# New template format - USE THIS
Return your analysis in this exact format:

```json
{
  "analysis": "your analysis here"
}
```

filename.txt

```

```json
// New schema - USE THIS
{
  "type": "object",
  "properties": {
    "analysis": {"type": "string"}
  },
  "additionalProperties": false
}
```

#### Key Changes

1. **Remove `download_link` from JSON schema** - Files are now downloaded via annotations
2. **Use fenced JSON blocks** - Wrap JSON in ````json ...````
3. **Place markdown link outside JSON** - Link must be plain text after the JSON block
4. **Let ostruct handle downloads** - File downloads are automatic when Code Interpreter generates files

#### Troubleshooting File Downloads

**Files not downloading?**

1. **Check template format**:

   ```bash
   ostruct run template.j2 schema.json --debug --template-debug post-expand
   ```

   Verify the template instructs fenced JSON + markdown link

2. **Check model response**:

   ```bash
   ostruct run template.j2 schema.json --debug
   ```

   Look for "markdown_text" in debug output

3. **Check annotations**:

   ```bash
   ostruct run template.j2 schema.json --debug
   ```

   Look for "container_file_citation" annotations in logs

**Common Issues:**

- **Markdown link inside JSON** → Move link outside JSON block
- **No fenced JSON** → Wrap JSON in ````json ...````
- **Manual link formatting** → ostruct handles file downloads automatically
- **Model doesn't follow instructions** → Try different model (GPT-4o-mini works well)

#### File Conflict Resolution

**Files being overwritten?**

Use the `--ci-duplicate-outputs` flag to control behavior:

```bash
# Generate unique names for duplicate files
ostruct run template.j2 schema.json --file ci:data data.csv --ci-duplicate-outputs rename

# Skip files that already exist
ostruct run template.j2 schema.json --file ci:data data.csv --ci-duplicate-outputs skip

# Overwrite existing files (default)
ostruct run template.j2 schema.json --file ci:data data.csv --ci-duplicate-outputs overwrite
```

Or configure permanently in `ostruct.yaml`:

```yaml
tools:
  code_interpreter:
    duplicate_outputs: "rename"  # overwrite|rename|skip
```

## Quick Diagnostic Checklist

When encountering template issues, follow this checklist:

1. **File downloads not working?** → [File Download Migration](#file-download-migration-v081)
2. **Template not expanding?** → [Template Expansion Issues](#template-expansion-issues)
3. **Undefined variable errors?** → [Undefined Variable Errors](#undefined-variable-errors)
4. **Syntax errors?** → [Jinja2 Syntax Errors](#jinja2-syntax-errors)
5. **Optimization problems?** → [Optimization Issues](#optimization-issues)
6. **Performance issues?** → [Performance Problems](#performance-problems)

## Template Expansion Issues

### Symptoms

- Template shows `{{ variable }}` in output instead of content
- Template appears unchanged after processing
- No variables are being substituted

### Diagnostic Steps

#### 1. Check Template Syntax

```bash
ostruct run template.j2 schema.json --template-debug steps --file config config.yaml
```

**Look for**:

- Jinja2 parsing errors
- Invalid template syntax
- Unclosed blocks or braces

#### 2. Verify Template Content

```bash
ostruct run template.j2 schema.json --template-debug post-expand --file config config.yaml
```

**Expected**: Should show expanded template content, not raw template.

#### 3. Check Debug Output

```bash
ostruct run template.j2 schema.json --debug --file config config.yaml
```

**Look for**:

- Template loading messages
- Expansion step details
- Any error messages in logs

### Common Causes & Solutions

| Problem | Cause | Solution |
|---------|-------|----------|
| No expansion | Invalid Jinja2 syntax | Fix template syntax errors |
| Partial expansion | Mixed valid/invalid syntax | Use `--template-debug steps` to find errors |
| Wrong output | Template logic errors | Review conditionals and loops |

## Undefined Variable Errors

### Symptoms

```
UndefinedError: 'variable_name' is undefined
```

### Diagnostic Steps

#### 1. List Available Variables

```bash
ostruct run template.j2 schema.json --template-debug vars --file config config.yaml
```

**Check**:

- Are the expected variables listed?
- Are variable names spelled correctly?
- Are files being loaded properly?

#### 2. Detailed Variable Inspection

```bash
ostruct run template.j2 schema.json --template-debug vars,preview --file config config.yaml
```

**Look for**:

- File loading errors
- Content preview to verify data
- Variable types and attributes

#### 3. Debug File Loading

```bash
ostruct run template.j2 schema.json --debug --file config config.yaml
```

**Check logs for**:

- File routing messages
- Content loading confirmation
- Any file access errors

### Common Variable Issues

#### Issue: Typo in Variable Name

```jinja2
# Wrong
{{ config_flie.content }}

# Correct
{{ config_file.content }}
```

**Debug**: Use `--template-debug vars` to see actual variable names.

#### Issue: Wrong File Routing

```bash
# Wrong: Using generic -f flag (deprecated)
ostruct run template.j2 schema.json -f config.yaml

# Correct: Using explicit file routing
ostruct run template.j2 schema.json --file config_file config.yaml
```

**Debug**: Check that file routing creates the expected variable name.

#### Issue: Accessing Non-existent Attributes

```jinja2
# Wrong
{{ files.count }}

# Correct
{{ files | length }}
```

**Debug**: Use `--template-debug vars,preview` to see available attributes.

#### Issue: Loop Variable Scope

```jinja2
# Wrong - 'file' undefined outside loop
{% for file in files %}
{{ file.name }}
{% endfor %}
Last file: {{ file.name }}

# Correct - store in outer scope
{% set last_file = none %}
{% for file in files %}
{{ file.name }}
{% set last_file = file %}
{% endfor %}
Last file: {{ last_file.name if last_file }}
```

## Jinja2 Syntax Errors

### Common Syntax Issues

#### 1. Unclosed Braces/Blocks

```jinja2
# Wrong
{{ variable }
{% if condition %}
  content
# Missing {% endif %}

# Correct
{{ variable }}
{% if condition %}
  content
{% endif %}
```

**Debug**: Use `--template-debug steps` to see parsing errors.

#### 2. Invalid Filter Syntax

```jinja2
# Wrong
{{ text | len() }}

# Correct
{{ text | length }}
```

**Debug**: Check Jinja2 filter documentation for correct names.

#### 3. Block Nesting Errors

```jinja2
# Wrong
{% for item in items %}
  {% if item.active %}
    {{ item.name }}
  {% endfor %}  <!-- Should be {% endif %} -->
{% endfor %}

# Correct
{% for item in items %}
  {% if item.active %}
    {{ item.name }}
  {% endif %}
{% endfor %}
```

#### 4. String Quoting Issues

```jinja2
# Wrong
{% set message = Hello World %}

# Correct
{% set message = "Hello World" %}
```

### Debugging Syntax Errors

1. **Use detailed template expansion**:

   ```bash
   ostruct run template.j2 schema.json --template-debug steps --file config config.yaml
   ```

2. **Check specific error messages** in the output

3. **Use a Jinja2 syntax validator** online if needed

4. **Break down complex templates** into smaller parts for testing

## File Content Display Issues

### Symptoms

- Template shows `FileInfoList(['filename'])` instead of file content
- File content appears as object representation instead of actual content

### Diagnostic Steps

#### 1. Check File Content Access

```bash
ostruct run template.j2 schema.json --template-debug vars,preview --file data file.txt
```

**Look for**:

- How file variables are being accessed
- Whether `.content` property is being used
- File variable types and available properties

#### 2. Test Template Expansion

```bash
ostruct run template.j2 schema.json --template-debug steps --file data file.txt
```

**Check for**:

- Proper variable expansion
- Template syntax errors
- Variable access patterns

### Common File Content Problems

#### Issue: FileInfoList Shows Instead of Content

**Symptoms**: Template shows `FileInfoList(['filename'])` instead of file content.

**Debug**: Check if you're using `{{ variable }}` instead of `{{ variable.content }}`.

**Solution**: Always use `.content` to access file content:

- ✅ Correct: `{{ my_file.content }}`
- ❌ Wrong: `{{ my_file }}`

#### Issue: File Variable Undefined

**Symptoms**: Template fails with undefined variable errors.

**Debug**: Check file routing and variable naming.

**Solution**: Use proper file attachment flags and verify variable names.

## Performance Problems

### Symptoms

- Slow template rendering
- High memory usage during processing
- Timeouts with large templates

### Diagnostic Steps

#### 1. Profile Template Processing

```bash
time ostruct run template.j2 schema.json --debug --file large large_file.txt
```

#### 2. Test Template Complexity

```bash
ostruct run template.j2 schema.json --template-debug steps --file large large_file.txt
```

### Performance Solutions

#### Large Files

- Use explicit file routing (`--file alias`, `--dir alias`) instead of generic `-f`
- Consider breaking large files into smaller pieces
- Use file content selectively (e.g., `{{ file.content | truncate(1000) }}`)

#### Complex Templates

- Reduce nested loops and conditionals
- Use template includes for reusable components
- Cache expensive operations in variables

#### Many Variables

- Use `--template-debug vars` to verify only needed variables are loaded
- Remove unused file references
- Use selective file loading

## Error Pattern Reference

### Template Errors

| Error Message | Cause | Debug Command | Solution |
|---------------|-------|---------------|----------|
| `UndefinedError: 'var' is undefined` | Missing variable | `--template-debug vars` | Add variable or fix typo |
| `TemplateSyntaxError` | Invalid Jinja2 syntax | `--template-debug steps` | Fix template syntax |
| `TemplateNotFound` | Missing template file | `--debug` | Check file path |
| `FilterArgumentError` | Wrong filter usage | `--template-debug steps` | Fix filter syntax |
| `FileInfoList(['path'])` in output | Using `{{ var }}` instead of `{{ var.content }}` | `--template-debug steps` | Use `.content` to access file content |

### File Loading Errors

| Error Message | Cause | Debug Command | Solution |
|---------------|-------|---------------|----------|
| `FileNotFoundError` | Missing input file | `--debug` | Check file path |
| `PermissionError` | No file access | `--debug` | Fix file permissions |
| `UnicodeDecodeError` | Binary file as text | `--template-debug vars,preview` | Use correct file type |

## Emergency Debugging Workflow

When nothing else works, follow this step-by-step process:

### 1. Isolate the Problem

```bash
# Minimal test
ostruct run simple_template.j2 schema.json --attach test_var "hello world"
```

### 2. Add Complexity Gradually

```bash
# Add one file
ostruct run template.j2 schema.json --attach config config.yaml

# Add more files
ostruct run template.j2 schema.json --attach config config.yaml --attach data data.json

# Use full template
ostruct run template.j2 schema.json --file config config.yaml --file data data.json
```

### 3. Enable Full Debugging

```bash
ostruct run template.j2 schema.json --debug --template-debug vars,preview --file config config.yaml
```

### 4. Test Template Expansion

```bash
# Test template expansion steps
ostruct run template.j2 schema.json --template-debug steps --file config config.yaml

# Test with dry run
ostruct run template.j2 schema.json --dry-run --template-debug post-expand --file config config.yaml
```

### 5. Get Help

```bash
# Show debug help
ostruct run template.j2 schema.json --help-debug

# Check available options
ostruct run --help
```

## Known Issues

### OpenAI API Limitations

- **File Search Empty Results**: The OpenAI Responses API `file_search` tool currently has a known issue where it returns empty results despite successful vector store creation. This affects all models and is an upstream OpenAI API bug. See [known-issues/2025-07-openai-file-search-empty-results.md](known-issues/2025-07-openai-file-search-empty-results.md) for detailed information and community reports.

## Getting Support

If you've followed this troubleshooting guide and still have issues:

1. **Gather debug information**:

   ```bash
   ostruct run template.j2 schema.json --debug --template-debug vars --file config file.yaml > debug_output.txt 2>&1
   ```

2. **Create minimal reproduction case**:
   - Simplest template that shows the issue
   - Minimal input files
   - Exact command that fails

3. **Include version information**:

   ```bash
   ostruct --version
   python --version
   ```

4. **Check documentation**:
   - Main debugging guide: `docs/template_debugging.md`
   - Examples: `examples/debugging/`
   - Task details: `docs/dev/TEMPLATE_DEBUG_TASKS.md`
