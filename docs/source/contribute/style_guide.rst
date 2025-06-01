=============
Style Guide
=============

This document outlines coding standards, documentation guidelines, and best practices for contributing to ostruct. Following these guidelines ensures consistency and maintainability across the codebase.

.. contents:: Table of Contents
   :local:
   :depth: 2

Python Coding Standards
=======================

Code Formatting
---------------

We use **Black** for code formatting with these settings:

.. code-block:: toml

   # pyproject.toml
   [tool.black]
   line-length = 79
   target-version = ["py310"]
   include = '\.pyi?$'
   extend-exclude = '''
   /(
     # Exclude generated files
     \.eggs
     | \.git
     | \.venv
     | _build
     | build
     | dist
   )/
   '''

**Key formatting rules:**

- Maximum line length: 79 characters
- Use double quotes for strings
- Trailing commas in multi-line structures
- Consistent indentation (4 spaces)

.. code-block:: python

   # Good
   def process_files(
       template_path: str,
       schema_path: str,
       output_file: Optional[str] = None,
   ) -> ProcessingResult:
       """Process files with the given template and schema."""
       return ProcessingResult(
           success=True,
           message="Processing completed successfully",
       )

Import Organization
-------------------

Use **isort** for import sorting with these guidelines:

.. code-block:: python

   # Standard library imports
   import asyncio
   import json
   from pathlib import Path
   from typing import Dict, List, Optional

   # Third-party imports
   import click
   import jinja2
   from pydantic import BaseModel

   # Local imports
   from ostruct.cli.errors import ValidationError
   from ostruct.cli.security import SecurityManager

**Import ordering:**

1. Standard library imports
2. Third-party library imports
3. Local application imports

**Import style:**

- Use absolute imports when possible
- Group imports logically
- Avoid wildcard imports (``from module import *``)
- Use explicit imports for clarity

Type Hints
----------

Use comprehensive type hints for better code clarity:

.. code-block:: python

   from typing import Dict, List, Optional, Union, Any
   from pathlib import Path

   # Function signatures
   def validate_config(
       config: Dict[str, Any],
       strict_mode: bool = False
   ) -> ValidationResult:
       """Validate configuration with optional strict mode."""

   # Class definitions
   class TemplateRenderer:
       """Renders Jinja2 templates with file content access."""

       def __init__(self, template_dir: Path) -> None:
           self.template_dir = template_dir
           self._cache: Dict[str, str] = {}

   # Complex types
   FileMapping = Dict[str, Union[str, Path]]
   ConfigDict = Dict[str, Union[str, int, bool, List[str]]]

Variable Naming
---------------

Follow Python naming conventions:

.. code-block:: python

   # Constants (module level)
   MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
   DEFAULT_MODEL = "gpt-4o"

   # Functions and variables
   def process_template_file(template_path: Path) -> str:
       file_content = template_path.read_text()
       processed_content = transform_content(file_content)
       return processed_content

   # Classes
   class SecurityManager:
       """Manages file access security and validation."""

   # Private methods/variables
   class TemplateProcessor:
       def __init__(self):
           self._template_cache = {}

       def _validate_template(self, content: str) -> bool:
           return bool(content.strip())

**Naming guidelines:**

- Use descriptive names that explain purpose
- Avoid abbreviations unless widely understood
- Use snake_case for functions and variables
- Use PascalCase for classes
- Use SCREAMING_SNAKE_CASE for constants
- Prefix private members with underscore

Docstrings
----------

Use comprehensive docstrings following Google style:

.. code-block:: python

   def render_template(
       template_path: Path,
       context: Dict[str, Any],
       strict_mode: bool = False
   ) -> str:
       """Render a Jinja2 template with the provided context.

       This function loads a Jinja2 template from the specified path and
       renders it with the given context variables. It supports both
       regular and strict rendering modes.

       Args:
           template_path: Path to the Jinja2 template file.
           context: Dictionary containing template variables.
           strict_mode: If True, raises errors for undefined variables.
               Defaults to False.

       Returns:
           The rendered template as a string.

       Raises:
           TemplateNotFoundError: If the template file doesn't exist.
           TemplateRenderError: If template rendering fails.
           ValidationError: If template contains invalid syntax.

       Example:
           >>> context = {"name": "ostruct", "version": "0.8.0"}
           >>> result = render_template(Path("template.j2"), context)
           >>> print(result)
           Hello, ostruct v0.8.0!
       """

**Docstring guidelines:**

- Start with a one-line summary
- Include detailed description if needed
- Document all parameters and return values
- List all possible exceptions
- Provide usage examples for complex functions
- Use present tense ("Returns the result" not "Will return")

Error Handling
==============

Exception Hierarchy
-------------------

Use the structured exception hierarchy from ``cli/errors.py``:

.. code-block:: python

   from ostruct.cli.errors import (
       CLIError,              # Base exception
       VariableError,         # Variable-related errors
       TaskTemplateError,     # Template processing errors
       PathSecurityError,     # Security-related errors
       SchemaError,          # Schema validation errors
   )
   from ostruct.cli.base_errors import OstructFileNotFoundError

   # Good - specific exception types
   def validate_file_path(path: str) -> Path:
       """Validate and return a Path object."""
       if not path:
           raise VariableError("File path cannot be empty")

       try:
           file_path = Path(path).resolve()
       except (OSError, ValueError) as e:
           raise PathSecurityError(f"Invalid file path '{path}': {e}")

       if not file_path.exists():
           raise OstructFileNotFoundError(path)

       return file_path

Error Messages
--------------

Provide clear, actionable error messages:

.. code-block:: python

   # Good - specific and actionable
   raise TaskTemplateError(
       f"Template file '{template_path}' is too large "
       f"({file_size} bytes). Maximum allowed size is {MAX_SIZE} bytes. "
       f"Consider splitting the template into smaller files."
   )

   # Bad - vague and unhelpful
   raise TaskTemplateError("Template error")

**Error message guidelines:**

- Include relevant context (file names, values)
- Suggest solutions when possible
- Use consistent terminology
- Avoid technical jargon in user-facing messages
- Include specific limits or constraints

Logging
-------

Use structured logging with appropriate levels:

.. code-block:: python

   import logging

   logger = logging.getLogger(__name__)

   def process_files(files: List[Path]) -> None:
       """Process multiple files with proper logging."""
       logger.info(f"Starting to process {len(files)} files")

       for file_path in files:
           logger.debug(f"Processing file: {file_path}")

           try:
               result = process_single_file(file_path)
               logger.info(f"Successfully processed {file_path}")
           except Exception as e:
               logger.error(
                   f"Failed to process {file_path}: {e}",
                   exc_info=True
               )
               raise

**Logging guidelines:**

- Use appropriate log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Include context in log messages
- Never log sensitive information (API keys, file contents)
- Use structured logging for machine-readable logs
- Log performance metrics for optimization

Security Guidelines
===================

Input Validation
----------------

Validate all inputs through the security layer:

.. code-block:: python

   from ostruct.cli.security import SecurityManager

   def process_user_files(file_paths: List[str]) -> None:
       """Process user-provided files with security validation."""
       security_manager = SecurityManager()

       for file_path in file_paths:
           # Always validate through security manager
           validated_path = security_manager.validate_file_access(file_path)

           # Process the validated path
           with validated_path.open('r') as f:
               content = f.read()
               process_content(content)

Path Handling
-------------

Use secure path operations:

.. code-block:: python

   from ostruct.cli.security import safe_join
   from ostruct.cli.security.symlink_resolver import _resolve_symlink

   def build_safe_path(base_dir: Path, user_path: str) -> Path:
       """Build a safe path within the base directory."""
       # Use safe_join to prevent directory traversal
       joined_path = safe_join(str(base_dir), user_path)
       if joined_path is None:
           raise PathSecurityError(f"Unsafe path: {user_path}")

       # Resolve symlinks securely
       resolved_path = _resolve_symlink(
           Path(joined_path),
           max_depth=16,
           allowed_dirs=[base_dir]
       )

       return resolved_path

**Security practices:**

- Never trust user input directly
- Use path normalization and validation
- Resolve symlinks securely
- Implement proper access controls
- Log security events for auditing

Testing Standards
=================

Test Organization
-----------------

Organize tests by functionality and scope:

.. code-block:: python

   import pytest
   from unittest.mock import patch, MagicMock
   from pathlib import Path

   from ostruct.cli.template_utils import render_template
   from ostruct.cli.errors import TaskTemplateError


   class TestTemplateRendering:
       """Tests for template rendering functionality."""

       @pytest.fixture
       def sample_template(self):
           """Create a sample template string."""
           return "Hello, {{ name }}!"

       @pytest.fixture
       def template_env(self):
           """Create a Jinja2 environment."""
           import jinja2
           return jinja2.Environment()

       def test_render_simple_template(self, sample_template, template_env):
           """Test rendering a simple template."""
           context = {"name": "World"}
           result = render_template(sample_template, context, template_env)
           assert result == "Hello, World!"

       def test_render_missing_variable(self, template_env):
           """Test error handling for missing variables."""
           template = "Hello, {{ missing_var }}!"
           with pytest.raises(TaskTemplateError):
               render_template(template, {}, template_env)

Test Coverage
-------------

Aim for comprehensive test coverage:

.. code-block:: python

   # Test happy path
   def test_successful_processing(self):
       """Test successful file processing."""

   # Test error conditions
   def test_invalid_input_raises_error(self):
       """Test that invalid input raises appropriate error."""

   # Test edge cases
   def test_empty_file_handling(self):
       """Test handling of empty files."""

   # Test boundary conditions
   def test_maximum_file_size_limit(self):
       """Test behavior at maximum file size limit."""

**Coverage guidelines:**

- Test both success and failure paths
- Include edge cases and boundary conditions
- Mock external dependencies (API calls, file system)
- Use parameterized tests for multiple scenarios
- Maintain at least 90% test coverage

Mocking Best Practices
----------------------

Use mocking effectively for external dependencies:

.. code-block:: python

   @patch('ostruct.cli.runner.AsyncOpenAI')
   def test_responses_api_call_success(self, mock_openai):
       """Test successful Responses API call with mocked client."""
       # Setup mock
       mock_client = AsyncMock()
       mock_openai.return_value = mock_client

       # Create mock streaming response for Responses API
       async def mock_stream():
           yield Mock(response=Mock(body='{"result": "test response"}'))

       mock_client.responses.create.return_value = mock_stream()

       # Test implementation
       result = await stream_structured_output(
           client=mock_client,
           model="gpt-4o",
           system_prompt="System prompt",
           user_prompt="User prompt",
           output_schema=TestSchema
       )

       # Verify behavior
       mock_client.responses.create.assert_called_once()
       # Verify API parameters
       call_args = mock_client.responses.create.call_args
       assert call_args[1]["model"] == "gpt-4o"
       assert "input" in call_args[1]  # Responses API uses 'input' not 'messages'
       assert "text" in call_args[1]   # Responses API uses 'text' format

Documentation Standards
=======================

reStructuredText Guidelines
---------------------------

Use consistent reStructuredText formatting:

.. code-block:: rst

   ===================
   Chapter Title
   ===================

   Section Title
   =============

   Subsection Title
   ----------------

   Subsubsection Title
   ^^^^^^^^^^^^^^^^^^^

   **Key formatting rules:**

   - Use underlines of the same length as the title
   - Maintain consistent heading hierarchy
   - Include table of contents for long documents
   - Use proper cross-references

Code Examples
-------------

Include comprehensive code examples:

.. code-block:: rst

   .. code-block:: bash

      # Example command with explanation
      ostruct run template.j2 schema.json \
        -fc source_code/ \
        -fs documentation/ \
        -ft config.yaml

   .. code-block:: python

      # Python code example
      from ostruct.cli import TemplateRenderer

      renderer = TemplateRenderer()
      result = renderer.render_template(template, context)

**Documentation guidelines:**

- Include working examples that can be copied and pasted
- Explain complex concepts with simple examples
- Use consistent terminology throughout
- Link to related sections and external resources
- Keep examples up to date with current API

API Documentation
-----------------

Document all public APIs comprehensively:

.. code-block:: python

   def render_template_with_context(
       template_content: str,
       context: Dict[str, Any],
       env: jinja2.Environment
   ) -> str:
       """Render a Jinja2 template with the provided context.

       This function provides a secure interface for rendering
       Jinja2 templates with file content access. It includes built-in
       security validation and optimization.

       Args:
           template_content: The template content as a string.
           context: Dictionary containing template variables.
           env: Jinja2 environment for rendering.

       Returns:
           The rendered template as a string.

       Raises:
           TaskTemplateError: If template rendering fails.

       Example:
           >>> import jinja2
           >>> env = jinja2.Environment()
           >>> context = {"name": "ostruct", "version": "0.8.1"}
           >>> result = render_template_with_context(
           ...     "Hello, {{ name }} v{{ version }}!", context, env
           ... )
           >>> print(result)
           Hello, ostruct v0.8.1!
       """

Performance Guidelines
======================

Async/Await Usage
-----------------

Use async/await for I/O operations:

.. code-block:: python

   import asyncio
   from typing import List

   async def process_files_async(file_paths: List[Path]) -> List[str]:
       """Process multiple files asynchronously."""
       tasks = [process_single_file(path) for path in file_paths]
       results = await asyncio.gather(*tasks, return_exceptions=True)

       # Handle results and exceptions
       processed_results = []
       for result in results:
           if isinstance(result, Exception):
               logger.error(f"Processing failed: {result}")
           else:
               processed_results.append(result)

       return processed_results

Caching Strategies
------------------

Implement appropriate caching for performance:

.. code-block:: python

   from ostruct.cli.cache_manager import FileCache

   class TemplateManager:
       """Template management with file caching."""

       def __init__(self, max_cache_size: int = 50 * 1024 * 1024):
           self._file_cache = FileCache(max_cache_size)

       def get_template_content(self, template_path: str) -> str:
           """Get template content with caching."""
           from pathlib import Path

           path = Path(template_path)
           stat = path.stat()

           # Try to get from cache
           cached = self._file_cache.get(
               str(path.absolute()),
               stat.st_mtime_ns,
               stat.st_size
           )

           if cached:
               return cached.content

           # Read and cache
           content = path.read_text(encoding='utf-8')
           self._file_cache.put(
               str(path.absolute()),
               content,
               'utf-8',
               None,  # hash_value
               stat.st_mtime_ns,
               stat.st_size
           )

           return content

**Performance practices:**

- Cache expensive operations (template compilation, file reads)
- Use appropriate data structures for performance
- Profile code to identify bottlenecks
- Optimize token usage for API calls
- Implement lazy loading where appropriate

Git Workflow
============

Commit Messages
---------------

Write clear, descriptive commit messages:

.. code-block:: text

   # Good commit message format
   Add template caching to improve rendering performance

   - Implement LRU cache for compiled templates
   - Add cache size configuration option
   - Include cache hit/miss metrics in logging
   - Update documentation with caching behavior

   Fixes #123

**Commit message guidelines:**

- Use imperative mood ("Add feature" not "Added feature")
- Keep first line under 50 characters
- Include detailed description if needed
- Reference issue numbers
- Explain the "why" not just the "what"

Branch Naming
-------------

Use descriptive branch names:

.. code-block:: text

   # Feature branches
   feature/template-caching
   feature/multi-tool-support

   # Bug fixes
   fix/security-validation-error
   fix/template-rendering-crash

   # Documentation
   docs/api-reference-update
   docs/contribution-guidelines

Pull Request Guidelines
-----------------------

Create comprehensive pull requests:

1. **Clear title and description**
2. **Link to related issues**
3. **Include testing notes**
4. **Update documentation as needed**
5. **Ensure CI passes**

Review Checklist
================

Before submitting code, verify:

Code Quality
------------

- [ ] Code follows formatting standards (Black, isort)
- [ ] No linting errors (Flake8)
- [ ] Type hints are comprehensive (MyPy)
- [ ] Docstrings are complete and accurate
- [ ] Error handling is appropriate

Security
--------

- [ ] All inputs are validated through security layer
- [ ] No sensitive information in logs
- [ ] Path handling uses security utilities
- [ ] Access controls are properly implemented

Testing
-------

- [ ] All tests pass
- [ ] New functionality has comprehensive tests
- [ ] Edge cases are covered
- [ ] Mock dependencies appropriately

Documentation
-------------

- [ ] Public APIs are documented
- [ ] Examples are working and current
- [ ] Documentation builds without warnings
- [ ] Cross-references are valid

Getting Help
============

If you have questions about coding standards:

1. **Check existing code** for examples
2. **Review this style guide** for clarification
3. **Ask in GitHub discussions** for guidance
4. **Submit a draft PR** for early feedback

Remember: Consistency is more important than personal preference. When in doubt, follow the existing patterns in the codebase.
