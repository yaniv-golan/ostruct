# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.0] - Unreleased

### Added

- Added support for O1/O3 models with their specific parameter constraints.
- Added validation to prevent use of unsupported parameters for each model type.
- Added explicit type casting for Click commands with improved type hints.
- Added integration with `openai_structured.model_registry` for better model capability management.
- Added more comprehensive test coverage for model validation and type safety.

### Changed

- Enhanced parameter validation to ensure compliance with model-specific requirements.
- Changed default model from `gpt-4-turbo-preview` to `gpt-4o`.
- Changed default temperature from 0.0 to 0.7.
- Upgraded minimum Python version requirement from 3.9 to 3.10.
- Updated MyPy configuration with more specific settings for different modules.
- Improved type safety throughout the codebase with `ParamSpec` and better type hints.
- Moved CLI command definition outside the `create_cli` function for better organization.
- Improved error messages for model parameter validation.
- Enhanced test infrastructure with better OpenAI test isolation.
- Improved error handling with consistent use of `ExitCode` enum.
- Improved handling of paths (relative to security manager's base directory).

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
