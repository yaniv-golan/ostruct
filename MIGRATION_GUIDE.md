# Migration Guide: Legacy → New Syntax

**ostruct v0.8.x → v0.9.0**

## Breaking Changes Summary (v0.9.0)

The new CLI completely replaces the old file routing system with explicit target/alias syntax. This provides better control, security, and clarity about how files are processed.

### What Changed

- **File routing system**: Complete replacement with target/alias syntax
- **Security model**: Enhanced with three-tier security modes
- **Tool targeting**: Explicit control over which tools receive files
- **Alias requirements**: All file attachments now require explicit aliases

## Migration Examples

### Basic File Attachments

| Legacy Syntax (v0.8.x) | New Syntax (v0.9.0) | Notes |
|-------------------------|----------------------|-------|
| `-f data file.txt` | `--file data file.txt` | Template access only |
| `-d docs ./docs` | `--dir docs ./docs` | Template access only |
| `-p logs '*.log'` | `--dir logs ./logs --pattern '*.log'` | Directory with pattern |

### Tool-Specific Routing

| Legacy Syntax (v0.8.x) | New Syntax (v0.9.0) | Notes |
|-------------------------|----------------------|-------|
| `-fc file.csv` | `--file ci:data file.csv` | Code Interpreter |
| `-fs manual.pdf` | `--file fs:docs manual.pdf` | File Search |
| `-ft config.yaml` | `--file config config.yaml` | Template only (explicit) |
| `--file-for code-interpreter data.csv` | `--file ci:data data.csv` | Simplified syntax |
| `--dir-for-search ./docs` | `--dir fs:docs ./docs` | Directory upload |

### Advanced Routing

| Legacy (v0.8.x) | New (v0.9.0) | Benefit |
|------------------|---------------|---------|
| Multiple `--file-for` calls | `--file ci,fs:shared data.json` | Single attachment, multiple targets |
| Manual variable naming | Explicit aliases required | Clear template variable names |
| Auto-generated names | User-controlled aliases | Predictable template access |

## Security Migration

| Legacy (v0.8.x) | New (v0.9.0) | Benefit |
|------------------|---------------|---------|
| No explicit security | `--path-security strict` | Enhanced security |
| Manual path validation | `--allow /safe/paths` | Explicit allowlists |
| N/A | `--allow-file specific.txt` | File-level permissions |
| Basic validation | Three-tier security model | Granular control |

## Automated Migration

### Bulk Script Migration

Use these sed commands for bulk migration of existing scripts:

```bash
# Basic file attachments
sed -i 's/-f \([^ ]*\) \([^ ]*\)/--file \1 \2/g' scripts/*.sh

# Directory attachments
sed -i 's/-d \([^ ]*\) \([^ ]*\)/--dir \1 \2/g' scripts/*.sh

# Code Interpreter files
sed -i 's/-fc \([^ ]*\)/--file ci:data \1/g' scripts/*.sh

# File Search files
sed -i 's/-fs \([^ ]*\)/--file fs:docs \1/g' scripts/*.sh

# Template files (explicit)
sed -i 's/-ft \([^ ]*\)/--file prompt:config \1/g' scripts/*.sh

# Advanced routing
sed -i 's/--file-for-code-interpreter \([^ ]*\)/--file ci:data \1/g' scripts/*.sh
sed -i 's/--file-for-file-search \([^ ]*\)/--file fs:docs \1/g' scripts/*.sh
```

### Migration Script

Create a migration script for complex transformations:

```python
#!/usr/bin/env python3
"""
ostruct CLI Migration Script (v0.8.x → v0.9.0)
Converts legacy file routing to new attachment syntax.
"""

import re
import sys
from pathlib import Path

def migrate_command(cmd_line):
    """Migrate a single command line from legacy to new syntax."""

    # Basic file attachments
    cmd_line = re.sub(r'-f (\w+) ([^\s]+)', r'--file \1 \2', cmd_line)

    # Directory attachments
    cmd_line = re.sub(r'-d (\w+) ([^\s]+)', r'--dir \1 \2', cmd_line)

    # Tool-specific routing
    cmd_line = re.sub(r'-fc ([^\s]+)', r'--file ci:data \1', cmd_line)
    cmd_line = re.sub(r'-fs ([^\s]+)', r'--file fs:docs \1', cmd_line)
    cmd_line = re.sub(r'-ft ([^\s]+)', r'--file config \1', cmd_line)

    # Advanced routing
    cmd_line = re.sub(r'--file-for-code-interpreter ([^\s]+)',
                     r'--file ci:data \1', cmd_line)
    cmd_line = re.sub(r'--file-for-file-search ([^\s]+)',
                     r'--file fs:docs \1', cmd_line)

    return cmd_line

def migrate_file(file_path):
    """Migrate an entire script file."""
    with open(file_path, 'r') as f:
        content = f.read()

    lines = content.split('\n')
    migrated_lines = []

    for line in lines:
        if 'ostruct run' in line:
            migrated_line = migrate_command(line)
            print(f"Migrated: {line.strip()}")
            print(f"      →   {migrated_line.strip()}")
            migrated_lines.append(migrated_line)
        else:
            migrated_lines.append(line)

    # Write backup
    backup_path = f"{file_path}.backup"
    with open(backup_path, 'w') as f:
        f.write(content)
    print(f"Backup saved: {backup_path}")

    # Write migrated version
    with open(file_path, 'w') as f:
        f.write('\n'.join(migrated_lines))
    print(f"Migrated: {file_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: migrate.py <script_file> [script_file ...]")
        sys.exit(1)

    for file_path in sys.argv[1:]:
        if Path(file_path).exists():
            migrate_file(file_path)
        else:
            print(f"File not found: {file_path}")
```

## Manual Migration Steps

### 1. Update Shell Scripts

For each script using ostruct:

1. **Backup the original**: `cp script.sh script.sh.backup`
2. **Apply sed transformations** or use the migration script above
3. **Test the migrated script**: Verify it works with new syntax
4. **Update security settings**: Add `--path-security` if needed

### 2. Update Documentation

1. **Update README files**: Replace all CLI examples
2. **Update build scripts**: Migrate CI/CD pipeline commands
3. **Update user guides**: Replace file routing examples

### 3. Update Configuration

1. **Environment variables**: Some may have changed
2. **Configuration files**: Check for deprecated settings
3. **Security policies**: Implement new security modes

## Common Migration Issues

### Issue: Auto-generated Variable Names

**Problem**: Legacy auto-naming (`-ft config.yaml` → `config_yaml`)
**Solution**: Use explicit aliases (`--file config config.yaml`)

### Issue: Multiple Tool Routing

**Problem**: Multiple `--file-for` calls for same file
**Solution**: Use multi-target syntax (`--file ci,fs:shared file.json`)

### Issue: Directory Patterns

**Problem**: Pattern syntax changes
**Solution**: Use `--dir alias ./path --pattern '*.ext'`

### Issue: Security Validation

**Problem**: New security modes may block previously allowed files
**Solution**: Use `--path-security permissive` temporarily, then migrate to `strict`

## New Features to Adopt

### 1. Enhanced Security

```bash
# Enable strict security mode
ostruct run template.j2 schema.json \
  --path-security strict \
  --allow /safe/directory \
  --allow-file /specific/file.txt
```

### 2. JSON Output Options

```bash
# Get execution plan as JSON
ostruct run template.j2 schema.json --dry-run --dry-run-json

# Get run summary as JSON
ostruct run template.j2 schema.json --run-summary-json

# Get JSON help for programmatic consumption
ostruct run --help-json
```

### 3. Multi-Tool Integration

```bash
# Share files between tools
ostruct run workflow.j2 schema.json \
  --file ci,fs:shared data.json \
  --file prompt:config settings.yaml
```

### 4. File Collections

```bash
# Process multiple files from list
ostruct run batch.j2 schema.json --collect ci:data @file-list.txt
```

## Testing Migration

### Validation Commands

```bash
# Test syntax validation
ostruct run template.j2 schema.json --dry-run --file data file.txt

# Verify file routing
ostruct run template.j2 schema.json --dry-run-json --file ci:data file.csv

# Check security settings
ostruct run template.j2 schema.json --path-security strict --dry-run
```

### Comparison Testing

1. **Run legacy version** (v0.8.x) and save output
2. **Run migrated version** (v0.9.0) with new syntax
3. **Compare outputs** to ensure equivalence
4. **Test error cases** to verify proper validation

## Getting Help

- **CLI Help**: `ostruct run --help`
- **JSON Help**: `ostruct run --help-json`
- **Quick Reference**: `ostruct quick-ref`
- **Documentation**: <https://ostruct.readthedocs.io>

## Rollback Plan

If migration issues occur:

1. **Use backup files**: Restore from `.backup` files
2. **Pin to v0.8.x**: `pip install ostruct-cli==0.8.29`
3. **Gradual migration**: Migrate scripts one at a time
4. **Report issues**: File issues at <https://github.com/yaniv-golan/ostruct/issues>

---

**Need Help?** The migration is designed to be straightforward, but if you encounter issues, please consult the documentation or file an issue for assistance.
