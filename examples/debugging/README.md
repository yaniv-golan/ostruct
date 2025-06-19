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
ostruct run debug_template.j2 ../../../schema.json --show-templates \
  --file config_yaml example_config.yaml \
  --ftl code_files sample_code.py \
  --file current_model "gpt-4" \
  --file timestamp "2025-01-24 10:30:00"

# Show context variables
ostruct run debug_template.j2 ../../../schema.json --show-context \
  --file config_yaml example_config.yaml \
  --ftl code_files sample_code.py \
  --file current_model "gpt-4"

# Full debugging (will show undefined variable error)
ostruct run debug_template.j2 ../../../schema.json --debug \
  --file config_yaml example_config.yaml \
  --ftl code_files sample_code.py \
  --file current_model "gpt-4" \
  --file timestamp "2025-01-24 10:30:00"
```

### 2. Context Inspection

```bash
# Basic context summary
ostruct run debug_template.j2 ../../../schema.json --show-context \
  --file config_yaml example_config.yaml \
  --ftl code_files sample_code.py \
  --file current_model "gpt-4"

# Detailed context with content previews
ostruct run debug_template.j2 ../../../schema.json --show-context-detailed \
  --file config_yaml example_config.yaml \
  --ftl code_files sample_code.py \
  --file current_model "gpt-4"
```

### 3. Template Expansion Steps

```bash
# Step-by-step template expansion
ostruct run debug_template.j2 ../../../schema.json --debug-templates \
  --file config_yaml example_config.yaml \
  --ftl code_files sample_code.py \
  --file current_model "gpt-4" \
  --file timestamp "2025-01-24 10:30:00"
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
ostruct run debug_template.j2 ../../../schema.json --show-templates \
  --file config_yaml example_config.yaml \
  --ftl code_files sample_code.py \
  --file current_model "gpt-4"

# Debug by checking available context
ostruct run debug_template.j2 ../../../schema.json --show-context \
  --file config_yaml example_config.yaml \
  --ftl code_files sample_code.py \
  --file current_model "gpt-4"

# Fix by adding the missing variable
ostruct run debug_template.j2 ../../../schema.json --show-templates \
  --file config_yaml example_config.yaml \
  --ftl code_files sample_code.py \
  --file current_model "gpt-4" \
  --file potentially_missing_var "This variable is now defined!"
```

### Scenario 2: Complex Logic Debugging

The template includes loops and conditionals. Use step-by-step debugging:

```bash
# See how loops and conditionals are processed
ostruct run debug_template.j2 ../../../schema.json --debug-templates \
  --file config_yaml example_config.yaml \
  --ftl code_files sample_code.py \
  --file current_model "gpt-4" \
  --file timestamp "2025-01-24 10:30:00"
```

### Scenario 3: File Content Analysis

The template processes file content. Debug file loading:

```bash
# Verify files are loaded correctly
ostruct run debug_template.j2 ../../../schema.json --show-context-detailed \
  --file config_yaml example_config.yaml \
  --ftl code_files sample_code.py \
  --file current_model "gpt-4"

# See how file content is used in template
ostruct run debug_template.j2 ../../../schema.json --show-templates \
  --file config_yaml example_config.yaml \
  --ftl code_files sample_code.py \
  --file current_model "gpt-4" \
  --file timestamp "2025-01-24 10:30:00" \
  --file potentially_missing_var "Fixed!"
```

## Optimization Debugging Examples

### Large File Optimization

Create a large template to see optimization in action:

```bash
# Show optimization differences
ostruct run debug_template.j2 ../../../schema.json --show-optimization-diff \
  --file config_yaml example_config.yaml \
  --ftl code_files sample_code.py \
  --file current_model "gpt-4"

# Track optimization steps
ostruct run debug_template.j2 ../../../schema.json --show-optimization-steps \
  --file config_yaml example_config.yaml \
  --ftl code_files sample_code.py \
  --file current_model "gpt-4"

# Compare with no optimization
ostruct run debug_template.j2 ../../../schema.json --no-optimization \
  --file config_yaml example_config.yaml \
  --ftl code_files sample_code.py \
  --file current_model "gpt-4"
```

## Troubleshooting Guide

### Problem: Template Not Expanding

**Symptoms**: Template shows `{{ variable }}` in output.

**Debug steps**:

1. Check template syntax: `--debug-templates`
2. Verify variables exist: `--show-context`
3. Look for typos in variable names

### Problem: Undefined Variable Errors

**Error**: `UndefinedError: 'variable_name' is undefined`

**Debug steps**:

1. List available variables: `--show-context`
2. Check variable names for typos
3. Verify file routing is correct

### Problem: Optimization Breaking Template

**Symptoms**: Works with `--no-optimization` but fails normally.

**Debug steps**:

1. Compare before/after: `--show-optimization-diff`
2. Check step-by-step: `--show-optimization-steps`
3. Report if it's a bug in the optimizer

## Quick Reference Commands

```bash
# Basic debugging workflow
ostruct run template.j2 schema.json --show-templates -f file.yaml
ostruct run template.j2 schema.json --show-context -f file.yaml
ostruct run template.j2 schema.json --debug -f file.yaml

# Optimization debugging
ostruct run template.j2 schema.json --show-optimization-diff -f file.yaml
ostruct run template.j2 schema.json --no-optimization -f file.yaml

# Get help
ostruct run template.j2 schema.json --help-debug
```

## Pro Tips

1. **Start simple**: Begin with `--show-templates` to see basic expansion
2. **Check context**: Use `--show-context` when debugging variables
3. **Use step tracking**: `--debug-templates` for complex template logic
4. **Compare optimization**: Always check `--show-optimization-diff` for large files
5. **Test without optimization**: Use `--no-optimization` to isolate optimization issues

## Need Help?

- **CLI Help**: `ostruct run --help-debug`
- **Documentation**: `docs/template_debugging.md`
- **Task Details**: `docs/dev/TEMPLATE_DEBUG_TASKS.md`
