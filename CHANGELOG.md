# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.6.1] - 2025-08-03

### Fixed

#### Code Interpreter Download Strategy

- Fixed issue where `--ci-download` flag was not properly triggering two-pass sentinel mode with structured outputs
- Resolved "No sentinel JSON found in first pass" warnings when using Code Interpreter file downloads
- Template processor now receives correct download strategy for proper sentinel marker injection
- Auto-enable logic for two-pass mode now executes before template processing rather than after

#### CLI Help System

- Corrected CLI option groupings in help output to match actual available flags
- Fixed `--sys-prompt-file` reference to correct `--sys-file` flag name
- Updated security options to reflect current flag names (`--allow` instead of `--allow-paths`)
- Removed references to non-existent `--disallow-paths` flag

#### Documentation

- Updated `llms.txt` with correct flag references and enhanced schema design patterns
- Added Jupyter/notebook integration guidance and use case mental models
- Corrected scaffold command documentation to show proper OST file creation syntax

### Changed

#### Internal Improvements

- Enhanced template context handling for download strategy determination
- Added `_effective_download_strategy` field to CLIParams TypedDict for better type safety
- Improved execution flow to ensure strategy decisions occur before template processing

## [1.6.0] - 2025-08-02

### 💥 BREAKING CHANGES

#### Code Interpreter Download Behavior Overhaul

- **File downloads now disabled by default** for Code Interpreter to optimize for the common use case (computation over file generation)
- **New `--ci-download` flag** provides explicit control over file downloads - add this flag when you need to save generated charts, reports, or data files locally
- **Deprecated `auto_download` config option** - use `--ci-download` CLI flag instead for clearer intent and better performance
- **Performance improvement**: Single-pass execution by default (~2-3s faster) with two-pass sentinel mode only when downloads are explicitly enabled
- **Migration required**: Existing commands that need file downloads must add `--ci-download` flag

**Migration Example:**

```bash
# OLD (files downloaded automatically)
ostruct run analysis.j2 schema.json --enable-tool code-interpreter

# NEW (explicit flag for file downloads)
ostruct run analysis.j2 schema.json --enable-tool code-interpreter --ci-download
```

See migration guide: `docs/migration/auto-download.md`

### Added

- **CLI**: New `--ci-download` flag for explicit Code Interpreter file download control
- **Documentation**: Comprehensive migration guide for `auto_download` → `--ci-download` transition
- **Backward Compatibility**: Deprecation warnings for legacy `auto_download: true` config during transition period

#### 🔬 Data Science Integration Examples

- **Complete Example Suite**: New `examples/data-science/` directory with production-ready workflows:
  - **Analysis Pipeline**: CSV data processing with Code Interpreter integration (`examples/data-science/analysis/`)
  - **Market Entry Analysis**: Complex business analysis example with financial projections and regulatory data (`examples/data-science/integration/market-entry/`)
  - **Interactive Jupyter Integration**: Full `ostruct_data_analysis.ipynb` notebook with environment detection, experiment tracking, and chart display
  - **Self-Executing OST File**: `jupyter_integration.ost` for streamlined notebook integration
- **Development Infrastructure**: Makefiles, requirements files, and sample datasets for easy setup and testing
- **Documentation**: Comprehensive READMEs and integration guides for each example workflow

#### 🛠️ Dry-Run & API Key Validation Improvements

- **`--dry-run-json` UX Enhancement**: Flag now automatically enables dry-run mode - no need for redundant `--dry-run` flag

  ```bash
  # Before: ostruct run template.j2 schema.json --dry-run --dry-run-json
  # After:  ostruct run template.j2 schema.json --dry-run-json
  ```

- **API Key Validation in Dry-Run**: Dry-run mode now validates API key availability from all sources (CLI flag, environment variable, .env file)
- **Enhanced JSON Output**: `--dry-run-json` now includes `api_key_available` field for programmatic validation

#### 🛡️ Enhanced Code Interpreter File Download Reliability

- **Model-Specific Instructions**: Automatically inject tailored prompts for different models (gpt-4.1, gpt-4o, o4-mini) to improve file annotation reliability
- **Raw HTTP Download Fallback**: Direct HTTP downloads for container files when SDK limitations prevent normal file access
- **Container Expiry Detection**: Proactive detection and handling of expired Code Interpreter containers
- **Enhanced Error Classification**: Detailed error types with user-friendly messages and actionable suggestions
- **Exponential Backoff Retry Logic**: Automatic retries for transient download failures with intelligent backoff
- **Progress Integration**: Download progress reporting integrated with existing `--progress` flag system
- **Schema Validation Warnings**: Automatic warnings when Code Interpreter is enabled but schema lacks text fields for download links

#### 🤖 Intelligent Download Strategy Auto-Selection

- **Auto-Enable Two-Pass Sentinel**: ostruct now automatically enables the `two_pass_sentinel` download strategy when:
  - Code Interpreter is enabled
  - Structured output (JSON schema) is being used
  - `auto_download: true` (default)

  This works around a critical OpenAI API bug where structured output mode prevents file download annotations. The auto-enable behavior ensures files download successfully without manual configuration.

- **Smart Fallback Logic**: Users can still explicitly set `download_strategy: "single_pass"` in configuration to override the auto-enable behavior if needed.

#### 🔧 Developer Infrastructure

- **Comprehensive Testing Suite**: Mini-tests, integration tests, and performance benchmarks for CI download reliability
- **Enhanced Logging**: Detailed download attempt logging with credential sanitization
- **Memory Protection**: File size limits (100MB) to prevent memory exhaustion during downloads

#### 📚 Documentation Enhancements

- **General Troubleshooting Guide**: New comprehensive `docs/troubleshooting.md` covering installation, API connection, model issues, template problems, tool integration, and performance troubleshooting
- **Data Science Integration Guide**: New `docs/source/user-guide/data_science_integration.rst` with comprehensive Sphinx documentation for data science workflows
- **Developer CI Downloads Guide**: New `docs/developer-ci-downloads.md` with technical details for Code Interpreter file download implementation
- **Specialized Troubleshooting**: New `docs/troubleshooting-ci-downloads.md` focused on Code Interpreter download issues and solutions
- **Enhanced Documentation Cross-References**: Improved linking between troubleshooting guides, known issues, and developer documentation

### Changed

- **Default Behavior**: Code Interpreter file downloads disabled by default (breaking change)
- **Performance**: Faster single-pass execution when file downloads not needed
- **Configuration**: `auto_download: false` is now the default in `CODE_INTERPRETER` constants

- **Download Strategy**: Prioritizes raw HTTP downloads for container files over SDK methods due to better reliability
- **Error Messages**: More specific and actionable error messages for download failures
- **Progress Reporting**: File downloads now integrate with existing progress system instead of separate implementation

### Deprecated

- **Config**: `auto_download` setting in `tools.code_interpreter` configuration (use `--ci-download` flag instead)

### Fixed

#### 🛡️ Code Interpreter File Download Issues

- **Container File Downloads**: Resolved SDK limitations preventing download of `cfile_*` prefixed files from Code Interpreter
- **Structured Output Compatibility**: Fixed file download issues when using structured JSON output with Code Interpreter
- **Container Expiry Handling**: Improved detection and error messaging for expired Code Interpreter containers

#### 🛠️ Code Interpreter Tool Enablement

- **Tool Choice Without Files**: Fixed critical bug where `--enable-tool code-interpreter` and `--tool-choice code-interpreter` would fail with "Tool choice not found in tools parameter" when no files were uploaded
- **File-Free Code Execution**: Code Interpreter can now be enabled for model-generated files without requiring input file uploads
- **Valid Use Cases Restored**:
  - `ostruct run template.j2 schema.json --enable-tool code-interpreter` - Let the model create files from scratch
  - `ostruct run template.j2 schema.json --tool-choice code-interpreter` - Force Code Interpreter usage for data generation
- **Backward Compatibility**: All existing Code Interpreter workflows with file uploads continue to work unchanged

#### 🔧 MCP Server Configuration Validation

- **HTTP MCP Server Support**: Fixed validation error that prevented HTTP-based MCP servers from working with the `--mcp-server` flag
- **Unified Transport Support**: MCP server validation now properly supports both transport formats:
  - **STDIO format**: `{"name": "server-name", "command": "command-to-run"}` for local subprocess servers
  - **HTTP format**: `{"url": "https://server-url", "label": "optional-label"}` for remote HTTP/SSE servers
- **CLI Integration**: Resolved conflict between CLI MCP integration and service configuration validation systems
- **Backward Compatibility**: All existing STDIO MCP server configurations continue to work unchanged

### Technical Notes

- **Workaround Implementation**: Enhanced download features implement automatic workarounds for the known OpenAI Responses API issue documented in `docs/known-issues/2025-06-responses-ci-file-output.md`
- **Future Removal**: Auto-enable logic will be removed when OpenAI resolves the underlying API bug
- **Performance Impact**: Two-pass execution and enhanced reliability features add ~2-3 seconds to structured output requests but ensure reliable file downloads

## [1.5.0] - 2025-07-30

### Added

#### 🎯 Major Feature: File Management System

- **Complete File Upload Management**: Introduced comprehensive `ostruct files` command group for managing uploaded files and cache:
  - `files upload` - Upload files with tool bindings (user-data, code-interpreter, file-search), tags, and vector store assignment
  - `files list` - List cached files with advanced filtering by tool, tags, vector store, and customizable column display
  - `files gc` - Garbage collect old cache entries with configurable TTL (e.g., `--older-than 30d`)
  - `files bind` - Bind existing cached files to additional tools without re-uploading
  - `files rm` - Delete remote files and purge from local cache
  - `files diagnose` - Live diagnostic probes (head/vector/sandbox tests) for troubleshooting file issues
  - `files vector-stores` - List available vector stores and their contents
- **Advanced File Display**: Smart path truncation, responsive table formatting, and customizable column layouts for better file inventory management
- **JSON Output Support**: All file commands support `--json` flag for programmatic integration and automation

#### 🔧 Enhanced CLI Organization

- **Models Command Group**: Introduced `ostruct models` command group with better organization:
  - `ostruct models list` - List available OpenAI models with table/JSON/simple output formats
  - `ostruct models update` - Update model registry with force option and progress reporting
- **Dynamic Deprecation Warnings**: Legacy commands (`list-models`, `update-registry`) now show dynamic version warnings indicating exact removal version

#### 🎨 Template System Enhancements

- **New File Attachment Helpers**: Modern template functions for file handling workflows:
  - `attach_file(path)` - Attach files for binary access (vision/code interpreter)
  - `get_file_ref(path)` - Get deterministic file labels for consistent referencing
  - `embed_text(alias)` - Schedule text content for XML appendix embedding
  - `get_embed_ref(alias)` - Get reference tags for embedded content
- **Upload Cache Integration**: Template environment now has access to upload cache for intelligent file labeling and metadata
- **Comprehensive Template Documentation**: Updated llms.txt with complete reference of all template functions and filters

### Changed

#### 🚨 Template Filter Cleanup

- **Deprecated Functions**: `file_ref()` function deprecated in favor of new `embed_text()` + `get_embed_ref()` pattern with clear migration path
- **Removed Deprecated Filters**: Cleaned up template system by removing unused filters:
  - `remove_comments`, `wrap`, `indent`, `dedent` (text processing)
  - `files` (file sequence protocol)
  - `dir_of`, `len_of`, `validate_json`, `format_error` (utility functions)

#### 📊 Improved Error Handling & JSON Output

- **Comprehensive File Error System**: Specific error types for common file issues (FileNotFoundError, DirectoryNotFoundError, PermissionError, BrokenSymlinkError) with actionable error messages
- **Standardized JSON Output**: Consistent JSON formatting across all commands with metadata, timestamps, and structured error reporting
- **Enhanced Progress Reporting**: Unified progress indicators across all CLI commands with configurable verbosity levels

#### 🔧 CLI Infrastructure Improvements

- **Modular Utilities Structure**: Reorganized CLI utilities into focused modules for better maintainability and testing
- **Rich-Click Integration**: Improved argument parsing and error handling with better user experience
- **Smart Path Handling**: Intelligent path truncation for readable file displays in terminal output

### Fixed

#### 🔍 Template Processing

- **File Reference Validation**: Improved validation of file references and labels in templates
- **Upload Cache Management**: Better integration between template system and file upload cache

### Improved

#### 📚 Documentation & Known Issues

- **OpenAI File-Search Issue**: Documented known upstream issue where OpenAI Responses API file_search returns empty results despite successful vector store creation
- **CLI Documentation**: Updated llms.txt with complete FILES command documentation and template function reference
- **Enhanced Examples**: Updated agent examples with improved architecture documentation and execution flow details. Not ready yet though.

#### 🔒 Security & Reliability

- **File Validation**: Enhanced file existence and permission checking with specific error types
- **Path Security**: Improved path handling and security validation across file operations
- **Error Recovery**: Better error recovery and user guidance for common file and permission issues

### Dependencies

- **Updated Core Dependencies**:
  - `click>=8.2.1` (improved CLI framework)
  - `pytest-asyncio>=0.25.2,<2.0` (better async test support)
- **Added New Dependencies**:
  - `tabulate>=0.9.0,<0.10.0` (table formatting for file listings)
  - `questionary>=2.0.0,<3.0.0` (interactive prompts)
  - `types-tabulate` (type checking support)

### Deprecated

- **Legacy Commands**: `ostruct list-models` and `ostruct update-registry` are deprecated and will be removed in v1.6.0. Use `ostruct models list` and `ostruct models update` instead.
- **Template Functions**: `file_ref()` function is deprecated. Use the new `embed_text()` + `get_embed_ref()` pattern for better control and clarity.

### Migration Notes

#### File Management

- **New Capability**: Use `ostruct files upload` to pre-upload and manage files with specific tool bindings and metadata
- **Cache Management**: Use `ostruct files list` to view your upload cache and `ostruct files gc` for cleanup
- **Troubleshooting**: Use `ostruct files diagnose <file_id>` to test file accessibility across different tools

#### Template Updates

- **Replace deprecated file_ref()**:

  ```jinja2
  <!-- Old (deprecated) -->
  {{ file_ref("docs") }}

  <!-- New (recommended) -->
  {{ embed_text("docs") }}
  Reference: {{ get_embed_ref("docs") }}
  ```

#### CLI Command Updates

- **Model Management**:

  ```bash
  # Old (deprecated)
  ostruct list-models
  ostruct update-registry

  # New (recommended)
  ostruct models list
  ostruct models update
  ```

This release significantly enhances ostruct's file management capabilities, provides better CLI organization, and improves the overall user experience while maintaining backward compatibility through clear deprecation paths.

## [1.4.1] - 2025-07-21

### Added

- **llms.txt file**: Added standardized llms.txt file following llmstxt.org format for LLM consumption with complete CLI documentation and technical reference

### Improved

- **Storyboard-to-VEO3 Example**: Enhanced documentation and usability for video production automation pipeline

## [1.4.0] - 2025-01-20

### Added

#### 🎯 Major Feature: OST (Self-Executing Templates)

- **Complete OST implementation** - Self-executing ostruct prompts that bundle templates, schemas, and CLI configuration into single executable files
- **`ostruct runx` command** - Execute OST files with custom command-line interfaces
- **Dynamic CLI generation** - OST files automatically generate custom CLIs with argument validation and help
- **Global argument policies** - Configure allowed, blocked, fixed, and pass-through modes for ostruct flags
- **Cross-platform execution** - Unix shebang support + Windows file associations via `ostruct setup windows-register`
- **OST Generator tool** - Automated creation of OST files from existing templates and schemas
- **Comprehensive validation** - Front-matter parsing, schema validation, and error reporting
- **Self-documenting workflows** - Each OST file provides custom `--help` output and usage examples

### Changed

- File attachment documentation enhanced with practical examples
- File metadata now properly exposed on LazyFileContent objects
- CLI reference updated with comprehensive OST documentation

### Improved

- **Scaffold Templates**: Enhanced template generation with improved Jinja2 templates that follow ostruct patterns, include proper front-matter system prompts, and use defensive variable handling
- **Documentation**: Added comprehensive scaffold command documentation to CLI reference guide with usage examples and best practices

### Fixed

- Improved error message for invalid Jinja2 template syntax
- Import organization and code quality improvements

### Security

- Comprehensive DoS protection suite addressing multiple attack vectors:
  - Template size limits with configurable thresholds
  - JSON parsing size limits to prevent memory exhaustion
  - Symlink depth restrictions to prevent traversal attacks
  - ReDoS protection with safe regex patterns
  - Upload manager memory leak fixes
  - Credential sanitization to prevent API key exposure
  - Unicode path traversal prevention
  - Global security context management

### Removed

- Unused template variable name generation function

### Dependencies

- Updated `pyfakefs` to 5.9.1 for improved test reliability
- Updated `jinja2` to 3.1.6 for enhanced template processing security

## [1.3.0] - 2024-12-04

### Added

- **User-Data Workflow**: New ``ud:`` / ``user-data:`` attachment target for PDF uploads to vision-enabled models:
  - Direct PDF processing using OpenAI's vision capabilities for both text and image-based PDF documents
  - Remote URL support for processing PDFs from web sources with security validation
  - 512 MB hard limit and 50 MB warning threshold with early validation
  - Model capability validation with descriptive errors for non-vision models

- **URL Security Controls**: Comprehensive security for remote file attachments:
  - Strict HTTPS & public-network enforcement for remote attachments
  - ``--allow-insecure-url`` flag to whitelist specific HTTP or private URLs
  - ``--strict-urls/--no-strict-urls`` toggle to globally enable/disable validation

- **Enhanced Template Error Analysis**: Improved debugging and validation for template development:
  - Advanced error detection and reporting for template syntax issues
  - Integration with template validation system for better developer experience
  - Enhanced error messages with actionable guidance for template fixes

- **Pitch-Distiller Example**: Comprehensive startup pitch deck analysis example with two-pass analysis system and industry taxonomy integration

- **Enhanced File Type Detection**: Optional magika integration for improved auto-routing accuracy:
  - Added `enhanced-detection` optional dependency for advanced file type detection using Google's magika library
  - Intelligent fallback to extension-based detection when magika is unavailable
  - Improves auto-routing accuracy for `--file auto:` target with content-based detection
  - Cross-platform compatibility with graceful degradation on Alpine Linux and other environments
  - Install with `pip install ostruct-cli[enhanced-detection]` for enhanced capabilities
  - Works seamlessly with existing extension-based detection as fallback

### Changed

- **Schema Limits**: Raised OpenAI Structured Outputs schema limits to match July 11 2025 announcement: object properties 5,000 (was 100), enum values 1,000 (was 500), total enum characters 15,000 (was 7,500). Updated validator constants, templates, docs, and added boundary unit tests.

### Fixed

- **Template Rendering**: Resolved various template rendering bugs and improved error handling
- **Schema Validation**: Enhanced schema validation with dynamic model creation during dry-run
- **File Routing**: Corrected file routing metadata for File Search attachments
- **Schema Processing**: Fixed JSON serialization issues and improved schema definition propagation

### Improved

- **Dry-Run Display**: Enhanced execution plan display with URL reachability validation and clearer attachment routing information
- **Binary Detection**: Added comprehensive binary file detection and handling
- **Error Messages**: Improved user experience with better error messages and guidance

### Documentation

- **CLI Reference**: Updated with new targets, flags, examples, and user-data limits
- **Security Overview**: Expanded with URL validation rules and user-data safeguards
- **Advanced Patterns**: Added remote PDF user-data example and enhanced template guidance
- **Test Coverage**: Added comprehensive test coverage for new features and file routing scenarios

### Internal

- **Examples Infrastructure**: Standardized example testing with consistent Makefile interface across all examples
- **Shared Logging Library**: Replaced problematic log4sh with modern `lib/simple_logging.sh` for reliable script logging
- **Development Tools**: Enhanced example organization and removed private agent example from public documentation

## [1.2.0] - 2025-07-06

(Minor-breaking change: default template file-size limit raised from 64 KB to unlimited; see "Changed" section.)

### Added

- **User-Visible Cache Indicators**: Enhanced user experience with clear feedback on upload cache usage:
  - **Progress Indicators**: Cache hits displayed as "♻️ Reusing cached upload for..." with file age and hash information in detailed mode
  - **End-of-Run Summary**: Cache performance summary showing hit/miss rate, space saved estimates, and cache database location
  - **Non-Intrusive Design**: Cache information appears only when relevant, maintaining clean output for cache-disabled workflows
  - **Detailed Mode Support**: Enhanced cache hit reporting with file hash and age information via `--verbose` flag

- **Configurable JSON Parsing Strategy**: Robust handling of OpenAI API duplication bugs with user control:
  - **Automatic Recovery**: Default "robust" mode automatically handles OpenAI's intermittent JSON duplication bug where responses contain duplicate concatenated objects
  - **Configuration Options**: `json_parsing_strategy` setting in `ostruct.yaml` and `OSTRUCT_JSON_PARSING_STRATEGY` environment variable
  - **Strict Mode**: Optional "strict" mode for environments requiring strict JSON validation (fails on malformed JSON)
  - **Community References**: Includes links to OpenAI community discussions about the duplication issue
  - **Comprehensive Documentation**: New known issue document with technical details, workaround implementation, and removal plan

- **Upload Cache System**: Comprehensive persistent caching system for Code Interpreter and File Search uploads:
  - **SQLite Backend**: Hash-based file deduplication with cross-platform support and corruption recovery
  - **TTL Management**: Configurable cache lifetime with automatic expiration and cleanup
  - **CLI Integration**: New `--cache-uploads/--no-cache-uploads` flag and `--cache-path` option for cache configuration
  - **Configuration Support**: Environment variables (`OSTRUCT_CACHE_*`) and `ostruct.yaml` settings for persistent cache behavior
  - **Performance Benefits**: Eliminates redundant uploads for frequently used files across sessions
  - **Cache Statistics**: Comprehensive monitoring and reporting of cache performance and storage usage
  - **Thread Safety**: Robust concurrent access handling for multi-tool scenarios

- **--tool-choice** CLI flag allowing explicit control over assistant tool usage (values: `auto`, `none`, `required`, `code-interpreter`, `file-search`, `web-search`).
- **Documentation and tests for the new flag.

### Changed

- **Breaking: File Size Limit Configuration**: Changed default behavior for file size limits in template processing:
  - **Default Changed**: `OSTRUCT_TEMPLATE_FILE_LIMIT` environment variable default changed from 64KB to unlimited
  - **New Semantic Values**: Environment variable now supports "unlimited", "none", and empty string (all meaning no limit)
  - **CLI Option Added**: New `--max-file-size` option with size suffixes (KB, MB, GB) and semantic values
  - **Configuration Support**: Added `template.max_file_size` setting in `ostruct.yaml` for persistent configuration
  - **Enhanced Tool Integration**: Templates now automatically receive `file_search_enabled` variable for conditional logic
  - **Migration**: Users who need the old 64KB limit should set `OSTRUCT_TEMPLATE_FILE_LIMIT=64KB` or use `--max-file-size 64KB`

### Improved

- **Path Security Warnings**: Enhanced user experience for file access warnings with comprehensive improvements:
  - **User-Friendly Messages**: Replaced technical "PathOutsidePolicy" warnings with clear, actionable security notices
  - **Contextual Guidance**: Warnings now include specific CLI flags (--allow, --allow-file, --path-security) to resolve the issue
  - **Smart Deduplication**: Each external file triggers only one warning per session, eliminating repetitive warning spam
  - **File Type Detection**: Contextual messages identify file types (document, data file, downloaded file) for better user understanding
  - **Configuration Support**: Added ostruct.yaml configuration options for warning behavior (suppress_path_warnings, warning_summary)
  - **Thread Safety**: Warning system is safe for concurrent file access scenarios

### Fixed

- **Token Validation for Multi-Tool Scenarios**: Fixed context window validation bug that incorrectly counted tool files (Code Interpreter, File Search) as template content:
  - **Accurate Token Counting**: Tool files are now excluded from context window validation as they consume tokens differently than template files
  - **Multi-Tool Support**: Complex workflows with --file ci: and --file fs: attachments no longer fail with false "context window exceeded" errors
  - **Backward Compatibility**: Template-only files continue to be validated normally for context window limits
  - **Documentation**: Added comprehensive documentation explaining tool token consumption behavior

## [1.1.0] - 2025-06-30

### Added

- **Gitignore Support**: Automatic .gitignore pattern matching for directory file collection
  - **CLI Options**: New `--ignore-gitignore` flag to disable gitignore filtering and `--gitignore-file PATH` to specify custom gitignore files
  - **Environment Variables**: `OSTRUCT_IGNORE_GITIGNORE` and `OSTRUCT_GITIGNORE_FILE` for default behavior configuration
  - **Configuration Support**: New `file_collection` section in `ostruct.yaml` with `ignore_gitignore` and `gitignore_file` options
  - **Pattern Matching**: Uses `pathspec` library for robust gitignore pattern matching following Git's behavior
  - **Documentation**: gitignore guide with usage examples, patterns, and troubleshooting
  - **Security Benefits**: Automatically excludes sensitive files (`.env`, API keys) and build artifacts from directory collection

- **Enhanced AIF Visualization**: Improved argument analysis visualization tools
  - **Interactive Mermaid Diagrams**: Added clickable nodes and full text comments for better visualization
  - **Script Improvements**: Fixed path references and enhanced output formatting

### Changed

- **Global Flag Behavior**: `--recursive` and `--pattern` flags now apply to ALL `--dir` and `--collect` attachments instead of only the last attachment, providing more intuitive and consistent behavior
- **Default Directory Processing**: Directory file collection now respects `.gitignore` patterns by default for improved security and cleaner file sets (can be disabled with `--ignore-gitignore`)
- **Dry-Run JSON Output**: Improved attachment type detection in dry-run mode, correctly identifying `directory`, `file`, and `collection` attachment types

### Fixed

- **Test Reliability**: Adjusted performance test thresholds from 0.1s to 0.2s to account for CI environment variability while still catching real performance regressions
- **CLI Integration**: Fixed dry-run JSON format validation and schema requirements for better test compatibility
- **Type Safety**: Resolved path handling issues in plan assembly for collection attachments

### Dependencies

- **Added**: `pathspec (>=0.12.1,<0.13.0)` for gitignore pattern matching

## [1.0.3] - 2025-06-29

### Documentation

- **Major Documentation Reorganization**: Restructured documentation from 25 pages to 13 focused pages with improved navigation
  - Consolidated template documentation into 3 comprehensive guides (template_guide.rst, template_quick_reference.rst, advanced_patterns.rst)
  - Created unified tool_integration.rst covering Code Interpreter, File Search, Web Search, and MCP servers
  - Merged automation content (4→2 pages) and contributing section (5→3 pages)
  - Extracted CLI content from index.rst to cli_reference.rst
  - Fixed all Sphinx build warnings and broken cross-references
  - Achieved zero-warning documentation builds

### Security

- **Security Scanning Configuration**: Implemented solution for handling intentionally vulnerable example code:
  - **Dependabot Configuration**: Added `.github/dependabot.yml` to disable dependency updates for vulnerability demonstration examples
  - **Security Policy**: Created `SECURITY.md` documenting intentional vulnerabilities in `examples/security/vulnerability-scan/` directory
  - **Scanner Suppression**: Enhanced vulnerable example files with security scanner suppression comments (`# nosec`, `# noqa: S`, `# NOSONAR`)
  - **Git Attributes**: Configured `.gitattributes` to mark vulnerability examples as documentation to reduce automated scanning
  - **Clear Documentation**: Added prominent warnings and explanations that vulnerabilities in security examples are intentional for educational purposes

## [1.0.2] - 2025-06-28

### Fixed

- **Read the Docs Build Compatibility**: Complete resolution of documentation build failures on Read the Docs:
  - **Sphinx Extension Registration**: Added `sphinx_rtd_theme` to Sphinx extensions list in `conf.py`, required for Sphinx 8+ theme discovery
  - **Explicit Package Installation**: Added explicit pip installation of `myst-parser`, `sphinx-design`, and `sphinx-rtd-theme` in Read the Docs build configuration to ensure package availability
  - **Documentation Dependencies**: Restored key documentation dependencies to the `docs` optional-dependencies section for environments that rely on the extras mechanism
  - **Lock File Consistency**: Updated `poetry.lock` to reflect the documentation dependency changes

This release ensures both "stable" and "latest" documentation builds work correctly on Read the Docs with Sphinx 8.x.

## [1.0.1] - 2025-06-28

### Fixed

- **Sphinx 8 Compatibility**: Updated documentation build system for compatibility with Sphinx 8.x:
  - **Theme Dependency Update**: Updated `sphinx-rtd-theme` from 2.0.x to 3.0+ which supports Sphinx 8
  - **Sphinx Version Range**: Updated Sphinx version constraints from `<8.0` to `<9.0` to allow Sphinx 8.x
  - **Dependency Resolution**: Updated `poetry.lock` with compatible package versions
  - **Configuration Cleanup**: Removed incorrect `sphinx_rtd_theme` from extensions list (themes are not extensions in older Sphinx versions)

This release resolves Read the Docs build failures that occurred when Read the Docs upgraded to Sphinx 8.2.3.

## [1.0.0] - 2025-06-28

### Added

- **Enhanced Code Interpreter Download System**: Comprehensive improvements to file download reliability and user experience:
  - **Duplicate File Handling**: New `--ci-duplicate-outputs` CLI option and `duplicate_outputs` config setting with three strategies: `overwrite` (default), `rename` (generates unique names like file_1.txt), and `skip` (ignores existing files)
  - **Early Validation**: Download directory permissions and configuration validated during dry-run and startup, catching issues before API calls
  - **Improved Error Handling**: Specific error classes (`DownloadPermissionError`, `DownloadNetworkError`, `DownloadFileNotFoundError`) with actionable troubleshooting guidance
  - **Enhanced Dry-Run Coverage**: Download configuration validation included in execution plans with directory status and permission checks

- **Centralized Configuration System**: Streamlined configuration management with consistent defaults and improved maintainability:
  - **Default Model Update**: Changed default model from `gpt-4o` to `gpt-4.1` for enhanced reasoning capabilities and larger context windows
  - **Unified Constants**: Centralized all default values, paths, and configuration options in a single location for consistency
  - **Enhanced Configuration Options**: Added support for new Code Interpreter features including duplicate handling and output validation
  - **Improved Developer Experience**: Better type definitions and IDE support for configuration management

- **Reorganized Examples Library**: Complete restructuring of examples for better discoverability and learning progression:
  - **Categorical Organization**: Examples now organized into logical categories - analysis/, automation/, debugging/, integration/, security/, tools/, and utilities/
  - **Focused Learning Path**: Each category provides a clear progression from basic to advanced usage patterns
  - **Reduced Maintenance Overhead**: Consolidated overlapping examples and removed outdated patterns that don't align with current best practices
  - **Better Tool Integration**: Examples now demonstrate proper multi-tool usage with Code Interpreter, File Search, Web Search, and MCP servers
  - **Improved Documentation**: Each example category includes clear README files with usage guidance and learning objectives

- **Enhanced Template System**: Improved template processing with better file handling and user experience:
  - **Advanced Template Filters**: New filters for better file reference handling and data processing in templates
  - **Improved Error Handling**: Better error messages and debugging support for template development
  - **Enhanced Integration**: Seamless integration between template system and new download/file handling features
  - **Rich CLI Output**: Improved formatting and visual presentation of CLI output and help text

- **Development Tools and Build System**: Streamlined development workflow with new tools and simplified build processes:
  - **Schema Generator Tool**: New development tool for automatically generating JSON schemas from templates, reducing manual schema creation effort
  - **Template Analyzer Tool**: Advanced template analysis tool for debugging complex templates and understanding template behavior
  - **Simplified Build Process**: Removed complex build scripts in favor of standard Python packaging, making the project easier to contribute to
  - **Enhanced Documentation**: Updated documentation to reflect current best practices and removed outdated installation methods

- **File Reference System**: Introduced `file_ref("alias")` function for clean, structured file references in templates. Files are automatically organized into XML appendices, eliminating the need for manual file content loops in templates. Works seamlessly with existing `--dir`, `--file`, and `--collect` attachments.

- **Enhanced Template Debugging**: Comprehensive template debugging system with granular capacity control:
  - Consolidated 8 overlapping debug flags into single `--template-debug` (`-t`) flag
  - Capacity-based debugging: `vars`, `preview`, `steps`, `optimization`, `pre-expand`, `post-expand`, `optimization-steps`
  - Consistent output prefixes (`[VARS]`, `[TPL]`, `[OPTIM]`, `[STEP]`, `[PRE]`, `[PREVIEW]`, `[OPTIM-STEP]`) for easy parsing
  - Improved template expansion tracking and variable inspection
  - Usage: `-t vars,preview` for specific capacities, `-t all` or bare `-t` for complete debugging

- **Safe Nested Access**: Added `safe_get()` function for safe nested attribute access in templates, preventing errors when accessing potentially undefined nested properties. Replaces verbose conditional boilerplate with clean single-line calls.

- **Dynamic Model Validation**: Enhanced model selection with real-time validation against OpenAI's model registry, ensuring compatibility and providing helpful error messages for unsupported models.

- **Enhanced Examples Testing Infrastructure**: Comprehensive automated testing system for all examples:
  - **Auto-Discovery**: Automatically discovers and tests all examples following EXAMPLES_STANDARD.md specification
  - **Dual Testing Modes**: Fast dry-run validation (no API calls) and live API testing with `@pytest.mark.live` for cost control
  - **Structure Validation**: Ensures examples follow standard structure (README.md, templates/, schemas/, run.sh with standard_runner.sh)
  - **CI/CD Integration**: Seamlessly integrates into pytest test suite for continuous validation of 9+ examples across analysis, tools, integration, security, and utilities categories
  - **Cross-Platform Compatibility**: Works with pyfakefs and handles subprocess calls reliably across different development environments

- **Comprehensive Examples**: Added extensive example collection demonstrating real-world usage patterns:
  - File reference examples with security audit, code review, and data analysis templates
  - Multi-tool integration examples showing file routing to different services
  - Template debugging examples with various complexity levels
  - Updated existing examples to demonstrate new `file_ref()` patterns

- **Experimental --help-json Flag**: Added experimental JSON help output for programmatic CLI integration:
  - **Hidden Flag**: `--help-json` flag available but hidden from help output (not ready for public use)
  - **Structured Output**: Outputs complete command help in JSON format for tools and automation
  - **Dynamic Model Information**: Includes real-time model registry metadata and validation details
  - **Attachment System Documentation**: Comprehensive JSON documentation of file routing targets and syntax
  - **Note**: JSON format designed for eventual public API but subject to (and will) change

- **Enhanced CLI Help System**: Integrated rich-click for beautiful, modern CLI help output with:
  - Color-coded help text with professional styling and organized option groups
  - Rich-formatted panels with borders and visual separation for better readability
  - Structured option grouping (Template Data, Model Configuration, File Attachment, Tool Integration, etc.)
  - Enhanced error messages with improved formatting and user guidance
  - Terminal UI automatically adapts to terminal capabilities

- **Quick Reference System**: Added `--quick-ref` flag for instant access to common usage patterns and examples:
  - Rich-formatted quick reference with visual panels and syntax highlighting
  - Comprehensive file attachment examples showing all routing targets
  - Multi-tool integration patterns with real command examples
  - Environment variable reference with clear categorization
  - Replaces the previous `ostruct quick-ref` command with integrated help flag

### Changed

- **Progress Options Simplification**: Merged `--no-progress` and `--progress-level` flags into a single `--progress [none|basic|detailed]` option for a cleaner, more intuitive CLI interface. This eliminates redundancy and follows standard CLI patterns where a single option controls related functionality.

- **Simplified CLI Syntax**: Updated all examples and documentation to use thes simplified attachment system with explicit file routing (`--file ci:`, `--dir fs:`, etc.) instead of legacy flags.

- **Comprehensive Error Categorization System**: Revolutionary error handling with intelligent categorization and solutions:
  - **13 Specific Error Categories**: FILE_FORMAT_ERROR, API_KEY_ERROR, SCHEMA_ERROR, TEMPLATE_ERROR, and 9 others for precise problem identification
  - **Actionable Solutions**: Each error provides primary and alternative solutions with corrected command examples
  - **Context-Aware Messaging**: Errors include relevant context (file paths, line numbers, configuration details) for faster troubleshooting
  - **Exit Code Mapping**: Consistent exit codes (USAGE_ERROR=2, DATA_ERROR=3, VALIDATION_ERROR=4, etc.) for reliable automation integration

- **Enhanced CLI Reference with Better Examples**: Comprehensive improvements to CLI documentation and error handling:
  - **Dynamic Model Validation**: Real-time validation against OpenAI model registry with helpful suggestions for invalid models
  - **Rich Error Messages**: Clean, user-friendly error display without technical stack traces for common issues
  - **Better Template Error Messages**: Proper variable name extraction from Jinja2 errors with actionable feedback
  - **Improved Schema Validation**: Enhanced schema validation feedback with specific guidance for common issues

- **Documentation Overhaul**: Complete documentation update including:
  - Comprehensive file reference system guide with usage examples
  - Template debugging documentation with capacity explanations
  - Updated CLI reference with all new options and examples
  - Template structure guide for advanced template authoring
  - Examples showing both manual file access and automatic `file_ref()` approaches

- **Streamlined Installation**: Removed complex installation script in favor of standard methods (pipx, Homebrew, Docker), with automated Homebrew formula updates on release.

- **MCP Environment Variables**: Changed MCP environment variable pattern from `MCP_<NAME>_URL` to `OSTRUCT_MCP_URL_<name>` for consistency with other ostruct environment variables (e.g., `OSTRUCT_MCP_URL_stripe` instead of `MCP_STRIPE_URL`). This provides better namespace isolation and follows the established `OSTRUCT_*` pattern used by other environment variables like `OSTRUCT_DISABLE_REGISTRY_UPDATE_CHECKS`.

- **YAML Frontmatter Configuration Updates**: Clarified configuration requirements for template frontmatter:
  - **Model and Temperature Restriction**: Model and temperature parameters must be specified via CLI flags (`--model gpt-4.1 --temperature 0.7`) and are not supported in YAML frontmatter
  - **System Prompt Support**: YAML frontmatter continues to support `system_prompt` and `include_system` configuration options
  - **Documentation Updates**: Updated all template documentation to reflect CLI-only requirement for model parameters
  - **Conflict Detection**: Added warning when both YAML frontmatter system_prompt and `--sys-file` are provided, with CLI taking precedence

- **Template Environment Variables**: Renamed template-specific environment variables for clarity:
  - `OSTRUCT_MAX_FILE_SIZE` → `OSTRUCT_TEMPLATE_FILE_LIMIT` (controls individual file size limits for template access)
  - `OSTRUCT_MAX_TOTAL_SIZE` → `OSTRUCT_TEMPLATE_TOTAL_LIMIT` (controls total file size limits for template processing)
  - `OSTRUCT_PREVIEW_LIMIT` → `OSTRUCT_TEMPLATE_PREVIEW_LIMIT` (controls template debugging preview character limits)

  These variables only affect template file access (via `--file alias path`) and do not impact Code Interpreter (`--file ci:`) or File Search (`--file fs:`) file routing. The new names clearly indicate their template-specific scope.

### Fixed

- **Configuration and Test Reliability**: Resolved critical configuration and testing issues that were causing failures in CI/CD environments:
  - **Default Model Alignment**: Fixed test suite to properly expect `gpt-4.1` as the default model, ensuring consistency between code and tests
  - **Import and Type Safety**: Resolved duplicate import issues and type annotation problems that were causing runtime errors
  - **Cross-Environment Compatibility**: Improved test reliability across different development environments by removing dependencies on external tools like poetry where not available
  - **Error Handling**: Enhanced error handling with proper exit codes and user-friendly error messages

- **Template Rendering**: Fixed template environment creation and validation issues that were causing mypy errors and rendering failures.

- **File Processing**: Resolved issues with file routing and processing, including proper handling of large files and elimination of inappropriate warnings for Code Interpreter and File Search usage.

- **Code Interpreter Downloads**: Significantly improved reliability of file downloads from Code Interpreter with robust fallback mechanisms and proper API integration.

- **Security Enhancements**: Multiple security improvements including:
  - Robust Azure endpoint validation using proper hostname parsing
  - Enhanced MCP response sanitization
  - Improved symlink security validation with resolved path checks
  - Better path traversal protection

- **CLI Consistency**: Updated argument handling throughout examples and scripts to use consistent simplified syntax, replacing deprecated flags like `--fta`, `--fca`, `-dc`, `-R` with current equivalents.

### Removed

- **Template Optimization System**: Completely removed the automatic template optimization system (1,104 lines of code) that had functional overlap with the new `file_ref()` mechanism. This includes:
  - Deleted `template_optimizer.py` module entirely
  - Removed `--no-optimization` CLI flag and related parameters
  - Eliminated automatic template content reorganization and appendix generation
  - Removed optimization-related debug capacities (`optimization`, `optimization-steps`)
  - Cleaned up optimization progress reporting and help text
  - Updated template debugging system to remove optimization-specific functions
  - The explicit `file_ref()` system provides cleaner, more predictable template organization

- **Legacy Flags**: Removed deprecated `--web-search` and `--no-web-search` flags in favor of universal `--enable-tool` and `--disable-tool` flags.

- **Streaming Support**: Removed unnecessary streaming support from OpenAI API calls to improve model compatibility (especially o3/o1 models) and reduce code complexity while maintaining identical user experience.

- **Placeholder Files**: Cleaned up dummy/placeholder files from examples that were causing build issues without providing value.

- **Quick Reference Command**: Removed `ostruct quick-ref` command in favor of the new `--quick-ref` flag, which provides the same functionality with enhanced rich formatting and better integration with the main CLI help system.

### Security

- **Enhanced Validation**: Strengthened security across multiple areas:
  - Improved Azure endpoint validation to prevent false positives
  - Enhanced MCP server response sanitization
  - Better symlink resolution and path validation
  - Robust dependency installation with proper error handling

### Migration Notes

For a comprehensive migration guide with examples and automated migration scripts, see [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md).

- **Template Optimization**: The automatic template optimization system has been removed. Users should migrate to the explicit `file_ref()` system:
  - Templates that relied on automatic optimization should now use `file_ref("alias")` for structured file references
  - The `--no-optimization` flag is no longer available (and no longer needed)
  - Template debugging capacities `optimization` and `optimization-steps` have been removed

- **File References**: Users can now choose between two approaches:
  - `file_ref("alias")` for automatic XML appendix generation (recommended for most use cases)
  - Direct file access with `{{ alias.content }}` for custom formatting needs

- **Template Debugging**: Replace old debug flags with new capacity-based system:
  - Old: `--debug-template --show-vars --show-preview`
  - New: `-t vars,preview` or `-t all`

- **CLI Syntax**: Update to simplified attachment syntax if still using legacy flags:
  - Old: `--fta alias file.txt`
  - New: `--file alias file.txt`

- **MCP Environment Variables**: Update your environment variable names:
  - Old: `MCP_STRIPE_URL=https://mcp.stripe.com`
  - New: `OSTRUCT_MCP_URL_stripe=https://mcp.stripe.com`
  - Old: `MCP_CUSTOM_URL=https://my-server.com`
  - New: `OSTRUCT_MCP_URL_custom=https://my-server.com`

- **Template Environment Variables**: Update template-specific environment variable names:
  - `OSTRUCT_MAX_FILE_SIZE` → `OSTRUCT_TEMPLATE_FILE_LIMIT`
  - `OSTRUCT_MAX_TOTAL_SIZE` → `OSTRUCT_TEMPLATE_TOTAL_LIMIT`
  - `OSTRUCT_PREVIEW_LIMIT` → `OSTRUCT_TEMPLATE_PREVIEW_LIMIT`

  These variables control template file processing limits and do not affect Code Interpreter or File Search operations.

- **Quick Reference Access**: The `ostruct quick-ref` command has been replaced with the `--quick-ref` flag:
  - Old: `ostruct quick-ref`
  - New: `ostruct --quick-ref`

  The new flag provides the same reference information with enhanced rich formatting and better visual organization.

## [0.8.9] - 2025-06-12

### Added

- **Comprehensive Template Documentation**: Added a new, in-depth `ostruct_template_scripting_guide.rst` to the documentation, covering all aspects of ostruct's templating system. Also added a `template_quick_reference.rst` for quick lookups.
- **Special Character Support in CLI**: Added a `fix_surrogate_escapes` utility to automatically correct UTF-8 encoding issues in command-line arguments. This fixes bugs when using filenames or arguments containing non-ASCII characters (e.g., en dashes, accents).
- **Template Convenience**: Added an `.extension` property to `FileList` objects, providing a convenient way to access a file's extension in templates when working with a single file (e.g., `{{ my_file.extension }}`).

### Changed

- **Simplified and Automated Installation**: Streamlined and automated the project's distribution channels. The Homebrew formula is now updated automatically on release, Docker builds are more reliable, and the custom macOS installation script has been removed in favor of standard methods (`pipx`, `Homebrew`, binaries, Docker). See `README.md` for updated installation instructions.
- **Documentation Improvements**: Revamped the `template_authoring.rst` guide to use the new, canonical script invocation patterns and variable naming conventions.
- **File Path Handling**: The `FileInfo.path` property now correctly returns absolute paths for files located outside the project's base directory, as long as they are within a directory explicitly allowed by the security manager.

### Fixed

- **System Prompt Errors**: Correctly initialized `SystemPromptError` to ensure it captures and reports errors related to system prompt processing properly.

## [0.8.8] - 2025-06-06

### Changed

- **Installation Script Distribution**: Updated all documentation to use `latest` release URL (`https://github.com/yaniv-golan/ostruct/releases/latest/download/install-macos.sh`) instead of version-specific URLs for future-proof installation instructions.
- **macOS Installation Script**: Added dynamic Python version fetching using endoflife.date API
  - Eliminates hardcoded Python URLs that require manual maintenance
  - Automatically installs the latest stable Python version with security patches
  - Uses fallback to Python 3.12.0 if API call fails
  - Simplified to use universal2 installers supporting both Intel and Apple Silicon

### Fixed

- **Installation Script Logic**: Fixed double-installation issue where script would install ostruct-cli via both pipx and pip. Added proper installation method tracking to prevent redundant installations.
- **pipx Fallback Support**: Added fallback to install pipx via pip when Homebrew is unavailable, improving installation success rate on systems without Homebrew.
- **Error Visibility**: Removed error suppression (`2>/dev/null`) from critical pip and ostruct commands to provide better diagnostic information for troubleshooting.
- **Version Checking**: Enhanced version verification with robust error handling and more cautious messaging when older versions are detected.
- **Homebrew Updates**: Added `brew update` calls before package installations to ensure latest package information and reduce installation failures.
- **User Communication**: Added warnings about Xcode Command Line Tools requirement and PEP 668 bypass when using `--break-system-packages`.
- **Python Installation**: Improved Python.org installer with version tracking, better error messages, and guidance for manual updates.

## [0.8.7] - 2025-06-06

### Fixed

- **Installation Script Build**: Fixed build script to create required directories during GitHub Actions workflow. The macOS installation script is now properly generated and available as a release asset.

## [0.8.6] - 2025-06-06

### Changed

- **Installation Script Distribution**: Modified GitHub Actions publish workflow to upload macOS installation script as release asset instead of committing to repository. Installation URL changed from raw GitHub URL to release asset: `https://github.com/yaniv-golan/ostruct/releases/download/v{VERSION}/install-macos.sh`

## [0.8.5] - 2025-06-06

### Added

- **macOS Installation Script**: Added comprehensive installation script with dynamic version management and industry-standard organization. The script automatically handles Python installation, PATH configuration, and ostruct setup on macOS. Features include Python 3.10+ installation via Homebrew or python.org, shell PATH configuration, pip cache clearing, and version verification. The script uses a template-based build system that automatically extracts the current version from `pyproject.toml`. Scripts are organized following industry best practices with separate directories for build automation, platform-specific installation, and categorized testing (unit/integration/docker). Users can install with: `curl -sSL https://github.com/yaniv-golan/ostruct/releases/latest/download/install-macos.sh | bash`

- **Centralized Dependency Installation Utilities**: Added comprehensive dependency management system in `scripts/install/dependencies/` with reusable utilities for installing common tools across examples. Features include `ensure_jq.sh` and `ensure_mermaid.sh` with multiple installation strategies (system package managers, direct binary downloads, Docker wrappers), cross-platform support (Linux, macOS, Windows), environment variable controls (`OSTRUCT_SKIP_AUTO_INSTALL`, `OSTRUCT_PREFER_DOCKER`), and comprehensive testing framework. This eliminates code duplication across examples and provides consistent, reliable tool installation.

- **Enhanced Argument Interchange Format (AIF) Support**: Major enhancement to the `arg_to_aif` example with a complete AIF extension system for advanced argument visualization. Features include:
  - **AIF Extension System**: Backward-compatible extensions with semantic categories (premise, evidence, conclusion, inference, conflict), relationship types (supports, conflicts, infers, attacks, relates), and display names for compact visualization
  - **Advanced Mermaid Visualization**: Color-coded diagrams with semantic node styling, enhanced edge labels showing argument relationships, smaller fonts allowing 80 characters per node, and automatic SVG generation
  - **Enhanced Prompt Engineering**: Balanced prompt for complex academic arguments, explicit node-type guidance, proper use of all AIF node types (I, RA, CA, PA, MA), and support for 20-35 node structures for academic texts
  - **Model Parameter Support**: Configurable model selection with GPT-4.1 default for sophisticated reasoning
  - **Comprehensive Documentation**: Complete AIF extension specification in `AIF_EXTENSIONS.md` with usage examples and compatibility guidelines

- **Multi-Agent Debate Citation Enhancement**: Enhanced the multi-agent debate example with smart citation post-processing that automatically converts any AI citation format to clean academic-style numbered references. Features include:
  - **Smart Citation Processing**: Extracts inline citations from debate text and converts them to numbered references [1], [2], [3]
  - **URL Parameter Handling**: Flexible URL matching that handles query parameters (e.g., `?utm_source=openai`) for reliable citation identification
  - **Title Enhancement**: Merges inline citation positioning with structured citation metadata to provide meaningful titles instead of bare domain names
  - **Perfect Correspondence**: Maintains 1:1 correspondence between text references and citation list for clean, academic-style presentation
  - **Cross-Format Compatibility**: Works with any AI citation format, making debates more readable for technical audiences

- **Multi-Agent Debate GPT-4.1 Upgrade**: Upgraded the multi-agent debate example to use GPT-4.1 as the default model, providing 1M+ context window (vs 128k for GPT-4o), 32k max output (vs 16k), and enhanced reasoning capabilities for more sophisticated debate quality and handling of larger, more complex discussions.

- **Professional Build System**: Implemented comprehensive build automation and testing infrastructure:
  - **Makefile Integration**: Added dependency testing targets to main Makefile with `test-dependencies` for automated validation
  - **Cross-Platform Scripts**: Organized script structure with platform-specific installation, build automation, and categorized testing (unit/integration/docker)
  - **Template-Based Build System**: Dynamic version management that automatically extracts current version from `pyproject.toml`

### Changed

- **Dependency Management**: Migrated from scattered `ensure_*.sh` scripts across examples to centralized utilities in `scripts/install/dependencies/`. Examples now source shared utilities instead of maintaining duplicate installation logic, reducing maintenance overhead and ensuring consistency.

- **Documentation Structure**: Added `DEPENDENCY_UTILITIES.md` (renamed from `DEPENDENCY_MANAGEMENT.md`) with comprehensive documentation for the new dependency installation system, including usage patterns, environment variables, and testing procedures.

### Fixed

- **Code Duplication**: Eliminated duplicate dependency installation scripts across examples (removed `examples/multi_agent_debate/scripts/ensure_*.sh` files) in favor of centralized utilities.

- **Build System Organization**: Restructured scripts directory following industry best practices with separate directories for build automation (`scripts/build/`), platform-specific installation (`scripts/install/`), and categorized testing (`scripts/test/`).

### Security

- **Dependency Installation**: Enhanced security in dependency installation utilities with proper error handling, validation of download sources, and fallback mechanisms to prevent installation of compromised tools.

## [0.8.4] - 2025-06-05

### Added

- **Environment File Support**: Added automatic loading of `.env` files from the current directory. Environment variables defined in `.env` files are automatically loaded at startup, with command-line environment variables taking precedence over `.env` file values. This provides a convenient way to manage API keys and configuration without exposing them in command history or process lists.

### Changed

- **Simplified Timeout Parameters**: Streamlined timeout handling to use a single `--timeout` parameter for OpenAI API calls (default: 60 seconds). Removed the complex dual timeout system that previously caused parameter conflicts and user confusion. The CLI now has cleaner, more intuitive timeout behavior.

## [0.8.3] - 2025-06-05

### Added

- **Universal Tool Toggle Flags**: Added `--enable-tool` and `--disable-tool` CLI flags for controlling tool enablement across all built-in tools (code-interpreter, web-search, file-search, mcp). These flags are repeatable, take highest precedence over all other configuration methods, and work for the current run only. Example: `--enable-tool web-search --disable-tool code-interpreter`. Conflicts between enabling and disabling the same tool are detected and reported as errors.
- **Feature Flags**: Added `--enable-feature` and `--disable-feature` CLI flags for experimental features. Currently supports `ci-download-hack` to enable/disable the Code Interpreter file download workaround on a per-run basis, overriding configuration file settings.
- **Multi-Agent Debate Example**: Added comprehensive multi-agent evidence-seeking debate example in `examples/multi_agent_debate/` demonstrating structured debates between PRO and CON agents with web search integration. Features include command-line topic arguments, self-installing dependencies (jq, Mermaid CLI), dual visualizations (interactive HTML + colorful SVG diagrams), color-coded agents and relationships, topic-centered diagram flow, and clean file organization. Showcases ostruct's latest CLI syntax, JSON schema validation, and cross-platform auto-installation capabilities.
- **Improved File Processing**: Enhanced file routing to eliminate inappropriate large file warnings when using Code Interpreter (`-fc`, `--fca`) and File Search (`-fs`, `--fsa`) flags. Large file warnings now only appear for template-only files where they're actually relevant. Also fixed duplicate file mapping errors when the same file is processed multiple times.
- **Reliable Code Interpreter File Downloads**: Significantly improved file download reliability for Code Interpreter workflows. Files generated by Code Interpreter are now automatically detected and downloaded using OpenAI's latest API format, with robust fallback mechanisms to ensure downloads work consistently across different scenarios.

### Deprecated

- **Tool Enablement Flags**: The `--web-search` and `--no-web-search` flags are now deprecated in favor of the universal `--enable-tool web-search` and `--disable-tool web-search` flags. The old flags will be removed in v0.9.0. Deprecation warnings are shown when the old flags are used.

### Fixed

- **Template Optimization Bug**: Fixed template optimizer incorrectly processing single-file variables accessed via `.content` (e.g., `{{ argument_text.content }}`) as directory references, which caused them to be replaced with "the files and subdirectories in <dir:variable>" instead of actual file content. The `--fta` flag now works correctly for any alias name, not just those containing specific keywords like "file" or "config". This resolves issues where custom variable names would be misprocessed during template optimization.
- **Code Interpreter File Downloads**: Fixed Code Interpreter file downloads to work with OpenAI's structured output mode. Implemented a two-pass sentinel workaround for OpenAI's bug where `response_format` with JSON schema prevents `container_file_citation` annotations, blocking file downloads. The solution uses a configurable two-pass execution strategy: (1) raw API call without structured output to generate files and annotations, (2) download files using the Container Files API, (3) extract JSON from sentinel markers for schema compliance. Added `download_strategy` configuration option (default: "single_pass" for backward compatibility, "two_pass_sentinel" to enable the workaround). Implemented robust Container Files API integration with dual-approach strategy (primary: `client.containers.files.content()`, fallback: raw HTTP requests) to handle OpenAI SDK variations. Files generated by Code Interpreter are now reliably downloaded across all models when using structured output mode. CLI flags `--enable-feature ci-download-hack` and `--disable-feature ci-download-hack` provide per-run control over this workaround.
- **File Routing Intent Bug**: Fixed incorrect large file warnings for Code Interpreter and File Search files. Also fixed duplicate file mapping error that occurred when the same file was processed twice from both CLI args and routing result by adding proper deduplication logic.
- **Template Error Messages**: Fixed issue where internal class names like `ostruct.cli.file_list.FileInfoList` were appearing in user-facing template error messages. Error messages now properly extract variable names from Jinja2 errors and provide clean, actionable feedback.
- **Large File Warning Timing**: Fixed large file warnings to trigger when file content is actually accessed (via `.content` property) rather than during FileInfo initialization, ensuring warnings appear at the appropriate time and are properly captured by test frameworks.
- **Streaming Support Removal**: Removed unnecessary streaming support from OpenAI API calls to improve model compatibility (especially o3/o1 models) and reduce code complexity. The streaming implementation provided no user benefits since all responses were buffered anyway, but created compatibility issues with newer models. This change eliminates ~300 lines of complex chunk processing code while maintaining identical user experience and improving reliability. All functionality is preserved with simplified non-streaming API calls.
- **Error Handling Display**: Fixed error handling logic that was showing Python tracebacks for user input errors (schema validation, JSON parsing, etc.). User-facing errors now display clean, actionable messages without technical stack traces, while preserving detailed logging for debugging with `--verbose` flag.

## [0.8.2] - 2025-06-01

### Fixed

- **Documentation Accuracy**: Audit and correction of all documentation files to ensure they accurately reflect the actual codebase implementation
- **Style Guide**: Updated coding standards to match actual project configuration (Black line-length 79 vs documented 88, correct error class names, actual API patterns)
- **CLI Examples**: Fixed several CLI syntax examples throughout documentation to use correct flag syntax (--fta instead of incorrect -ft two-argument usage)
- **API Documentation**: Corrected mocking examples to use OpenAI Responses API instead of Completions API, matching actual ostruct implementation
- **Cross-References**: Fixed broken documentation cross-references and removed references to non-existent files
- **Sphinx Warnings**: Resolved all Sphinx build warnings including title underline length issues
- **Code Examples**: Updated all code examples to use the updated classes, functions, and import paths from the codebase

## [0.8.1] - 2025-06-01

### Added

- **Web Search Integration**: Added documentation for web search functionality across all relevant documentation files
- **Examples**: Linked docs to existing web-search example to demonstrate real-time information retrieval capabilities

### Fixed

- **Documentation Build**: Fixed Read the Docs configuration to use `pip install -e ".[docs]"` instead of `poetry install --with docs` to properly install documentation dependencies from `pyproject.toml` optional-dependencies format
- **Documentation**: Updated all multi-tool integration references to include Web Search alongside Code Interpreter, File Search, and MCP servers
- **CLI Reference**: Added Web Search integration section with usage examples and privacy notices
- **Quick Reference**: Added web search tool and example to quick reference command

## [0.8.0] - 2025-06-01

### Added

- **Multi-Tool Integration**:
  - Introduced explicit file routing options (`-ft`, `-fc`, `-fs`, `--fta`, `--fca`, `--fsa`, `-dt`, `-dc`, `-ds`, `--dta`, `--dca`, `--dsa`) to direct files to specific tools: template context, Code Interpreter, or File Search. This provides granular control over file processing and data flow, especially concerning uploads to external services.
  - Added the `--file-for TOOL PATH` option (repeatable), enabling a file to be routed to a specific tool. To route one file to multiple tools, repeat the flag (e.g., `--file-for code-interpreter shared.json --file-for file-search shared.json`).
  - Enhanced template context to include tool-specific file objects (e.g., `code_interpreter_files`, `file_search_files_raw`) providing metadata about files processed by these tools.

- **Code Interpreter Integration**:
  - Integrated native support for OpenAI\'s Code Interpreter, allowing for Python code execution, data analysis, and visualization generation within ostruct workflows.
  - New CLI options for Code Interpreter: `--file-for-code-interpreter` (`-fc`), `--file-for-code-interpreter-alias` (`--fca`), `--dir-for-code-interpreter` (`-dc`), `--dir-for-code-interpreter-alias` (`--dca`), `--code-interpreter-cleanup` (default: true), and `--code-interpreter-download-dir`.
  - Core logic implemented in `src/ostruct/cli/code_interpreter.py`.

- **File Search Integration**:
  - Integrated native support for OpenAI\'s File Search, enabling vector-based semantic search and retrieval over user-provided documents.
  - New CLI options for File Search: `--file-for-search` (`-fs`), `--file-for-search-alias` (`--fsa`), `--dir-for-search` (`-ds`), `--dir-for-search-alias` (`--dsa`), `--file-search-cleanup` (default: true), `--file-search-vector-store-name`, `--file-search-retry-count`, and `--file-search-timeout`.
  - Core logic implemented in `src/ostruct/cli/file_search.py`.

- **Model Context Protocol (MCP) Integration**:
  - Added support for connecting to external Model Context Protocol (MCP) servers, allowing ostruct to leverage specialized external tools and knowledge bases.
  - New CLI options for MCP: `--mcp-server`, `--mcp-allowed-tools`, `--mcp-require-approval`, and `--mcp-headers` for authentication and custom request parameters.
  - Core logic implemented in `src/ostruct/cli/mcp_integration.py`.

- **Configuration System**:
  - Introduced a YAML-based configuration file (default: `ostruct.yaml` in the current directory or `~/.ostruct/config.yaml`, or a path specified by `--config`) for persistent settings related to models, tools, operational parameters, and cost limits.
  - Implemented direct loading of specific environment variables (e.g., `OPENAI_API_KEY`, `OSTRUCT_MCP_URL_<name>`) within the configuration system. Generic `${ENV_VAR}` style substitution within the YAML is not supported.
  - New CLI option: `--config` to specify a custom configuration file path.

- **Progress Reporting**:
  - Implemented real-time, granular progress indicators for long-running operations such as file processing, API interactions, and tool executions, enhancing user experience for complex tasks.
  - New CLI options: `--progress-level` (options: none, basic, detailed) and `--no-progress` to control the verbosity of progress updates.
  - Core logic implemented in `src/ostruct/cli/progress_reporting.py`.

- **Cost Estimation and Control**:
  - Integrated token usage estimation based on `tiktoken` and model-specific pricing for OpenAI API calls.
  - The `--dry-run` option has been enhanced to display estimated token counts and approximate costs without making actual API calls.
  - Introduced configuration options in `ostruct.yaml` for `max_cost_per_run` (to fail operations exceeding a budget) and `warn_expensive_operations` (to alert users).
  - Core logic implemented in `src/ostruct/cli/cost_estimation.py`.

- **Security Enhancements**:
  - Path Security: Strengthened file access controls through the `SecurityManager`. This includes mandatory validation of paths against explicitly allowed directories (specified via `-A`, `--allow`, or `--allowed-dir-file`) and a configurable base directory (`--base-dir`) for resolving relative paths.
  - Symlink Resolution: Improved and safer symlink handling within `SecurityManager` to prevent path traversal vulnerabilities by resolving symlinks to their canonical paths before validation.
  - Tool-Specific File Routing: Enforced strict file routing, requiring users to explicitly designate files for Code Interpreter or File Search. This prevents accidental uploading of sensitive files intended only for local template processing.
  - MCP Security: Added validation for MCP server URLs (requiring HTTPS) and mechanisms for approval (`--mcp-require-approval`) and secure authentication via custom headers (`--mcp-headers`) when connecting to external MCP services.

- **Template Filters and Globals**:
  - Added a comprehensive suite of new Jinja2 filters for advanced text manipulation (e.g., `word_count`, `char_count`, `remove_comments`, `strip_markdown`, `wrap`), data processing (e.g., `to_json`, `from_json`, `sort_by`, `group_by`, `unique`, `single`), table formatting (`table`, `dict_to_table`), and code processing (e.g., `format_code`, `strip_comments`).
  - Introduced new Jinja2 global functions for utility tasks such as `estimate_tokens`, `now` (current datetime), `validate_json`, `summarize`, and `pivot_table`.

- **CLI Improvements**:
  - Enhanced `--help` output across commands for improved clarity, providing better descriptions and examples for the new, extensive options.
  - Introduced the `ostruct quick-ref` command, offering users a concise summary of the new file routing options and their syntaxes.
  - Added new utility commands: `ostruct list-models` to display available OpenAI models from the registry and `ostruct update-registry` to refresh the local model registry.
  - Improved error handling with more specific error messages and standardized exit codes, providing better context for troubleshooting and integration into automated workflows.
  - Added new debugging options: `--debug-validation` (for detailed schema validation errors) and `--debug-openai-stream` (for inspecting raw OpenAI API stream data).
  - Comprehensive template debugging infrastructure (`--debug-template`, `--show-templates`, etc.).
  - `OSTRUCT_DISABLE_REGISTRY_UPDATE_CHECKS` environment variable to control update notifications.

- **Documentation**:
  - Developed comprehensive user guides covering new features, including an updated CLI reference, guides for tool integration (Code Interpreter, File Search, MCP), security best practices, CI/CD automation patterns, and containerization.
  - Added a rich set of examples in the `examples/` directory, demonstrating practical use cases for the new multi-tool capabilities, configuration system, and advanced CLI options.
  - Meta-Schema Generator example for automated JSON schema creation.

- **Template System**:
  - Template Optimization: Automatic prompt optimization for better LLM performance.
  - Shared System Prompts: New `include_system:` feature for sharing common system prompt content.

- **File Handling**:
  - Binary File Handling: Restored lazy loading for binary files in dry-run.
  - Windows Compatibility: Enhanced file routing for Windows.

- **Token Management**:
  - Added 90% token usage warning threshold.

### Changed

- **File Routing (Critical Change)**: The legacy file input flags (`-f`, `-d`, `-p`) are now considered aliases, primarily for template-only access (equivalent to `-ft`, `-dt`). While backward compatibility is maintained, users are **strongly encouraged** to adopt the new explicit routing flags (e.g., `-ft`, `-fc`, `-fs`, and their directory/alias counterparts like `--fca`, `-ds`) for clarity, security, and to leverage new tool integrations. This change is fundamental to how ostruct handles files, especially concerning data uploads to OpenAI services.
- **Default Model**: The default OpenAI model has been updated to `gpt-4o`.
- **Error Handling**: Standardized error messages and exit codes across the application to provide more consistent and actionable feedback for users and automation scripts. Enhanced error messages provide actionable file routing guidance.
- **Logging**: Enhanced logging capabilities with more granular control. Verbose logging now offers deeper insights into internal operations and API interactions.
- **Dependencies**:
  - Removed `openai-structured` dependency in favor of direct OpenAI SDK integration (`openai==1.81.0`).
  - Updated `tiktoken` (to `v0.9.0`) and `openai-model-registry` (to `v0.7.0`).
  - Introduced new dependencies such as `aiohttp` and `python-magic`.
- **Project Structure**: Reorganized the `src/ostruct/cli/` directory into a more modular structure, with dedicated subdirectories for commands and security, and new modules for each major feature.
- **Schema Validation**: Schema validation against the provided JSON Schema is now more aligned with OpenAI\'s specific requirements for structured outputs, such as enforcing a root object type and `additionalProperties: false`.
- **Template Context**: Template context now includes files from all routing options.

### Fixed

- **Critical**: Resolved Click framework limitations for variable argument file routing.
- **Critical**: Fixed template variable collision issues with comprehensive file naming.
- **Critical**: Resolved directory routing design flaw - generic templates can now use stable variable names with directory alias syntax.
- **Critical**: Made `FileInfoList` scalar properties (`.content`, `.path`, `.abs_path`, `.size`, `.name`) strict single-file only, raising `ValueError` for multiple files. **Migration required**: Use `.names` for lists, iterate, or use `|single` filter.
- Improved handling of large template files, reducing the likelihood of exceeding token limits by more efficient internal processing.
- Enhanced input validation for various CLI arguments, providing clearer error messages for incorrect usage.
- Addressed issues related to special characters in file paths causing errors on certain operating systems.
- Refined logging mechanisms for API calls to aid in debugging.
- Corrected path traversal detection in Unicode safety patterns to correctly handle valid filenames that contain multiple dots, while still preventing malicious inputs.
- Fixed whitespace handling in variable (`-V`) and JSON variable (`-J`) validators.
- Resolved a potential infinite recursion issue within the `PathSecurityError.details` property getter.
- Restored binary-safe lazy loading to prevent unnecessary content loading during dry-run.
- Enhanced file routing with better error handling and validation.
- Improved template variable optimization with proper file attribute references.
- Standardized Python version requirements across CI/CD (Python 3.10+).

### Removed

- The `ostruct init` command has been deprecated and removed. Project initialization is now achieved through manual creation of template/schema files and the optional `ostruct.yaml` configuration file.
- Implicit file routing behaviors have been removed. Files intended for Code Interpreter or File Search must now be explicitly routed using the appropriate flags (e.g., `-fc`, `-fs`). This change enhances security by preventing unintentional data uploads.
- The `--verbose-schema` option has been removed. Detailed schema validation information is now part of the `--debug-validation` output.
- The generic directory extension flag `--ext` has been renamed to `--dir-ext` to clarify its application to directory processing only.

### Security

- Enhanced overall path security with more comprehensive validation logic within the `SecurityManager`, including stricter checks for allowed directories and base path resolution.
- Improved prevention of directory traversal attacks through robust path normalization and safe joining utilities.
- Strengthened symlink resolution mechanisms to detect and block potentially malicious symlinks pointing outside of allowed areas.
- Introduced explicit CLI flags for routing files to external services (Code Interpreter, File Search), ensuring users make conscious decisions about data uploads and reducing the risk of accidental data exposure.
- Added security considerations for MCP server integration, including support for custom headers (e.g., for API keys/Bearer tokens) and controls for restricting allowed tools per server (`--mcp-allowed-tools`, `--mcp-require-approval`).

### Migration Notes

- **FileInfoList API**: The `.content`, `.path`, `.name`, etc. properties on `FileInfoList` objects are now strict single-file only. Accessing them on a list with multiple files will raise a `ValueError`.
  - To get a list of names: `{{ my_files.names }}`
  - To access content of the first file: `{{ my_files[0].content }}`
  - To ensure a single file and get its content: `{{ (my_files|single).content }}`
- **CLI `--file-for` syntax**: Changed from `tool:path` to `tool path` for Windows compatibility.
- **Dependencies**: `openai-structured` has been removed.

## [0.7.2] - 2025-03-07

### Fixed

- Added missing Jinja2 dependency which is used for template rendering

## [0.7.1] - 2025-03-07

### Fixed

- Added missing Pygments dependency to fix startup errors when invoking the CLI
- Updated openai-structured dependency to version 3.0.0 to resolve Pydantic protected namespace warnings
- Improved error handling for missing dependencies

## [0.7.0] - 2025-03-01

### Added

- Added non-intrusive registry update checks with user notifications
- Added ability to disable registry update checks via environment variable
- Added support for GPT-4.5 models

### Changed

- Updated openai-structured dependency to version 2.1.0

## [0.6.2] - 2025-02-22

### Added

- Added clear documentation for system prompt precedence rules in README
- Added detailed logging configuration section with command-line options and environment variables
- Added ostruct logo assets in multiple formats (SVG, PNG at 1x, 2x, 3x resolutions)
- Added comprehensive etymology analysis example with documentation and schemas
- Added enhanced path validation and security checks

### Changed

- Changed comment block handling to explicitly reject nested comments for simpler, more predictable syntax
- Improved whitespace handling in variable parsing for better user experience
- Updated SecurityManager documentation for clarity
- Updated project description in README for better clarity and focus on core functionality
- Enhanced schema validation and error handling
- Updated Python version requirement to 3.10 and bumped openai-structured dependency

### Fixed

- Fixed path traversal detection in Unicode safety pattern to allow valid filenames with multiple dots
- Fixed whitespace handling in variable and JSON variable validators
- Fixed infinite recursion in PathSecurityError.details property

### Removed

- Removed outdated migration guide
- Removed temporary Read the Docs configuration file

## [0.6.0] - 2025-02-17

### Added

- Added shell completion support for command options and file paths
- Added comprehensive documentation with three detailed usage examples in README
- Added enhanced template context support for pattern-matched files

### Changed

- **Breaking:** Schema validation now enforces OpenAI compatibility rules
  - Root schemas must be of type 'object' (arrays must be wrapped in an object)
  - Improved error messages with examples and fixing instructions
- Enhanced error handling with more detailed context and troubleshooting tips
- Improved error messages for API responses and schema validation
- Pinned tiktoken to version 0.9.0 for better compatibility

### Fixed

- Fixed pattern-based file matching with `-p` or `--pattern` option for matching multiple files using glob patterns
- Improved type safety with better type hints and compatibility
- Enhanced error handling for API responses
- Fixed schema validation error reporting with more context
- Improved handling of OpenAI schema-specific errors

### Security

- Enhanced schema validation error messages to prevent exposure of sensitive information

## [0.5.0] - 2024-02-16

### Added

- Added support for o1 and o3 models with their specific parameter constraints.
- Added validation to prevent use of unsupported parameters for each model type.
- Added explicit type casting for Click commands with improved type hints.
- Added integration with [openai-structured v2.0.0](https://github.com/yaniv-golan/openai-structured) and its `openai_structured.model_registry` for better model capability management.
- Added more comprehensive test coverage for model validation and type safety.

### Changed

- **Major change to CLI structure:** Introduced the `run` subcommand.  The CLI no longer uses a single command format; instead, it's structured as `ostruct run <TASK_TEMPLATE> <SCHEMA_FILE> [OPTIONS]`. This provides better organization and extensibility.
- Enhanced parameter validation to ensure compliance with model-specific requirements.
- Changed default model to `gpt-4o`.
- Changed default temperature from 0.0 to 0.7.
- Upgraded minimum Python version requirement from 3.9 to 3.10.
- Updated MyPy configuration with more specific settings for different modules.
- Improved type safety throughout the codebase with `ParamSpec` and better type hints.
- Moved CLI command definition outside the `create_cli` function for better organization.
- Improved error messages for model parameter validation.
- Enhanced test infrastructure with better OpenAI test isolation.
- Improved error handling with consistent use of `ExitCode` enum.
- Improved handling of paths (relative to security manager's base directory).
- Changed the command-line options to use Click's option naming convention:
  - `--task-file` instead of using positional argument or `@` syntax.
  - `--schema-file` instead of using positional argument.
  - `--file name=path` now uses  `-f name path`
  - `--dir name=path` now uses `-d name path`
  - `--files name=pattern` now uses `-p name pattern`
  - `--dir-recursive` is now `-R` or `--recursive`
  - `--var name=value` is now `-V name=value`
  - `--json-var name=json` is now `-J name='json'`
  - `--system-prompt` is now `--sys-prompt`
  - `--system-prompt-file` is now `--sys-file`
  - `--ignore-task-sysprompt` is now `--ignore-task-sysprompt`
  - `--max-output-tokens` is now `--max-output-tokens`
  - `--verbose-schema` is removed. Schema is always validated. Validation details are now shown with `--debug-validation`.
  - `--ext` is renamed to `--dir-ext`, applying only to directory mappings.

### Fixed

- Fixed handling of model parameter validation to properly check supported parameters and their constraints.
- Removed duplicate `system_prompt` option from model_options to prevent conflicts.
- Fixed duplicate `mock_model_support` fixture in tests.
- Improved type checking and error messages in security-related tests.
- Enhanced `Path` object handling and type hints in test utilities.
- Fixed handling of fixed parameter models to completely prevent parameter overrides instead of trying to validate them.
- Fixed handling of `Path` objects in `safe_join` by converting them to strings.
- Fixed security error message formatting for better clarity.
- Fixed path handling inconsistencies in file collection utilities.

### Removed

- Removed has_fixed_parameters function and related tests as this concept is now handled by the model registry.
- Removed redundant test cases for stdin and directory input.
- Removed direct model parameter checks in favor of `ModelRegistry` usage.

### Security

- Enhanced path security checks with more comprehensive validation.
- Improved directory traversal prevention.
- Added more detailed security error messages with context.
- Enhanced validation of allowed directories and base paths.

## [0.4.0] - 2024-02-08

### Added

- Improved model handling with better support for non-streaming models
- Enhanced Windows path handling for better cross-platform compatibility
- Thread-safe file content handling in FileInfoList

### Fixed

- Resolved test failures in symlink behavior tests
- Improved error handling for permission and OS errors
- Enhanced content property error handling in FileInfo class
- Fixed ReadTheDocs project links
- Removed redundant code and unused type ignore comments

### Changed

- Refactored security module for better organization and maintainability
- Streamlined security test suite
- Improved code formatting and organization throughout the codebase

### Security

- Enhanced thread safety in file handling operations
- Improved permission checking and error handling for file operations

[0.4.0]: https://github.com/yaniv-golan/ostruct/compare/v0.3.0...v0.4.0

[0.5.0]: https://github.com/yaniv-golan/ostruct/compare/v0.4.0...v0.5.0

## [3.2.0] - 2025-01-01

### 🚨 BREAKING CHANGES

#### Template File Size Limits

- **Changed default behavior**: `OSTRUCT_TEMPLATE_FILE_LIMIT` now defaults to **unlimited** (was 64KB)
- **Reason**: The 64KB limit was artificially restricting template processing and preventing users from taking full advantage of large context windows
- **Migration**: If you need the old 64KB limit, set `OSTRUCT_TEMPLATE_FILE_LIMIT=65536` in your environment or config

### Added

- **Enhanced file size configuration**:
  - `--max-file-size` CLI option with support for size suffixes (KB, MB, GB)
  - Support for semantic values: `unlimited`, `none`, empty string for no limit
  - Configurable limits via CLI args, environment variables, and config files
  - Early validation in dry-run mode

- **Improved template tool integration**:
  - Automatic `file_search_enabled` variable detection
  - Enhanced AIF template with conditional multi-tool instructions
  - Better variable naming: `argument_file` (clearer than `argument_text`)
  - Smart content access for large documents

- **Better error handling**:
  - Clear warning messages for files exceeding limits
  - Graceful degradation with lazy loading
  - Informative error messages with suggested solutions

### Changed

- **Template processing**: Now supports unlimited file sizes by default
- **File size validation**: Enhanced to handle `None` values (unlimited)
- **Environment variable behavior**: `OSTRUCT_TEMPLATE_FILE_LIMIT` supports new semantic values

### Fixed

- **Large document processing**: Files over 64KB can now be processed directly
- **Tool variable detection**: `file_search_enabled` now properly set based on routing
- **Configuration consistency**: All file size settings now use consistent `None` for unlimited

### Technical Details

#### Core Changes

1. **LazyFileContent**: Enhanced `_get_default_max_size()` to return `None` by default
2. **Template Processor**: Added `file_search_enabled` to `_build_tool_context()`
3. **File Size Validator**: Updated to handle `None` values properly
4. **CLI Integration**: Added `--max-file-size` parameter with validation

#### Backward Compatibility

- Existing templates continue to work unchanged
- Legacy environment variable values still supported
- Graceful handling of invalid configuration values

#### Migration Examples

```bash
# Before (would fail for large files)
ostruct run template.j2 schema.json --file data large_document.pdf
# Error: File too large: 444,416 bytes > 65,536 bytes

# After (works by default)
ostruct run template.j2 schema.json --file data large_document.pdf
# ✅ Processes successfully

# To restore old behavior
OSTRUCT_TEMPLATE_FILE_LIMIT=65536 ostruct run template.j2 schema.json --file data document.pdf

# Or use CLI option
ostruct run template.j2 schema.json --file data document.pdf --max-file-size 64KB
```

## [3.1.0] - Previous Release

### Previous changes
