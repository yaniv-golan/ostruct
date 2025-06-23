# Template Environment Variables Example

This example demonstrates how to use ostruct's template-specific environment variables to control file processing behavior.

## Environment Variables Overview

ostruct provides three environment variables that control template processing:

- `OSTRUCT_TEMPLATE_FILE_LIMIT`: Maximum individual file size for template access (default: 64KB)
- `OSTRUCT_TEMPLATE_TOTAL_LIMIT`: Maximum total file size for all template files (default: 1MB)
- `OSTRUCT_TEMPLATE_PREVIEW_LIMIT`: Maximum characters shown in template debug previews (default: 4096)

**Important**: These variables only affect template-only files (`--file alias path`) and do NOT affect Code Interpreter (`--file ci:`) or File Search (`--file fs:`) operations.

## Basic Usage

### Default Behavior

```bash
# Uses default limits (64KB per file, 1MB total, 4KB preview)
ostruct run template.j2 schema.json --file config config.yaml
```

### Custom Limits

```bash
# Set larger limits for processing large configuration files
export OSTRUCT_TEMPLATE_FILE_LIMIT=262144    # 256KB per file
export OSTRUCT_TEMPLATE_TOTAL_LIMIT=5242880  # 5MB total

ostruct run large_config_analysis.j2 schema.json \
  --file config large_config.yaml \
  --file docs documentation.md
```

### Debug Preview Control

```bash
# Show more content in debug previews
export OSTRUCT_TEMPLATE_PREVIEW_LIMIT=8192  # 8KB preview

ostruct run template.j2 schema.json \
  --file data large_file.txt \
  --template-debug preview
```

## Scope Demonstration

```bash
# These files are subject to template limits
ostruct run analysis.j2 schema.json \
  --file config config.yaml \          # ← Template limits apply
  --file docs documentation.md \       # ← Template limits apply
  --file ci:data large_dataset.csv \   # ← Template limits DO NOT apply
  --file fs:docs manual.pdf             # ← Template limits DO NOT apply
```

## Configuration Methods

### 1. Project-specific (.env file)

Create a `.env` file in your project:

```bash
# .env
OSTRUCT_TEMPLATE_FILE_LIMIT=131072
OSTRUCT_TEMPLATE_TOTAL_LIMIT=2097152
OSTRUCT_TEMPLATE_PREVIEW_LIMIT=6144
```

### 2. Global environment

Add to your shell profile (`~/.bashrc` or `~/.zshrc`):

```bash
export OSTRUCT_TEMPLATE_FILE_LIMIT=131072
export OSTRUCT_TEMPLATE_TOTAL_LIMIT=2097152
export OSTRUCT_TEMPLATE_PREVIEW_LIMIT=6144
```

### 3. One-time override

```bash
# Temporary override for specific command
OSTRUCT_TEMPLATE_FILE_LIMIT=524288 \
OSTRUCT_TEMPLATE_TOTAL_LIMIT=10485760 \
ostruct run large_analysis.j2 schema.json --file data huge_file.txt
```

## Use Cases

### Large Configuration Processing

When working with large YAML/JSON configuration files:

```bash
export OSTRUCT_TEMPLATE_FILE_LIMIT=524288    # 512KB per file
export OSTRUCT_TEMPLATE_TOTAL_LIMIT=10485760 # 10MB total

ostruct run config_analysis.j2 schema.json \
  --file app_config config/app.yaml \
  --file db_config config/database.yaml \
  --file env_config config/environment.yaml
```

### Document Analysis

For processing large text documents:

```bash
export OSTRUCT_TEMPLATE_FILE_LIMIT=1048576   # 1MB per file
export OSTRUCT_TEMPLATE_TOTAL_LIMIT=20971520 # 20MB total

ostruct run document_analysis.j2 schema.json \
  --file docs documentation/ \
  --file specs specifications.md
```

### Memory-Constrained Environments

In resource-limited environments:

```bash
export OSTRUCT_TEMPLATE_FILE_LIMIT=32768     # 32KB per file
export OSTRUCT_TEMPLATE_TOTAL_LIMIT=262144   # 256KB total
export OSTRUCT_TEMPLATE_PREVIEW_LIMIT=1024   # 1KB preview

ostruct run lightweight_analysis.j2 schema.json \
  --file config small_config.yaml
```

### Debug Session with Extended Previews

For detailed debugging:

```bash
export OSTRUCT_TEMPLATE_PREVIEW_LIMIT=16384  # 16KB preview

ostruct run complex_template.j2 schema.json \
  --file data complex_data.json \
  --template-debug vars,preview
```

## Tips and Best Practices

1. **Start with defaults**: Only adjust limits when you encounter actual size issues
2. **Use .env files**: Keep project-specific limits in `.env` files for consistency
3. **Monitor memory usage**: Large limits can increase memory consumption
4. **Consider alternatives**: For very large files, consider using Code Interpreter or File Search routing instead
5. **Debug incrementally**: Use smaller preview limits for cleaner debug output, larger for detailed analysis

## Error Messages

When files exceed limits, you'll see helpful error messages:

```
File 'large_config.yaml' (131,072 bytes) exceeds size limit (65,536 bytes)
```

This indicates you should either:

- Increase `OSTRUCT_TEMPLATE_FILE_LIMIT`
- Use Code Interpreter routing (`--file ci:data large_config.yaml`)
- Use File Search routing (`--file fs:docs large_config.yaml`)
