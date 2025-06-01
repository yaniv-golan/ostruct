# Configuration Guide

AwesomeCLI provides flexible configuration options to customize its behavior for your specific needs.

## Configuration File Locations

AwesomeCLI looks for configuration files in the following order:

1. Current directory: `./awesome-cli.yaml`
2. User home: `~/.awesome-cli/config.yaml`
3. System-wide: `/etc/awesome-cli/config.yaml`

Create a configuration file:

```bash
# Initialize with defaults
awesome-cli --init-config

# Create in specific location
awesome-cli --init-config --config ~/.config/awesome-cli.yaml
```

## Configuration Format

### YAML Configuration (Recommended)

```yaml
# ~/.awesome-cli/config.yaml
general:
  # Processing settings
  workers: 4
  timeout: 300
  memory_limit: "2GB"

  # Output preferences
  verbose: false
  quiet: false
  progress: true

processing:
  # Data handling
  chunk_size: 10000
  streaming: true
  validate_input: true
  backup_files: true

  # Performance tuning
  cache_enabled: true
  cache_size: "500MB"
  parallel_processing: true

output:
  # Default output settings
  format: "json"
  compression: "gzip"
  pretty_print: true
  include_metadata: true

  # File naming
  timestamp_suffix: true
  output_directory: "./results"

logging:
  # Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
  level: "INFO"
  file: "/var/log/awesome-cli.log"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  max_size: "10MB"
  backup_count: 5

plugins:
  # Plugin configuration
  enabled:
    - "awesome-crypto"
    - "awesome-stats"

  paths:
    - "~/.awesome-cli/plugins"
    - "/usr/local/lib/awesome-cli/plugins"

security:
  # Security settings
  ssl_verify: true
  api_key_file: "~/.awesome-cli/api.key"
  encryption_key: "~/.awesome-cli/encrypt.key"
```

### Environment Variables

Override any configuration with environment variables:

```bash
# General settings
export AWESOME_WORKERS=8
export AWESOME_TIMEOUT=600
export AWESOME_VERBOSE=true

# Processing settings
export AWESOME_CHUNK_SIZE=50000
export AWESOME_STREAMING=false
export AWESOME_CACHE_ENABLED=false

# Output settings
export AWESOME_FORMAT=xml
export AWESOME_COMPRESSION=none
export AWESOME_OUTPUT_DIR=/tmp/results

# Logging
export AWESOME_LOG_LEVEL=DEBUG
export AWESOME_LOG_FILE=/tmp/awesome-cli.log

# Security
export AWESOME_API_KEY="your-api-key-here"
export AWESOME_SSL_VERIFY=false
```

### Command Line Override

Any configuration can be overridden on the command line:

```bash
# Override workers setting
awesome-cli process data.csv --workers 8

# Override multiple settings
awesome-cli process data.csv \
  --workers 8 \
  --timeout 600 \
  --format xml \
  --no-compression
```

## Configuration Sections

### General Settings

Basic operational parameters:

```yaml
general:
  workers: 4              # Number of parallel workers
  timeout: 300            # Operation timeout in seconds
  memory_limit: "2GB"     # Maximum memory usage
  temp_directory: "/tmp"  # Temporary file location
  verbose: false          # Enable verbose output
  quiet: false           # Suppress non-error output
  progress: true         # Show progress bars
  color: true            # Enable colored output
```

Example usage:

```bash
# High-performance configuration
awesome-cli process large_dataset.csv \
  --workers 16 \
  --timeout 3600 \
  --memory-limit 8GB
```

### Processing Settings

Data processing behavior:

```yaml
processing:
  # Input handling
  chunk_size: 10000       # Records per chunk
  streaming: true         # Enable streaming mode
  validate_input: true    # Validate input data
  skip_errors: false      # Skip invalid records

  # File handling
  backup_files: true      # Create backup before processing
  preserve_permissions: true  # Keep original file permissions
  follow_symlinks: false  # Follow symbolic links

  # Performance
  cache_enabled: true     # Enable result caching
  cache_size: "500MB"     # Cache size limit
  parallel_processing: true  # Enable parallel operations
  optimize_memory: true   # Memory optimization
```

Example configurations:

```bash
# Memory-efficient processing
awesome-cli process huge_file.csv \
  --chunk-size 1000 \
  --streaming \
  --optimize-memory

# Fast processing (more memory usage)
awesome-cli process data.csv \
  --chunk-size 100000 \
  --no-streaming \
  --workers 8
```

### Output Settings

Control output format and location:

```yaml
output:
  # Format options
  format: "json"          # json, csv, xml, parquet, xlsx
  compression: "gzip"     # gzip, bzip2, xz, none
  pretty_print: true      # Format output for readability
  include_metadata: true  # Include processing metadata

  # File handling
  timestamp_suffix: true  # Add timestamp to filenames
  output_directory: "./results"  # Default output location
  overwrite_existing: false     # Overwrite existing files
  create_directories: true      # Create output directories

  # CSV-specific options
  csv_delimiter: ","      # CSV field delimiter
  csv_quoting: "minimal"  # CSV quoting style
  csv_encoding: "utf-8"   # CSV file encoding
```

Format-specific examples:

```bash
# JSON output with pretty printing
awesome-cli process data.csv \
  --format json \
  --pretty-print \
  --output results.json

# CSV output with custom delimiter
awesome-cli process data.json \
  --format csv \
  --csv-delimiter "|" \
  --output data.csv

# Compressed output
awesome-cli process large_data.csv \
  --format parquet \
  --compression gzip \
  --output compressed_data.parquet.gz
```

### Logging Configuration

Control logging behavior:

```yaml
logging:
  level: "INFO"           # DEBUG, INFO, WARNING, ERROR, CRITICAL
  file: "/var/log/awesome-cli.log"  # Log file location
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  max_size: "10MB"        # Log file rotation size
  backup_count: 5         # Number of backup files

  # Console logging
  console_level: "WARNING"  # Console log level
  console_format: "%(levelname)s: %(message)s"

  # Structured logging
  structured: false       # Enable JSON structured logs
  include_caller: true    # Include caller information
```

Logging examples:

```bash
# Debug logging to console
awesome-cli process data.csv --log-level DEBUG

# Log to specific file
awesome-cli process data.csv --log-file /tmp/processing.log

# Quiet mode (errors only)
awesome-cli process data.csv --quiet
```

### Plugin Configuration

Manage plugins and extensions:

```yaml
plugins:
  enabled:
    - "awesome-crypto"    # Encryption/decryption plugin
    - "awesome-stats"     # Statistics plugin
    - "awesome-viz"       # Visualization plugin

  disabled:
    - "awesome-legacy"    # Disable specific plugins

  paths:
    - "~/.awesome-cli/plugins"           # User plugin directory
    - "/usr/local/lib/awesome-cli/plugins"  # System plugin directory

  # Plugin-specific configuration
  awesome-crypto:
    default_algorithm: "AES-256"
    key_derivation: "PBKDF2"

  awesome-stats:
    auto_generate: true
    include_charts: false
```

Plugin usage examples:

```bash
# List available plugins
awesome-cli plugin list

# Install plugin
awesome-cli plugin install awesome-crypto

# Use plugin features
awesome-cli process sensitive_data.csv \
  --encrypt \
  --algorithm AES-256 \
  --key-file encryption.key
```

## Profile-Based Configuration

Create and use configuration profiles for different scenarios:

### Creating Profiles

```bash
# Create data science profile
awesome-cli config create-profile data-science \
  --workers 8 \
  --format parquet \
  --compression snappy \
  --cache-size 2GB

# Create production profile
awesome-cli config create-profile production \
  --workers 16 \
  --timeout 3600 \
  --backup-files \
  --log-level WARNING \
  --output-dir /var/data/results
```

### Using Profiles

```bash
# Use specific profile
awesome-cli process data.csv --profile data-science

# List available profiles
awesome-cli config list-profiles

# Show profile configuration
awesome-cli config show-profile production
```

### Profile Configuration File

```yaml
profiles:
  data-science:
    workers: 8
    format: "parquet"
    compression: "snappy"
    cache_size: "2GB"
    include_metadata: true

  production:
    workers: 16
    timeout: 3600
    backup_files: true
    log_level: "WARNING"
    output_directory: "/var/data/results"

  development:
    workers: 2
    verbose: true
    log_level: "DEBUG"
    validate_input: true
    pretty_print: true
```

## Advanced Configuration

### Custom Processing Rules

```yaml
processing_rules:
  # Data validation rules
  validation:
    check_duplicates: true
    check_nulls: true
    check_types: true
    custom_validators:
      - "email_format"
      - "phone_number"

  # Transformation rules
  transformations:
    auto_infer_types: true
    normalize_whitespace: true
    convert_dates: true
    date_format: "%Y-%m-%d"

  # Filter rules
  filters:
    exclude_columns: ["internal_id", "temp_column"]
    include_pattern: ".*_public$"
    row_filters:
      - "status == 'active'"
      - "created_date >= '2023-01-01'"
```

### Performance Tuning

```yaml
performance:
  # Memory management
  memory_limit: "4GB"
  swap_threshold: 0.8
  gc_frequency: 1000

  # I/O optimization
  buffer_size: "64KB"
  read_ahead: true
  write_buffer: "1MB"

  # Concurrency
  max_workers: 16
  worker_timeout: 300
  queue_size: 100
```

## Configuration Management Commands

### View Configuration

```bash
# Show current configuration
awesome-cli config show

# Show specific section
awesome-cli config show --section processing

# Show configuration sources
awesome-cli config sources

# Validate configuration
awesome-cli config validate
```

### Modify Configuration

```bash
# Set configuration value
awesome-cli config set general.workers 8

# Set nested value
awesome-cli config set processing.cache_enabled true

# Unset configuration value
awesome-cli config unset output.compression

# Reset to defaults
awesome-cli config reset
```

### Configuration Examples

```bash
# Export current configuration
awesome-cli config export > my-config.yaml

# Import configuration
awesome-cli config import my-config.yaml

# Merge configurations
awesome-cli config merge additional-config.yaml

# Copy configuration between profiles
awesome-cli config copy-profile production staging
```

## Environment-Specific Configuration

### Development Environment

```yaml
# development.yaml
general:
  workers: 2
  verbose: true
  progress: true

processing:
  chunk_size: 1000
  validate_input: true
  backup_files: true

output:
  format: "json"
  pretty_print: true
  include_metadata: true

logging:
  level: "DEBUG"
  console_level: "INFO"
```

Usage:

```bash
awesome-cli process data.csv --config development.yaml
```

### Production Environment

```yaml
# production.yaml
general:
  workers: 16
  verbose: false
  progress: false

processing:
  chunk_size: 50000
  validate_input: false
  backup_files: true
  cache_enabled: true

output:
  format: "parquet"
  compression: "snappy"
  pretty_print: false
  include_metadata: false

logging:
  level: "WARNING"
  file: "/var/log/awesome-cli.log"
  structured: true
```

Usage:

```bash
awesome-cli process data.csv --config production.yaml
```

## Troubleshooting Configuration

### Common Issues

1. **Configuration not loading**:

   ```bash
   # Check configuration file path
   awesome-cli config show-path

   # Validate syntax
   awesome-cli config validate
   ```

2. **Environment variables not working**:

   ```bash
   # Check environment variable names
   awesome-cli config env-vars

   # Show effective configuration
   awesome-cli config show --with-sources
   ```

3. **Profile not found**:

   ```bash
   # List available profiles
   awesome-cli config list-profiles

   # Create missing profile
   awesome-cli config create-profile myprofile
   ```

### Configuration Debugging

```bash
# Enable configuration debugging
AWESOME_CONFIG_DEBUG=1 awesome-cli process data.csv

# Show configuration loading process
awesome-cli config debug

# Test configuration changes
awesome-cli config test --workers 8 --timeout 600
```

For more configuration examples and advanced topics, see:

- [Performance Tuning Guide](performance-tuning.md)
- [Plugin Development](plugin-development.md)
- [Security Configuration](security.md)
