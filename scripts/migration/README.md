# ostruct Migration Tools (v0.8.x → v0.9.0)

This directory contains migration tools to help users transition from ostruct v0.8.x legacy file routing syntax to the new v0.9.0 target/alias attachment system.

## Migration Tools Overview

### 🔧 `migrate_cli_syntax.py` - Main Migration Script

Migrates shell scripts, Python scripts, and other files containing ostruct CLI commands.

**Usage:**

```bash
# Preview changes (dry run)
python migrate_cli_syntax.py *.sh --dry-run

# Apply migrations to shell scripts
python migrate_cli_syntax.py *.sh

# Migrate with validation
python migrate_cli_syntax.py *.sh --validate

# Migrate configuration file
python migrate_cli_syntax.py --config ostruct.yaml
```

**Supported Migrations:**

- `-f alias file` → `--file alias file`
- `-d alias dir` → `--dir alias dir`
- `-fc file` → `--file ci:data file`
- `-fs file` → `--file fs:docs file`
- `-ft file` → `--file config file`
- `--file-for-*` → `--file target:alias`
- Security options: `-A` → `--allow`

### ⚙️ `migrate_config.py` - Configuration Migration

Specialized tool for migrating ostruct configuration files (YAML).

**Usage:**

```bash
# Analyze configuration
python migrate_config.py ostruct.yaml --analyze

# Preview configuration changes
python migrate_config.py ostruct.yaml --dry-run

# Migrate configuration file
python migrate_config.py ostruct.yaml --validate
```

**Configuration Changes:**

- `file_routing` → `attachments` section
- `security.allowed_dirs` → `attachments.allowed_directories`
- Adds new `path_security` configuration
- Adds new `tools` configuration for code_interpreter and file_search

### 📦 `batch_migrate.py` - Project-Wide Migration

Migrates entire projects or directories containing multiple ostruct files.

**Usage:**

```bash
# Analyze entire project
python batch_migrate.py /path/to/project --analyze

# Preview all project changes
python batch_migrate.py /path/to/project --dry-run --recursive

# Migrate project with report
python batch_migrate.py /path/to/project --validate --report migration_report.md
```

**Features:**

- Automatic file discovery (scripts, configs, CI/CD files)
- Risk assessment based on project size and complexity
- Comprehensive migration reporting
- Backup creation for all modified files

## Migration Process Recommendations

### 1. Pre-Migration Checklist

- [ ] **Backup your project** - Create a full backup before migration
- [ ] **Update ostruct** - Install v0.9.0 before testing
- [ ] **Review dependencies** - Check if any external scripts use ostruct
- [ ] **Prepare test environment** - Set up isolated testing environment

### 2. Migration Steps

#### Step 1: Analysis

```bash
# Analyze your project to understand scope
python batch_migrate.py . --analyze --recursive
```

#### Step 2: Preview Changes

```bash
# Preview all changes that will be made
python batch_migrate.py . --dry-run --recursive
```

#### Step 3: Migrate Configuration

```bash
# Migrate configuration files first
python migrate_config.py ostruct.yaml --validate
```

#### Step 4: Migrate Scripts

```bash
# Migrate all scripts with validation
python batch_migrate.py . --validate --recursive
```

#### Step 5: Generate Report

```bash
# Create comprehensive migration report
python batch_migrate.py . --validate --report migration_report.md
```

### 3. Post-Migration Validation

#### Test Migration Results

```bash
# Test basic functionality
ostruct run template.j2 schema.json --file data file.txt --dry-run

# Test security modes
ostruct run template.j2 schema.json --path-security strict --allow ./data

# Validate configuration
ostruct run template.j2 schema.json --config ostruct.yaml --dry-run
```

#### Common Issues and Solutions

**Issue**: "attachment without alias" error

```bash
# OLD (invalid): --file file.txt
# NEW (correct): --file data file.txt
```

**Issue**: Security path violations

```bash
# Add explicit path allowances
ostruct run template.j2 schema.json --path-security strict --allow /project/data
```

**Issue**: Missing tool targets

```bash
# OLD: -fc data.csv
# NEW: --file ci:data data.csv
```

## Migration Examples

### Shell Script Migration

**Before (v0.8.x):**

```bash
#!/bin/bash
ostruct run analysis.j2 schema.json \
  -fc data.csv \
  -fs documentation.pdf \
  -ft config.yaml \
  -A /project/data
```

**After (v0.9.0):**

```bash
#!/bin/bash
ostruct run analysis.j2 schema.json \
  --file ci:data data.csv \
  --file fs:docs documentation.pdf \
  --file config config.yaml \
  --allow /project/data
```

### Configuration Migration

**Before (v0.8.x):**

```yaml
file_routing:
  default_target: template
  auto_alias: true

security:
  allowed_dirs:
    - /project/data
    - /tmp
```

**After (v0.9.0):**

```yaml
attachments:
  default_target: prompt
  allowed_directories:
    - /project/data
    - /tmp

path_security:
  mode: warn

tools:
  code_interpreter:
    auto_download: true
    cleanup: true
  file_search:
    cleanup: true

models:
  default: gpt-4o
```

## Backup and Recovery

### Backup Strategy

All migration tools create `.bak` backup files automatically:

- `script.sh` → `script.sh.bak`
- `ostruct.yaml` → `ostruct.yaml.bak`

### Recovery Process

If migration issues occur:

```bash
# Restore from backup
mv script.sh.bak script.sh
mv ostruct.yaml.bak ostruct.yaml

# Or restore all backups
find . -name "*.bak" -exec sh -c 'mv "$1" "${1%.bak}"' _ {} \;
```

## Troubleshooting

### Common Migration Issues

**Files not found:**

- Ensure you're in the correct directory
- Check file permissions
- Use `--recursive` for subdirectories

**Syntax errors after migration:**

- Run with `--validate` to check for issues
- Review the migration report for warnings
- Test individual commands with `--dry-run`

**Performance issues:**

- Large projects may take time to analyze
- Use `--analyze` first to estimate scope
- Consider migrating in batches for very large projects

### Getting Help

1. **Check validation output** - Always use `--validate` flag
2. **Review migration reports** - Use `--report` to generate detailed logs
3. **Test incrementally** - Migrate small sections first
4. **Use dry-run mode** - Always preview changes before applying

## Version Compatibility

| ostruct Version | Migration Tool Support |
|----------------|----------------------|
| v0.8.x → v0.9.0 | ✅ Full support |
| v0.7.x → v0.9.0 | ⚠️ Manual review needed |
| v0.6.x and below | ❌ Not supported |

---

For additional help, file an issue at the ostruct repository.
