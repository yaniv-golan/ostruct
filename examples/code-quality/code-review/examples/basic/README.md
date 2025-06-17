# Basic Code Review Example

This directory contains a simple Python application (`app.py`) designed to demonstrate various code quality issues that can be detected through automated code review.

## Purpose

The `app.py` file is intentionally written with multiple code quality issues including:

- **Style Issues**: Inconsistent naming conventions (camelCase vs snake_case)
- **Performance Problems**: Inefficient algorithms (linear search, poor loop patterns)
- **Maintainability Issues**: Long functions, duplicated code, poor separation of concerns
- **Error Handling**: Bare except clauses, poor error messaging
- **Security Concerns**: Plain text password storage, weak input validation
- **Code Smells**: Magic numbers, global variables, hardcoded values

## Usage

This file is used in the code review example to demonstrate how ostruct can analyze code and provide structured feedback on quality issues.

### Example Command

```bash
ostruct run prompts/task.j2 schemas/code_review.json \
  --file code examples/basic/app.py \
  --sys-file prompts/system.txt
```

## Code Quality Issues Demonstrated

### Style and Convention Issues
- Mixed naming conventions (camelCase `addUser` vs snake_case `get_user`)
- Missing type hints in some places
- Inconsistent docstring formats

### Performance Issues
- Linear search through user list (`get_user` method)
- Modifying dictionary during iteration (`cleanup_old_sessions`)
- Inefficient batch processing with nested conditionals

### Security and Safety Issues
- Plain text password storage
- Weak email validation
- Information disclosure in exports
- Poor input validation

### Maintainability Issues
- Long functions with multiple responsibilities (`main`, `process_batch_users`)
- Duplicated validation logic
- Hardcoded configuration values
- Poor error handling patterns

This example provides a realistic codebase that code review tools can analyze to demonstrate their capabilities.