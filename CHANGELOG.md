# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.8.0] - 2025-05-31

### Added

- **Multi-Tool Integration**: Native support for OpenAI's Code Interpreter, File Search, and MCP servers
- **Hybrid File Routing Syntax**: Three flexible syntax options for file routing:
  - Auto-naming: `-ft config.yaml` → `config_yaml` variable
  - Equals syntax: `-ft app=config.yaml` → `app` variable
  - Two-argument alias: `--fta app config.yaml` → `app` variable (with perfect tab completion)
- **OpenAI Responses API Integration**: Direct integration with OpenAI Python SDK v1.81.0, replacing openai-structured wrapper
- **Enhanced CLI Interface**: New routing options (`-fc`/`--fca`, `-fs`/`--fsa`, `-ft`/`--fta`) with organized help system
- **Configuration System**: YAML-based configuration with environment variable support
- **Progress Reporting**: Real-time progress updates with user-friendly messaging
- **Template Optimization**: Automatic prompt optimization for better LLM performance
- **Shared System Prompts**: New `include_system:` feature for sharing common system prompt content across templates
- **Unattended Operation**: Full CI/CD compatibility with timeout controls and error handling
- **Cost Transparency**: Detailed cost reporting and token usage tracking

### Changed

- **Breaking**: Dropped Python 3.9 support (now requires Python 3.10+)
- **Breaking**: Removed openai-structured dependency in favor of direct OpenAI SDK integration
- **Enhanced**: Updated all examples with new multi-tool syntax options
- **Enhanced**: Improved error messages with actionable file routing guidance
- **Enhanced**: Template context now includes files from all routing options

### Fixed

- **Critical**: Resolved Click framework limitations for variable argument file routing
- **Critical**: Fixed template variable collision issues with comprehensive file naming
- **Critical**: Fixed FileInfoList API inconsistency - added adaptive `.name` property that returns scalar for single files, list for multiple files
- **Enhancement**: Added always-list `.names` property to FileInfoList for explicit list access
- **Enhancement**: Added `|single` Jinja2 filter for safe single-item extraction from lists with clear error messages
- **Enhancement**: Improved error messages when accessing FileInfo attributes on multi-file lists with specific guidance
- **Security**: Maintained all existing path validation and security controls
- **Performance**: Optimized file processing and template rendering

### Migration

- **100% Backward Compatible**: All existing `-f`, `-d`, `-p` commands work unchanged
- **Error-Driven Migration**: Clear guidance when commands exceed context limits
- **Progressive Enhancement**: Add new capabilities to existing workflows incrementally

### Technical

- **Validated Implementation**: All features validated through comprehensive probe testing
- **Performance Baseline**: Code Interpreter (10-16s), File Search (7-8s), basic operations (1-2s)
- **Architecture**: Explicit file routing system with tool-specific processing
- **Testing**: Enhanced test suite with proper OpenAI SDK mocking patterns

### Developer Experience

- **API Consistency**: FileInfoList now provides consistent adaptive behavior across all properties (name, content, path, abs_path, size)
- **Template Clarity**: All file variables are now explicitly FileInfoList instances with documented adaptive properties
- **Error Guidance**: Enhanced error messages include template variable names and suggest correct syntax patterns
- **Filter Safety**: New `|single` filter provides explicit validation for single-item expectations with descriptive errors

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
