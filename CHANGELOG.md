# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.0] - 2024-03-26

### Added

- Added support for fixed parameter models (o1, o3, and their variants)
- Added validation to prevent parameter modification for models with fixed parameters
- Added more comprehensive test coverage for model validation and type safety
- Added explicit type casting for Click commands with improved type hints

### Changed

- Enhanced parameter validation to ensure compliance with model-specific requirements
- Changed default model from gpt-4-turbo-preview to gpt-4o
- Changed default temperature from 0.0 to 0.7
- Upgraded minimum Python version requirement from 3.9 to 3.10
- Updated MyPy configuration with more specific settings for different modules
- Improved type safety throughout the codebase with ParamSpec and better type hints
- Moved CLI command definition outside the create_cli function for better organization

### Fixed

- Removed duplicate system prompt option from model_options to prevent conflicts
- Fixed duplicate mock_model_support fixture in tests
- Improved type checking and error messages in security-related tests
- Enhanced Path object handling and type hints in test utilities

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
