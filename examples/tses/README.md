# TSES Example Templates

This directory contains practical examples demonstrating TSES (Template Structure Enhancement System) capabilities. Each example shows different use cases and best practices for managing large content in templates.

## Examples Overview

| Example | Description | Use Case |
|---------|-------------|----------|
| `code-review.j2` | Code review template with multiple files | Software development |
| `config-analysis.j2` | Configuration file analysis | DevOps and system administration |
| `api-documentation.j2` | API documentation generation | Technical documentation |
| `data-analysis.j2` | Data analysis with large datasets | Data science and analytics |
| `troubleshooting.j2` | System troubleshooting with logs | System administration |

## Quick Start

1. **Basic usage** (content stays inline):

   ```bash
   ostruct run code-review.j2 schema.json --fta file main.py
   ```

2. **With appendix** (large content moved to appendix):

   ```bash
   ostruct run code-review.j2 schema.json --fta file main.py --appendix-mode always
   ```

3. **Auto mode** (intelligent size-based decisions):

   ```bash
   ostruct run code-review.j2 schema.json --fta file main.py --appendix-mode auto --appendix-threshold 512
   ```

## Example Details

### Code Review (`code-review.j2`)

**Purpose**: Review multiple code files with proper structure separation.

**Features**:

- Multiple file handling
- Language-specific syntax highlighting
- Focused review instructions
- Clean separation of code and commentary

**Usage**:

```bash
# Review single file
ostruct run code-review.j2 schema.json --fta file main.py --appendix-mode auto

# Review multiple files
ostruct run code-review.j2 schema.json --fta file main.py --fta file test_main.py --appendix-mode always
```

### Configuration Analysis (`config-analysis.j2`)

**Purpose**: Analyze system configuration files for security and best practices.

**Features**:

- Multi-format configuration support (YAML, JSON, TOML)
- Security-focused analysis
- Environment-specific considerations
- Clear recommendations format

**Usage**:

```bash
ostruct run config-analysis.j2 schema.json --fta file config.yaml --appendix-mode auto
```

### API Documentation (`api-documentation.j2`)

**Purpose**: Generate comprehensive API documentation from OpenAPI specs and examples.

**Features**:

- OpenAPI specification processing
- Example request/response handling
- Authentication documentation
- Rate limiting and error handling

**Usage**:

```bash
ostruct run api-documentation.j2 schema.json --fta file openapi.yaml --appendix-mode always
```

### Data Analysis (`data-analysis.j2`)

**Purpose**: Analyze large datasets and generate insights.

**Features**:

- Large dataset handling
- Multiple data format support
- Statistical analysis requests
- Visualization recommendations

**Usage**:

```bash
ostruct run data-analysis.j2 schema.json --fta file dataset.json --appendix-mode auto --appendix-threshold 1024
```

### Troubleshooting (`troubleshooting.j2`)

**Purpose**: Analyze system logs and configuration for troubleshooting.

**Features**:

- Log file analysis
- Configuration correlation
- Error pattern identification
- Solution recommendations

**Usage**:

```bash
ostruct run troubleshooting.j2 schema.json --fta file error.log --fta file config.yaml --appendix-mode always
```

## TSES Mode Comparison

### Never Mode (Default)

All content appears inline in the main prompt:

```bash
ostruct run code-review.j2 schema.json --fta file large_file.py --appendix-mode never
```

**Result**: Single prompt with all content visible.

### Always Mode

All filtered content moves to appendix:

```bash
ostruct run code-review.j2 schema.json --fta file large_file.py --appendix-mode always
```

**Result**: Clean main prompt + structured appendix with all code.

### Auto Mode

Intelligent size-based decisions:

```bash
ostruct run code-review.j2 schema.json --fta file small.py --fta file large.py --appendix-mode auto --appendix-threshold 256
```

**Result**: Small files inline, large files in appendix.

## Best Practices Demonstrated

### 1. Descriptive Handles

```jinja2
{{ main_code | appendix('main-module', 'python') }}
{{ test_code | appendix('test-suite', 'python') }}
{{ config | appendix('app-config', 'yaml') }}
```

### 2. Meaningful Titles

```jinja2
{{ openapi_spec | appendix('api-spec', 'yaml', 'OpenAPI 3.0 Specification') }}
{{ examples | appendix('examples', 'json', 'Example API Requests') }}
```

### 3. Appropriate MIME Types

```jinja2
{{ python_code | appendix('code', 'python') }}
{{ json_data | appendix('data', 'json') }}
{{ yaml_config | appendix('config', 'yaml') }}
{{ shell_script | appendix('script', 'bash') }}
```

### 4. Content Organization

- Group related files with consistent handle prefixes
- Use titles to provide context in appendix
- Leverage auto-detection for unknown content types

## Testing Different Modes

Each example can be tested with different TSES modes to see the impact:

```bash
# Test with different modes
for mode in never always auto; do
  echo "Testing with --appendix-mode $mode"
  ostruct run code-review.j2 schema.json --fta file example.py --appendix-mode $mode
  echo "---"
done
```

## Advanced Usage Examples

### Conditional TSES

```jinja2
{% if file_size > 1000 %}
{{ content | appendix('large-file', mime_type) }}
{% else %}
{{ content | inline }}
{% endif %}
```

### Dynamic Handles

```jinja2
{% for file in files %}
{{ file.content | appendix('file-' + loop.index|string, file.type) }}
{% endfor %}
```

### Mixed Content Strategy

```jinja2
<!-- Always inline for critical snippets -->
{{ error_snippet | inline }}

<!-- Appendix for large references -->
{{ full_stacktrace | appendix('stacktrace', 'text', 'Full Stack Trace') }}

<!-- Auto-decide for variable content -->
{{ log_excerpt | appendix('logs', 'text') }}
```

## Integration Examples

### With File Attachments

```bash
# Multiple files with different handling
ostruct run troubleshooting.j2 schema.json \
  --fta file error.log \
  --fta file config.yaml \
  --fta file debug.json \
  --appendix-mode auto \
  --appendix-threshold 512
```

### With Variables

```bash
# Using template variables with TSES
ostruct run config-analysis.j2 schema.json \
  --var environment=production \
  --var security_level=high \
  --fta file prod-config.yaml \
  --appendix-mode always
```

### With Debug Mode

```bash
# See TSES decisions in action
ostruct run data-analysis.j2 schema.json \
  --fta file large-dataset.json \
  --appendix-mode auto \
  --appendix-threshold 1024 \
  --template-debug all
```

## Performance Notes

- **Small files** (<256 bytes): Minimal performance impact
- **Medium files** (256B-1MB): Slight processing overhead in auto mode
- **Large files** (>1MB): Noticeable but acceptable processing time
- **Many files**: Linear scaling with number of filtered content blocks

## Troubleshooting Examples

### Handle Conflicts

If you get handle validation errors:

```jinja2
<!-- Problem: Invalid characters -->
{{ content | appendix('My_File.txt') }}

<!-- Solution: Use valid handle format -->
{{ content | appendix('my-file-txt') }}
```

### MIME Type Issues

If syntax highlighting isn't working:

```jinja2
<!-- Problem: Auto-detection failed -->
{{ content | appendix('script') }}

<!-- Solution: Specify MIME type -->
{{ content | appendix('script', 'bash') }}
```

### Size Threshold Tuning

If auto mode isn't working as expected:

```bash
# Too aggressive (moves small content)
--appendix-threshold 100

# Too conservative (keeps large content inline)
--appendix-threshold 10000

# Balanced approach
--appendix-threshold 512
```

## Contributing New Examples

When adding new examples:

1. Focus on real-world use cases
2. Demonstrate specific TSES features
3. Include usage instructions
4. Test with all three appendix modes
5. Document any special considerations

## Next Steps

After exploring these examples:

1. Try modifying the templates for your use cases
2. Experiment with different appendix modes
3. Create your own templates using TSES best practices
4. Read the full TSES documentation in `docs/user/TSES.md`
