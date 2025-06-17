# Template Debugging Guide

This guide covers ostruct's comprehensive template debugging capabilities for development and troubleshooting.

## Quick Start

```bash
# Show expanded template content only (clean output)
ostruct run template.j2 schema.json --show-templates -f config.yaml

# Debug everything (verbose logging + template expansion + context)
ostruct run template.j2 schema.json --debug -f config.yaml

# Get debugging help and examples
ostruct run template.j2 schema.json --help-debug
```

## Basic Template Debugging

### 🐛 Full Debug Mode (`--debug`)

Shows everything: template expansion, variable context, internal processing, and optimization details.

```bash
ostruct run prompt.j2 schema.json --debug -f config.yaml -f data.json
```

**When to use**: Initial debugging when you're not sure what's wrong.

### 📝 Template Display (`--show-templates`)

Shows only the expanded template content in clean format.

```bash
ostruct run prompt.j2 schema.json --show-templates -f config.yaml
```

**When to use**: When you want to see the final template without debug noise.

### 📋 Variable Context Inspection

#### Basic Context (`--show-context`)

Shows summary of all template variables organized by type:

```bash
ostruct run prompt.j2 schema.json --show-context -f config.yaml -f data.json
```

**Output example**:

```
📋 Template Context Summary:
FILES (2):
  config_yaml: config.yaml (1.2KB, 45 lines)
  data_json: data.json (856B, 23 lines)

STRINGS (1):
  current_model: "gpt-4"

OBJECTS (1):
  user_data: <dict with 5 keys>
```

#### Detailed Context (`--show-context-detailed`)

Shows content previews and detailed metadata:

```bash
ostruct run prompt.j2 schema.json --show-context-detailed -f config.yaml
```

**When to use**:

- Debugging undefined variable errors
- Understanding what data is available in templates
- Verifying file content is loaded correctly

### 🔍 Step-by-Step Template Expansion (`--debug-templates`)

Shows detailed template processing with 3 expansion steps:

```bash
ostruct run prompt.j2 schema.json --debug-templates -f config.yaml
```

**When to use**: Understanding how complex templates with loops and conditionals are processed.

## Optimization Debugging

### 🔧 Pre-Optimization Display (`--show-pre-optimization`)

Shows the template content before any optimization is applied:

```bash
ostruct run prompt.j2 schema.json --show-pre-optimization -f large_file.txt
```

**When to use**: Comparing what you wrote vs. what gets optimized.

### 🔄 Optimization Difference (`--show-optimization-diff`)

Shows line-by-line changes made by the optimizer:

```bash
ostruct run prompt.j2 schema.json --show-optimization-diff -f large_file.txt
```

**Output example**:

```
📊 Optimization Results:

Original: 25 lines, 867 chars
Optimized: 31 lines, 1024 chars

Changes:
  Line 5:
    - {{ large_file_txt.content }}
    + the files and subdirectories in <dir:large_file_txt>
  Line 28:
    + ==========================================
  Line 29:
    + APPENDIX: Referenced Files and Directories
  Line 30:
    + ==========================================
```

**When to use**: Understanding what the optimizer changed and why.

### ⚡ Skip Optimization (`--no-optimization`)

Completely bypasses template optimization:

```bash
ostruct run prompt.j2 schema.json --no-optimization -f large_file.txt
```

**When to use**:

- Testing if optimization is causing issues
- Working with templates that shouldn't be optimized
- Performance testing

### 🔧 Step-by-Step Optimization (`--show-optimization-steps`)

Shows detailed tracking of each optimization step:

```bash
ostruct run prompt.j2 schema.json --show-optimization-steps -f config.yaml -f data.json
```

**Output example**:

```
🔧 Optimization Step Tracking:

Step 1: Initial template loaded
  Characters: 0 → 1091 (+1091)
  Description: Starting optimization process with original template

Step 2: Directory reference optimization
  Characters: 1091 → 1307 (+216)
  Description: Moved 2 directory references to appendix format

Step 3: Appendix generation
  Characters: 1307 → 1708 (+401)
  Description: Built structured appendix with moved content references
```

#### Detailed Step Tracking (`--optimization-step-detail detailed`)

Shows full before/after content for each step:

```bash
ostruct run prompt.j2 schema.json --show-optimization-steps --optimization-step-detail detailed -f data.json
```

**When to use**: Deep debugging of optimization logic issues.

## Common Debugging Scenarios

### Scenario 1: Undefined Variable Error

**Error**: `UndefinedError: 'config_data' is undefined`

**Debug steps**:

1. **Check available variables**:

   ```bash
   ostruct run prompt.j2 schema.json --show-context -f config.yaml
   ```

2. **Verify file routing**:

   ```bash
   ostruct run prompt.j2 schema.json --debug -f config.yaml
   ```

3. **Check variable name in template**: Look for typos in `{{ config_data }}` vs available variables.

### Scenario 2: Template Not Expanding Properly

**Symptoms**: Template shows `{{ variable }}` in output instead of content.

**Debug steps**:

1. **View template expansion**:

   ```bash
   ostruct run prompt.j2 schema.json --show-templates -f config.yaml
   ```

2. **Check for syntax errors**:

   ```bash
   ostruct run prompt.j2 schema.json --debug-templates -f config.yaml
   ```

3. **Verify file content loading**:

   ```bash
   ostruct run prompt.j2 schema.json --show-context-detailed -f config.yaml
   ```

### Scenario 3: Optimization Breaking Template

**Symptoms**: Template works with `--no-optimization` but fails normally.

**Debug steps**:

1. **Compare before/after**:

   ```bash
   ostruct run prompt.j2 schema.json --show-optimization-diff -f large_file.txt
   ```

2. **Check step-by-step changes**:

   ```bash
   ostruct run prompt.j2 schema.json --show-optimization-steps -f large_file.txt
   ```

3. **Test without optimization**:

   ```bash
   ostruct run prompt.j2 schema.json --no-optimization -f large_file.txt
   ```

### Scenario 4: Performance Issues

**Debug steps**:

1. **Check optimization impact**:

   ```bash
   ostruct run prompt.j2 schema.json --show-optimization-diff -f large_file.txt
   ```

2. **Profile template expansion**:

   ```bash
   ostruct run prompt.j2 schema.json --debug-templates -f large_file.txt
   ```

3. **Test with minimal context**:

   ```bash
   ostruct run prompt.j2 schema.json --debug --attach simple_var "test content"
   ```

## Combining Debug Features

You can combine multiple debugging flags for comprehensive analysis:

```bash
# Show everything: context + templates + optimization changes
ostruct run prompt.j2 schema.json \
  --show-context \
  --show-templates \
  --show-optimization-diff \
  -f config.yaml -f data.json

# Deep debugging: all expansion details + optimization steps
ostruct run prompt.j2 schema.json \
  --debug-templates \
  --show-optimization-steps \
  --optimization-step-detail detailed \
  -f config.yaml

# Clean comparison: pre-optimization vs optimized
ostruct run prompt.j2 schema.json \
  --show-pre-optimization \
  --show-optimization-diff \
  -f large_file.txt
```

## Performance Considerations

- **Debug flags add minimal overhead** when not used
- **`--debug`** has the most impact due to verbose logging
- **`--show-templates`** is the lightest debugging option
- **Step tracking** only activates when optimization occurs
- **Context inspection** caches results for repeated access

## Best Practices

### For Development

1. Start with `--show-templates` to see basic expansion
2. Add `--show-context` when debugging variables
3. Use `--debug` for comprehensive troubleshooting
4. Use `--help-debug` for quick reference

### For Template Optimization

1. Always check `--show-optimization-diff` for large files
2. Use `--no-optimization` to test original templates
3. Track steps with `--show-optimization-steps` for complex cases
4. Combine with `--show-pre-optimization` for full visibility

### For Troubleshooting

1. **Undefined variables**: `--show-context` → `--show-context-detailed`
2. **Template syntax**: `--debug-templates` → `--debug`
3. **Optimization issues**: `--show-optimization-diff` → `--no-optimization`
4. **Performance**: `--show-optimization-steps` → profile individual steps

## Pro Tips

### 🎯 Quick Debugging Workflow

```bash
# 1. Quick check - is the template expanding?
ostruct run prompt.j2 schema.json --show-templates -f config.yaml

# 2. Variables missing? Check context
ostruct run prompt.j2 schema.json --show-context -f config.yaml

# 3. Still issues? Full debug
ostruct run prompt.j2 schema.json --debug -f config.yaml

# 4. Optimization problems? Compare
ostruct run prompt.j2 schema.json --show-optimization-diff -f config.yaml
```

### 🔧 Development Aliases

Add these to your shell profile for faster debugging:

```bash
alias tm-debug='ostruct run --debug --show-context'
alias tm-show='ostruct run --show-templates'
alias tm-opt='ostruct run --show-optimization-diff'
alias tm-help='ostruct run --help-debug'
```

### 📊 Template Quality Checks

Before using templates in production:

```bash
# Check optimization impact
ostruct run prompt.j2 schema.json --show-optimization-diff -f large_file.txt

# Verify all variables resolve
ostruct run prompt.j2 schema.json --show-context-detailed -f all_files.txt

# Test edge cases
ostruct run prompt.j2 schema.json --debug-templates -f edge_case.yaml
```

## Getting Help

- **CLI Help**: `ostruct run --help-debug` - Comprehensive debugging reference
- **General Help**: `ostruct run --help` - All CLI options
- **This Guide**: Complete debugging workflows and examples
- **Task Documentation**: `docs/dev/TEMPLATE_DEBUG_TASKS.md` - Implementation details
