# Template Debugging Guide

This guide covers ostruct's comprehensive template debugging capabilities for development and troubleshooting.

## Quick Start

```bash
# Show expanded template content only (clean output)
ostruct run template.j2 schema.json --template-debug post-expand --file config config.yaml

# Show all debugging information
ostruct run template.j2 schema.json -t all --file config config.yaml

# Show specific debugging capacities
ostruct run template.j2 schema.json -t vars,preview,steps --file config config.yaml

# Get debugging help and examples
ostruct run template.j2 schema.json --help-debug
```

## Template Debug Capacities

The new `--template-debug` (or `-t`) option uses **capacities** to control exactly what debugging information you see:

| Capacity | Purpose | Output Prefix | Description |
|----------|---------|---------------|-------------|
| `pre-expand` | Original template | `[PRE]` | Raw template before processing |
| `vars` | Variable summary | `[VARS]` | Variable names and types |
| `preview` | Variable content | `[PREVIEW]` | Content previews of variables |
| `optimization` | Optimization diff | `[OPTIM]` | Before/after optimization comparison |
| `optimization-steps` | Optimization steps | `[OPTIM-STEP]` | Detailed optimization tracking |
| `steps` | Template expansion | `[STEP]` | Jinja expansion trace |
| `post-expand` | Final prompts | `[TPL]` | Final prompts sent to API |

### Basic Usage

```bash
# Show just variable information
ostruct run template.j2 schema.json -t vars

# Show variables and content previews
ostruct run template.j2 schema.json -t vars,preview

# Show everything (equivalent to bare -t)
ostruct run template.j2 schema.json -t all
ostruct run template.j2 schema.json -t  # bare flag = all capacities
```

## Basic Template Debugging

### 🐛 Full Debug Mode (`--debug`)

Shows everything: template expansion, variable context, internal processing, and optimization details.

```bash
ostruct run prompt.j2 schema.json --debug --file config config.yaml --file data data.json
```

**When to use**: Initial debugging when you're not sure what's wrong.

### 📝 Template Display (`--template-debug post-expand`)

Shows only the expanded template content in clean format.

```bash
ostruct run prompt.j2 schema.json --template-debug post-expand --file config config.yaml
```

**When to use**: When you want to see the final template without debug noise.

### 📋 Variable Context Inspection

#### Basic Context (`--template-debug vars`)

Shows summary of all template variables organized by type:

```bash
ostruct run prompt.j2 schema.json --template-debug vars --file config config.yaml --file data data.json
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

#### Detailed Context (`--template-debug vars,preview`)

Shows content previews and detailed metadata:

```bash
ostruct run prompt.j2 schema.json --template-debug vars,preview --file config config.yaml
```

**When to use**:

- Debugging undefined variable errors
- Understanding what data is available in templates
- Verifying file content is loaded correctly

### 🔍 Step-by-Step Template Expansion (`--template-debug steps`)

Shows detailed template processing with 3 expansion steps:

```bash
ostruct run prompt.j2 schema.json --template-debug steps --file config config.yaml
```

**When to use**: Understanding how complex templates with loops and conditionals are processed.

## Optimization Debugging

### 🔧 Pre-Optimization Display (`--template-debug pre-expand`)

Shows the template content before any optimization is applied:

```bash
ostruct run prompt.j2 schema.json --template-debug pre-expand --file large large_file.txt
```

**When to use**: Comparing what you wrote vs. what gets optimized.

### 🔄 Optimization Difference (`--template-debug optimization`)

Shows line-by-line changes made by the optimizer:

```bash
ostruct run prompt.j2 schema.json --template-debug optimization --file large large_file.txt
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
ostruct run prompt.j2 schema.json --no-optimization --file large large_file.txt
```

**When to use**:

- Testing if optimization is causing issues
- Working with templates that shouldn't be optimized
- Performance testing

### 🔧 Step-by-Step Optimization (`--template-debug optimization-steps`)

Shows detailed tracking of each optimization step:

```bash
ostruct run prompt.j2 schema.json --template-debug optimization-steps --file config config.yaml --file data data.json
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

#### Detailed Step Tracking (`--template-debug optimization-steps`)

Shows full before/after content for each step:

```bash
ostruct run prompt.j2 schema.json --template-debug optimization-steps --file data data.json
```

**When to use**: Deep debugging of optimization logic issues.

## File Reference Debugging

### 📁 File Reference Operations (`--template-debug post-expand`)

Shows file reference registration and usage tracking:

```bash
ostruct run template.j2 schema.json --template-debug post-expand --dir source src/ --file config config.yaml
```

**Debug output shows**:

- **Alias Registration**: When files are grouped by their CLI aliases
- **Reference Tracking**: When `file_ref()` is called in templates
- **Appendix Generation**: When XML appendix is built for referenced files

**Example output**:

```
[DEBUG] File reference: Registered alias 'source' with 5 files from src/
[DEBUG] File reference: Registered alias 'config' with 1 file from config.yaml
[DEBUG] File reference: Referenced alias 'source' in template
[DEBUG] File reference: Referenced alias 'config' in template
[DEBUG] File reference: Building XML appendix with 2 aliases
```

### 🔍 File Reference Troubleshooting

#### Unknown Alias Errors

```bash
# Template uses {{ file_ref("missing") }} but alias not attached
ostruct run template.j2 schema.json --dir source src/
```

**Error output**:

```
Template Structure Error: Unknown alias 'missing' in file_ref()
Suggestions:
  • Available aliases: source
  • Check your --dir and --file attachments
```

#### No XML Appendix Generated

```bash
# Disable file references entirely for clean debugging
ostruct run template.j2 schema.json --dir source src/
```

**When to use**:

- Template uses `file_ref()` but no appendix appears
- Verifying which files are actually referenced
- Understanding file grouping by aliases

### 📋 File Reference Context

Use context debugging to see file attachment details:

```bash
ostruct run template.j2 schema.json --template-debug vars,preview --dir source src/ --file config config.yaml
```

**Shows**:

- File grouping by alias
- Attachment types (file, dir, collection)
- File paths and relative paths
- Content previews

**When to use**:

- Verifying files are attached correctly
- Understanding how aliases map to files
- Checking file content accessibility

## Common Debugging Scenarios

### Scenario 1: Undefined Variable Error

**Error**: `UndefinedError: 'config_data' is undefined`

**Debug steps**:

1. **Check available variables**:

   ```bash
   ostruct run prompt.j2 schema.json --template-debug vars --file config config.yaml
   ```

2. **Verify file routing**:

   ```bash
   ostruct run prompt.j2 schema.json --debug --file config config.yaml
   ```

3. **Check variable name in template**: Look for typos in `{{ config_data }}` vs available variables.

### Scenario 2: Template Not Expanding Properly

**Symptoms**: Template shows `{{ variable }}` in output instead of content.

**Debug steps**:

1. **View template expansion**:

   ```bash
   ostruct run prompt.j2 schema.json --template-debug post-expand --file config config.yaml
   ```

2. **Check for syntax errors**:

   ```bash
   ostruct run prompt.j2 schema.json --template-debug steps --file config config.yaml
   ```

3. **Verify file content loading**:

   ```bash
   ostruct run prompt.j2 schema.json --template-debug vars,preview --file config config.yaml
   ```

### Scenario 3: Optimization Breaking Template

**Symptoms**: Template works with `--no-optimization` but fails normally.

**Debug steps**:

1. **Compare before/after**:

   ```bash
   ostruct run prompt.j2 schema.json --template-debug optimization --file large large_file.txt
   ```

2. **Check step-by-step changes**:

   ```bash
   ostruct run prompt.j2 schema.json --template-debug optimization-steps --file large large_file.txt
   ```

3. **Test without optimization**:

   ```bash
   ostruct run prompt.j2 schema.json --no-optimization --file large large_file.txt
   ```

### Scenario 4: Performance Issues

**Debug steps**:

1. **Check optimization impact**:

   ```bash
   ostruct run prompt.j2 schema.json --template-debug optimization --file large large_file.txt
   ```

2. **Profile template expansion**:

   ```bash
   ostruct run prompt.j2 schema.json --template-debug steps --file large large_file.txt
   ```

3. **Test with minimal context**:

   ```bash
   ostruct run prompt.j2 schema.json --debug --attach simple_var "test content"
   ```

## Combining Debug Features

You can combine multiple debugging flags for comprehensive analysis:

```bash
# Show everything: context + expansion + optimization changes
ostruct run prompt.j2 schema.json \
  --template-debug vars,post-expand,optimization \
  --file config config.yaml --file data data.json

# Deep debugging: all expansion details + optimization steps
ostruct run prompt.j2 schema.json \
  --template-debug steps,optimization-steps \
  --file config config.yaml

# Clean comparison: pre-optimization vs optimized
ostruct run prompt.j2 schema.json \
  --template-debug pre-expand,optimization \
  --file large large_file.txt
```

## Performance Considerations

- **Debug flags add minimal overhead** when not used
- **`--debug`** has the most impact due to verbose logging
- **`--template-debug post-expand`** is the lightest debugging option
- **Step tracking** only activates when optimization occurs
- **Context inspection** caches results for repeated access

## Best Practices

### For Development

1. Start with `--template-debug post-expand` to see basic expansion
2. Add `--template-debug vars` when debugging variables
3. Use `--debug` for comprehensive troubleshooting
4. Use `--help` for quick reference

### For Template Optimization

1. Always check `--template-debug optimization` for large files
2. Use `--no-optimization` to test original templates
3. Track steps with `--template-debug optimization-steps` for complex cases
4. Combine with `--template-debug pre-expand` for full visibility

### For Troubleshooting

1. **Undefined variables**: `--template-debug vars` → `--template-debug vars,preview`
2. **Template syntax**: `--template-debug steps` → `--debug`
3. **Optimization issues**: `--template-debug optimization` → `--no-optimization`
4. **Performance**: `--template-debug optimization-steps` → profile individual steps

## Pro Tips

### 🎯 Quick Debugging Workflow

```bash
# 1. Quick check - is the template expanding?
ostruct run prompt.j2 schema.json --template-debug post-expand --file config config.yaml

# 2. Variables missing? Check context
ostruct run prompt.j2 schema.json --template-debug vars --file config config.yaml

# 3. Still issues? Full debug
ostruct run prompt.j2 schema.json --debug --file config config.yaml

# 4. Optimization problems? Compare
ostruct run prompt.j2 schema.json --template-debug optimization --file config config.yaml
```

### 🔧 Development Aliases

Add these to your shell profile for faster debugging:

```bash
alias tm-debug='ostruct run --debug --template-debug vars'
alias tm-show='ostruct run --template-debug post-expand'
alias tm-opt='ostruct run --template-debug optimization'
alias tm-help='ostruct run --help'
```

### 📊 Template Quality Checks

Before using templates in production:

```bash
# Check optimization impact
ostruct run prompt.j2 schema.json --template-debug optimization --file large large_file.txt

# Verify all variables resolve
ostruct run prompt.j2 schema.json --template-debug vars,preview --file all all_files.txt

# Test edge cases
ostruct run prompt.j2 schema.json --template-debug steps --file edge edge_case.yaml
```

## Getting Help

- **CLI Help**: `ostruct run --help` - Comprehensive CLI reference
- **General Help**: `ostruct run --help` - All CLI options
- **This Guide**: Complete debugging workflows and examples
- **Task Documentation**: `docs/dev/TEMPLATE_DEBUG_TASKS.md` - Implementation details
