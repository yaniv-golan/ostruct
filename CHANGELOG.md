# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.8.5] - 2025-06-06

### Added

- **macOS Installation Script**: Added comprehensive installation script with dynamic version management and industry-standard organization. The script automatically handles Python installation, PATH configuration, and ostruct setup on macOS. Features include Python 3.10+ installation via Homebrew or python.org, shell PATH configuration, pip cache clearing, and version verification. The script uses a template-based build system that automatically extracts the current version from `pyproject.toml`. Scripts are organized following industry best practices with separate directories for build automation, platform-specific installation, and categorized testing (unit/integration/docker). Users can install with: `curl -sSL https://raw.githubusercontent.com/yaniv-golan/ostruct/main/scripts/generated/install-macos.sh | bash`

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
