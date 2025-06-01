# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
  - Implemented direct loading of specific environment variables (e.g., `OPENAI_API_KEY`, `MCP_<NAME>_URL`) within the configuration system. Generic `${ENV_VAR}` style substitution within the YAML is not supported.
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
