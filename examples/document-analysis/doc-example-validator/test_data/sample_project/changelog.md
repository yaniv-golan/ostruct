# Changelog

All notable changes to AwesomeCLI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- New `--interactive` mode for guided processing
- Support for YAML configuration files

### Changed

- Improved error messages with suggested solutions

## [2.1.0] - 2024-01-15

### Added

- **Batch processing mode**: Process multiple files efficiently

  ```bash
  # Process all CSV files in directory
  awesome-cli batch --pattern "*.csv" --output-dir results/

  # Process specific file list
  awesome-cli batch file1.csv file2.csv file3.csv --workers 4
  ```

- **New validation engine**: Enhanced data validation capabilities

  ```bash
  # Validate with custom schema
  awesome-cli validate data.csv --schema schema.json

  # Validate with built-in rules
  awesome-cli validate data.csv --strict --check-duplicates
  ```

- **Plugin system**: Extensible architecture for custom processing

  ```bash
  # Install a plugin
  awesome-cli plugin install awesome-crypto

  # Use plugin features
  awesome-cli process data.csv --encrypt --key mykey.pem
  ```

### Changed

- **Performance improvements**: 40% faster processing for large files
- **Memory optimization**: Reduced memory usage by 25% with streaming
- **Better progress reporting**: Real-time progress with ETA

  ```bash
  # Enhanced progress display
  awesome-cli process large_file.csv --progress --show-eta
  Processing: ████████████████████████████████ 100% | ETA: 0:00:00
  ```

### Fixed

- Fixed memory leak in long-running batch operations
- Resolved Unicode handling issues on Windows
- Fixed configuration file parsing edge cases

### Security

- Updated dependencies to address CVE-2023-12345
- Added input sanitization for command injection prevention

## [2.0.0] - 2023-12-01

### Added

- **New CLI interface**: Complete redesign for better usability

  ```bash
  # Old way (deprecated)
  awesome-cli --input file.csv --output result.json --format json

  # New way
  awesome-cli process file.csv --to json --output result.json
  ```

- **Configuration profiles**: Save and reuse common settings

  ```bash
  # Create a profile
  awesome-cli config create-profile data-science \
    --format json \
    --validate strict \
    --workers 8

  # Use profile
  awesome-cli process data.csv --profile data-science
  ```

- **Docker support**: Containerized processing

  ```bash
  # Build container
  docker build -t awesome-cli .

  # Run in container
  docker run -v $(pwd):/data awesome-cli process /data/input.csv
  ```

### Changed

- **Breaking**: Renamed `--output-format` to `--to` for consistency
- **Breaking**: Configuration file format changed from INI to YAML
- **API versioning**: All API endpoints now include `/v2/` prefix

### Migration Guide

To upgrade from v1.x to v2.0:

1. **Update CLI commands**:

   ```bash
   # Replace old flags
   sed -i 's/--output-format/--to/g' your_scripts.sh
   sed -i 's/--input/process/g' your_scripts.sh
   ```

2. **Convert configuration**:

   ```bash
   # Automatic conversion
   awesome-cli config migrate config.ini config.yaml
   ```

3. **Update API calls**:

   ```python
   # Old API
   from awesome_cli.api import process_file

   # New API
   from awesome_cli.api.v2 import process_file
   ```

### Removed

- Deprecated `--legacy-mode` flag
- Removed support for Python 3.7

## [1.5.2] - 2023-10-15

### Fixed

- **Critical bug**: Fixed data corruption in CSV processing

  ```bash
  # Verify your data integrity after upgrade
  awesome-cli verify processed_file.csv --checksum
  ```

- Fixed timezone handling in timestamp columns
- Resolved SSL certificate issues with corporate proxies

### Security

- **Important**: Fixed command injection vulnerability (CVE-2023-45678)
- Updated OpenSSL to version 3.0.10

## [1.5.1] - 2023-09-20

### Fixed

- Fixed installation issues on macOS Ventura
- Resolved dependency conflicts with pandas 2.0
- Fixed Unicode BOM handling in text files

### Changed

- Improved error messages with actionable suggestions

  ```bash
  # Example improved error message
  Error: Unable to process file 'data.csv'
  Cause: File contains invalid UTF-8 sequence at line 42

  Suggestions:
  1. Convert file encoding: iconv -f ISO-8859-1 -t UTF-8 data.csv
  2. Skip invalid lines: awesome-cli process data.csv --skip-errors
  3. Specify encoding: awesome-cli process data.csv --encoding latin1
  ```

## [1.5.0] - 2023-08-10

### Added

- **Export functionality**: Multiple output formats

  ```bash
  # Export to different formats
  awesome-cli export data.csv --to json
  awesome-cli export data.csv --to parquet
  awesome-cli export data.csv --to xlsx --sheet "Results"
  ```

- **Data transformation**: Built-in transformations

  ```bash
  # Apply transformations
  awesome-cli transform data.csv \
    --rename "old_col:new_col" \
    --filter "age > 18" \
    --sort "name,age"
  ```

- **Scheduling support**: Cron-like job scheduling

  ```bash
  # Schedule daily processing
  awesome-cli schedule "0 2 * * *" \
    --command "process /data/daily.csv" \
    --name "daily-processing"
  ```

### Changed

- Improved CSV parsing speed by 50%
- Better memory management for large files
- Enhanced logging with structured output

## [1.4.0] - 2023-06-15

### Added

- **REST API**: HTTP interface for remote processing

  ```bash
  # Start API server
  awesome-cli serve --port 8080 --host 0.0.0.0

  # Use API
  curl -X POST http://localhost:8080/api/process \
    -F "file=@data.csv" \
    -F "format=json"
  ```

- **Webhook support**: Event-driven processing

  ```bash
  # Configure webhook
  awesome-cli webhook create \
    --url https://api.example.com/notify \
    --events "process.complete,process.error"
  ```

### Fixed

- Fixed deadlock in multi-threaded processing
- Resolved path handling issues on Windows
- Fixed memory usage calculation

## [1.3.0] - 2023-04-20

### Added

- **Template system**: Reusable processing templates

  ```bash
  # Create template
  awesome-cli template create sales-report \
    --steps "validate,transform,export" \
    --format json

  # Apply template
  awesome-cli template apply sales-report data.csv
  ```

- **Monitoring**: Built-in performance monitoring

  ```bash
  # Enable monitoring
  awesome-cli process data.csv --monitor --metrics-port 9090

  # View metrics (Prometheus format)
  curl http://localhost:9090/metrics
  ```

### Changed

- Refactored configuration system for better extensibility
- Improved command-line help with examples
- Better error recovery in network operations

## [1.2.0] - 2023-02-10

### Added

- **Cloud integration**: Support for cloud storage

  ```bash
  # Process files from S3
  awesome-cli process s3://bucket/data.csv --aws-profile production

  # Upload results to GCS
  awesome-cli process data.csv --output gs://bucket/results/

  # Azure Blob Storage support
  awesome-cli process data.csv --output azure://container/path/
  ```

- **Compression support**: Handle compressed files

  ```bash
  # Process compressed files directly
  awesome-cli process data.csv.gz
  awesome-cli process archive.zip --extract
  ```

### Fixed

- Fixed encoding detection for international characters
- Resolved timeout issues with large files
- Fixed progress bar display on narrow terminals

## [1.1.0] - 2023-01-05

### Added

- **Multi-format support**: Process various file types

  ```bash
  # Supported formats
  awesome-cli process data.csv     # CSV files
  awesome-cli process data.json    # JSON files
  awesome-cli process data.xlsx    # Excel files
  awesome-cli process data.parquet # Parquet files
  ```

- **Validation rules**: Data quality checks

  ```bash
  # Built-in validations
  awesome-cli validate data.csv --check-nulls --check-types

  # Custom validation rules
  awesome-cli validate data.csv --rules validation_rules.yaml
  ```

### Changed

- Improved error handling with detailed messages
- Better documentation with more examples
- Optimized memory usage for streaming operations

## [1.0.0] - 2022-12-01

### Added

- **Initial release**: Core processing functionality

  ```bash
  # Basic usage
  awesome-cli process input.csv --output result.json

  # With options
  awesome-cli process input.csv \
    --format json \
    --validate \
    --backup \
    --verbose
  ```

- **Configuration system**: Flexible settings management

  ```bash
  # Initialize configuration
  awesome-cli --init-config

  # View current settings
  awesome-cli --show-config
  ```

- **Logging**: Comprehensive operation logs

  ```bash
  # Enable detailed logging
  awesome-cli process input.csv --log-level DEBUG

  # Log to file
  awesome-cli process input.csv --log-file processing.log
  ```

### Installation

```bash
# Install via pip
pip install awesome-cli

# Install from source
git clone https://github.com/awesome-org/awesome-cli.git
cd awesome-cli
pip install -e .

# Install with all dependencies
pip install awesome-cli[all]
```

### Requirements

- Python 3.8+
- pandas >= 1.3.0
- click >= 8.0.0
- requests >= 2.25.0

---

## Migration Guides

### Upgrading from 1.x to 2.x

See detailed migration guide at: [docs/migration/v1-to-v2.md](docs/migration/v1-to-v2.md)

### API Changes Summary

- v2.0: Complete API redesign with breaking changes
- v1.5: Added export and transformation features
- v1.4: Introduced REST API
- v1.3: Added template system
- v1.2: Cloud storage integration
- v1.1: Multi-format support
- v1.0: Initial stable release

---

## Support

For questions about changelog entries or upgrade procedures:

- 📖 [Documentation](https://awesome-cli.readthedocs.io)
- 🐛 [Issue Tracker](https://github.com/awesome-org/awesome-cli/issues)
- 💬 [Discussions](https://github.com/awesome-org/awesome-cli/discussions)
- 📧 [Support Email](mailto:support@awesome-cli.org)
