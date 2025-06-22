# Template Debugging Examples

This directory contains practical examples demonstrating ostruct's template debugging capabilities.

## Directory Structure

```
debugging/
├── README.md                    # This file
├── template-expansion/          # Basic debugging examples
│   ├── debug_template.j2       # Example template with various scenarios
│   ├── example_config.yaml     # Sample configuration file
│   └── sample_code.py          # Sample Python code for analysis
├── optimization-analysis/       # Optimization debugging examples
│   ├── large_template.j2       # Template that benefits from optimization
│   ├── before_optimization.md  # Expected output before optimization
│   └── after_optimization.md   # Expected output after optimization
└── troubleshooting/            # Common troubleshooting scenarios
    ├── undefined_variables.j2  # Template with undefined variable errors
    ├── syntax_errors.j2        # Template with Jinja2 syntax issues
    └── optimization_issues.j2  # Template with optimization problems
```

## Getting Started

### 1. Basic Template Debugging

Navigate to the template-expansion directory and try these commands:

```bash
cd examples/debugging/template-expansion

# Show basic template expansion
ostruct run debug_template.j2 test_schema.json --template-debug \
  --file config_yaml example_config.yaml \
  --file code_files sample_code.py \
  -V current_model="gpt-4" \
  -V timestamp="2025-01-24 10:30:00"

# Show context variables
ostruct run debug_template.j2 test_schema.json --show-context \
  --file config_yaml example_config.yaml \
  --file code_files sample_code.py \
  -V current_model="gpt-4"

# Full debugging (will show undefined variable error)
ostruct run debug_template.j2 test_schema.json --debug \
  --file config_yaml example_config.yaml \
  --file code_files sample_code.py \
  -V current_model="gpt-4" \
  -V timestamp="2025-01-24 10:30:00"
```

### 2. Context Inspection

```bash
# Basic context summary
ostruct run debug_template.j2 test_schema.json --show-context \
  --file config_yaml example_config.yaml \
  --file code_files sample_code.py \
  -V current_model="gpt-4"

# Detailed context with content previews
ostruct run debug_template.j2 test_schema.json --show-context-detailed \
  --file config_yaml example_config.yaml \
  --file code_files sample_code.py \
  -V current_model="gpt-4"
```

### 3. Template Expansion Steps

```bash
# Step-by-step template expansion
ostruct run debug_template.j2 test_schema.json --template-debug \
  --file config_yaml example_config.yaml \
  --file code_files sample_code.py \
  -V current_model="gpt-4" \
  -V timestamp="2025-01-24 10:30:00"
```

## Common Debugging Scenarios

### Scenario 1: Undefined Variable Error

The `debug_template.j2` includes an undefined variable `potentially_missing_var`. This demonstrates:

1. How undefined variables are detected
2. How to use `--show-context` to see available variables
3. How to fix undefined variable errors

**Try this:**

```bash
# This will fail with an undefined variable error
ostruct run debug_template.j2 test_schema.json --template-debug \
  --file config_yaml example_config.yaml \
  --file code_files sample_code.py \
  -V current_model="gpt-4"

# Debug by checking available context
ostruct run debug_template.j2 test_schema.json --show-context \
  --file config_yaml example_config.yaml \
  --file code_files sample_code.py \
  -V current_model="gpt-4"

# Fix by adding the missing variable
ostruct run debug_template.j2 test_schema.json --template-debug \
  --file config_yaml example_config.yaml \
  --file code_files sample_code.py \
  -V current_model="gpt-4" \
  -V potentially_missing_var="This variable is now defined!"
```

### Scenario 2: Complex Logic Debugging

The template includes loops and conditionals. Use step-by-step debugging:

```bash
# See how loops and conditionals are processed
ostruct run debug_template.j2 test_schema.json --template-debug \
  --file config_yaml example_config.yaml \
  --file code_files sample_code.py \
  -V current_model="gpt-4" \
  -V timestamp="2025-01-24 10:30:00"
```

### Scenario 3: File Content Analysis

The template processes file content. Debug file loading:

```bash
# Verify files are loaded correctly and see variable content
ostruct run debug_template.j2 test_schema.json --template-debug vars,preview \
  --file config_yaml example_config.yaml \
  --file code_files sample_code.py \
  -V current_model="gpt-4"

# See how file content is used in template
ostruct run debug_template.j2 test_schema.json --template-debug post-expand \
  --file config_yaml example_config.yaml \
  --file code_files sample_code.py \
  -V current_model="gpt-4" \
  -V timestamp="2025-01-24 10:30:00" \
  -V potentially_missing_var="Fixed!"
```

## File Reference System Debugging

### New File Reference Pattern

The templates now use `file_ref()` for cleaner syntax:

```bash
# Test file reference expansion
ostruct run debug_template.j2 test_schema.json --template-debug post-expand \
  --file config_yaml example_config.yaml \
  --file code_files sample_code.py

# See XML appendix generation
ostruct run debug_template.j2 test_schema.json --dry-run \
  --file config_yaml example_config.yaml \
  --file code_files sample_code.py
```

### File Routing Options

Test different file routing strategies:

```bash
# Template-only access (default)
ostruct run debug_template.j2 test_schema.json --dry-run \
  --file config_yaml example_config.yaml \
  --file code_files sample_code.py

# Code Interpreter access
ostruct run debug_template.j2 test_schema.json --dry-run \
  --file ci:config_yaml example_config.yaml \
  --file ci:code_files sample_code.py

# File Search access
ostruct run debug_template.j2 test_schema.json --dry-run \
  --file fs:config_yaml example_config.yaml \
  --file fs:code_files sample_code.py
```

## Template Debug Capacities

The `--template-debug` flag uses **capacities** to control exactly what debugging information you see:

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
ostruct run template.j2 schema.json --template-debug vars

# Show variables and content previews
ostruct run template.j2 schema.json --template-debug vars,preview

# Show final expanded template
ostruct run template.j2 schema.json --template-debug post-expand

# Show everything (equivalent to bare --template-debug)
ostruct run template.j2 schema.json --template-debug all
ostruct run template.j2 schema.json --template-debug  # bare flag = all capacities
```

### Practical Examples

```bash
# Debug undefined variables
ostruct run debug_template.j2 test_schema.json --template-debug vars,preview \
  --file config_yaml example_config.yaml \
  --file code_files sample_code.py

# See template expansion process
ostruct run debug_template.j2 test_schema.json --template-debug post-expand \
  --file config_yaml example_config.yaml \
  --file code_files sample_code.py

# Debug optimization issues
ostruct run large_template.j2 test_schema.json --template-debug optimization,optimization-steps \
  --file config config.yaml \
  --file source app.py
```

## Optimization Debugging Examples

### Large File Optimization

Test the migrated optimization template:

```bash
cd ../optimization-analysis

# Create test files (all 5 required by the template)
echo "config: value" > config.yaml
echo "print('hello')" > app.py
echo "# README" > README.md
echo "# Test file" > test.py
echo "version: '3.8'" > docker-compose.yml

# Test with file references (all 5 files required)
ostruct run large_template.j2 test_schema.json --dry-run \
  --file config config.yaml \
  --file source app.py \
  --file docs README.md \
  --file tests test.py \
  --file deployment docker-compose.yml

# See template expansion
ostruct run large_template.j2 test_schema.json --template-debug post-expand \
  --file config config.yaml \
  --file source app.py \
  --file docs README.md \
  --file tests test.py \
  --file deployment docker-compose.yml
```

## Troubleshooting Guide

### Problem: Template Not Expanding

**Symptoms**: Template shows `{{ variable }}` in output.

**Debug steps**:

1. Check template syntax: `--template-debug post-expand`
2. Verify variables exist: `--template-debug vars`
3. Look for typos in variable names

### Problem: Undefined Variable Errors

**Error**: `Missing required template variable: variable_name`

**Debug steps**:

1. List available variables: `--template-debug vars`
2. Check variable names for typos
3. Verify file routing is correct
4. Use `-V variable_name=value` to provide missing variables

### Problem: File Reference Issues

**Error**: `Unknown alias 'alias_name' in file_ref()`

**Debug steps**:

1. Check file attachment aliases match `file_ref()` calls
2. Verify files exist and are accessible
3. Use `--template-debug vars` to see available file aliases

### Problem: Safe Variable Access

**Symptoms**: Variables showing as "undefined" instead of defaults

**Debug steps**:

1. Use `safe_get('var_name', 'default')` instead of `{{ var_name | default('default') }}`
2. Check for typos in variable names
3. Verify variable is properly provided via `-V`

## Quick Reference Commands

```bash
# Basic debugging workflow
ostruct run template.j2 schema.json --template-debug post-expand --file alias file.yaml
ostruct run template.j2 schema.json --template-debug vars --file alias file.yaml
ostruct run template.j2 schema.json --debug --file alias file.yaml

# File reference debugging
ostruct run template.j2 schema.json --dry-run --file alias file.yaml
ostruct run template.j2 schema.json --template-debug post-expand --file alias file.yaml

# Variable debugging
ostruct run template.j2 schema.json --template-debug vars,preview -V var=value
ostruct run template.j2 schema.json --template-debug vars -V var=value

# Template debug capacities
ostruct run template.j2 schema.json --template-debug vars,preview,post-expand --file alias file.yaml
ostruct run template.j2 schema.json --template-debug all --file alias file.yaml
```

## Pro Tips

1. **Start simple**: Begin with `--template-debug` to see basic expansion
2. **Check context**: Use `--show-context` when debugging variables
3. **Use file references**: Prefer `file_ref()` over manual file iteration
4. **Safe variable access**: Use `safe_get()` for robust variable handling
5. **Test file routing**: Try different routing options (-f, -fc, -fs) for different use cases
6. **Dry run first**: Always test with `--dry-run` before live execution

## Migration Notes

### Updated Patterns

- **File Access**: `{{ file_ref("alias") }}` instead of `{% for file in alias %}{{ file.content }}{% endfor %}`
- **Variable Access**: `{{ safe_get('var', 'default') }}` instead of `{{ var | default('default') }}`
- **CLI Flags**: `--file alias file.txt` instead of `--ftl alias file.txt`

### Backwards Compatibility

- Old templates still work but are not recommended
- Use migration examples as reference for updating existing templates
- File reference system provides cleaner syntax and better performance

## Need Help?

- **CLI Help**: `ostruct run --help`
- **Documentation**: `docs/template_debugging.md`
- **Examples**: All examples in this directory demonstrate current best practices
