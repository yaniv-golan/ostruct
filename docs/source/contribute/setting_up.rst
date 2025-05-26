====================
Development Setup
====================

This guide covers setting up a development environment for contributing to ostruct, including dependency management, testing, and development workflow.

.. contents:: Table of Contents
   :local:
   :depth: 2

Prerequisites
=============

Before setting up your development environment, ensure you have:

- **Python 3.10 or higher**: Check with ``python --version``
- **Git**: For version control and repository management
- **Poetry**: For dependency management and packaging

Installing Poetry
=================

Poetry is used for dependency management and packaging. Install it using the official installer:

.. code-block:: bash

   # Install Poetry (recommended method)
   curl -sSL https://install.python-poetry.org | python3 -

   # Add Poetry to your PATH (follow installer instructions)
   export PATH="$HOME/.local/bin:$PATH"

   # Verify installation
   poetry --version

Alternative installation methods are available in the `Poetry documentation <https://python-poetry.org/docs/#installation>`_.

Repository Setup
================

1. **Fork and Clone**

   Fork the repository on GitHub and clone your fork:

   .. code-block:: bash

      # Clone your fork
      git clone https://github.com/YOUR_USERNAME/ostruct.git
      cd ostruct

      # Add upstream remote
      git remote add upstream https://github.com/yaniv-golan/ostruct.git

2. **Install Dependencies**

   Install all dependencies including development and documentation tools:

   .. code-block:: bash

      # Install all dependency groups
      poetry install --with dev,docs,examples

      # Verify installation
      poetry run ostruct --version

   This installs:
   
   - **Core dependencies**: Required for ostruct functionality
   - **Development dependencies**: Testing, linting, formatting tools
   - **Documentation dependencies**: Sphinx and related tools
   - **Example dependencies**: Tools needed for running examples

3. **Activate Virtual Environment**

   Poetry creates and manages a virtual environment automatically:

   .. code-block:: bash

      # Activate the environment
      poetry shell

      # Or run commands directly
      poetry run python --version

Development Workflow
====================

Code Quality Tools
------------------

The project uses several tools to maintain code quality:

**Black** - Code formatting:

.. code-block:: bash

   # Format all code
   poetry run black src tests

   # Check formatting without changes
   poetry run black --check src tests

**isort** - Import sorting:

.. code-block:: bash

   # Sort imports
   poetry run isort src tests

   # Check import sorting
   poetry run isort --check-only src tests

**MyPy** - Type checking:

.. code-block:: bash

   # Type check source code
   poetry run mypy src

   # Type check with detailed output
   poetry run mypy --show-error-codes src

**Flake8** - Linting:

.. code-block:: bash

   # Lint source and tests
   poetry run flake8 src tests

   # Lint with configuration file
   poetry run flake8 --config=.flake8 src tests

Pre-commit Hooks
----------------

Set up pre-commit hooks to automatically run quality checks:

.. code-block:: bash

   # Install pre-commit
   poetry run pre-commit install

   # Run hooks manually
   poetry run pre-commit run --all-files

   # Update hook versions
   poetry run pre-commit autoupdate

The pre-commit configuration runs:

- Black code formatting
- isort import sorting
- MyPy type checking
- Flake8 linting
- Trailing whitespace removal
- YAML/JSON validation

Testing
=======

Running Tests
-------------

The project uses pytest for testing:

.. code-block:: bash

   # Run all tests
   poetry run pytest

   # Run specific test file
   poetry run pytest tests/test_cli.py

   # Run tests with coverage
   poetry run pytest --cov=src --cov-report=html

   # Run tests matching pattern
   poetry run pytest -k "test_template"

   # Run tests with verbose output
   poetry run pytest -v

Test Structure
--------------

Tests are organized in the ``tests/`` directory:

.. code-block:: text

   tests/
   ├── __init__.py
   ├── conftest.py              # Shared fixtures and configuration
   ├── mocks/                   # Mock objects and utilities
   ├── support/                 # Test support utilities
   ├── test_cli.py             # CLI interface tests
   ├── test_security.py        # Security feature tests
   ├── test_template_*.py      # Template system tests
   └── performance/            # Performance benchmarks

Writing Tests
-------------

Follow these guidelines when writing tests:

1. **Test Organization**:

   .. code-block:: python

      import pytest
      from ostruct.cli.some_module import SomeClass


      class TestSomeClass:
          """Tests for SomeClass functionality."""

          def test_basic_functionality(self):
              """Test basic functionality."""
              instance = SomeClass()
              result = instance.some_method()
              assert result == expected_value

2. **Use Fixtures**:

   .. code-block:: python

      @pytest.fixture
      def sample_config():
          """Provide sample configuration for tests."""
          return {
              "model": "gpt-4o",
              "temperature": 0.7
          }

      def test_with_config(sample_config):
          """Test using fixture."""
          assert sample_config["model"] == "gpt-4o"

3. **Mock External Dependencies**:

   .. code-block:: python

      from unittest.mock import patch, MagicMock

      @patch('ostruct.cli.openai_client.OpenAI')
      def test_api_call(mock_openai):
          """Test API call with mocked client."""
          mock_client = MagicMock()
          mock_openai.return_value = mock_client
          # Test implementation

Documentation Development
=========================

Building Documentation
----------------------

The documentation is built using Sphinx:

.. code-block:: bash

   # Navigate to docs directory
   cd docs

   # Build HTML documentation
   make html

   # Build and serve locally
   make livehtml

   # Clean build artifacts
   make clean

   # Check for broken links
   make linkcheck

Documentation Structure
-----------------------

Documentation is organized in the ``docs/source/`` directory:

.. code-block:: text

   docs/source/
   ├── index.rst               # Main documentation index
   ├── conf.py                 # Sphinx configuration
   ├── user-guide/            # User documentation
   ├── automate/              # Automation guides
   ├── security/              # Security documentation
   └── contribute/            # Contributor guides

Writing Documentation
---------------------

Follow these guidelines for documentation:

1. **Use reStructuredText** syntax with proper headers:

   .. code-block:: rst

      =================
      Chapter Title
      =================

      Section Title
      =============

      Subsection Title
      ----------------

2. **Include code examples** with syntax highlighting:

   .. code-block:: rst

      .. code-block:: bash

         # Example command
         ostruct run template.j2 schema.json -ft config.yaml

3. **Use cross-references** for internal links:

   .. code-block:: rst

      See :doc:`../user-guide/quickstart` for more information.

4. **Include table of contents**:

   .. code-block:: rst

      .. contents:: Table of Contents
         :local:
         :depth: 2

Debugging and Troubleshooting
=============================

Common Issues
-------------

**Import Errors**:

.. code-block:: bash

   # Reinstall dependencies
   poetry install --with dev,docs,examples

   # Clear Poetry cache
   poetry cache clear --all pypi

**Test Failures**:

.. code-block:: bash

   # Run tests with detailed output
   poetry run pytest -vvv --tb=long

   # Run single failing test
   poetry run pytest tests/test_file.py::test_function -vvv

**Documentation Build Issues**:

.. code-block:: bash

   # Clean and rebuild
   cd docs
   make clean
   make html

   # Check for Sphinx warnings
   make html 2>&1 | grep WARNING

Development Best Practices
==========================

Code Organization
-----------------

- Keep modules focused on single responsibilities
- Use clear, descriptive naming conventions
- Add comprehensive docstrings for public APIs
- Organize imports in standard order (standard library, third-party, local)

Error Handling
--------------

- Use specific exception types from ``cli/errors.py``
- Provide helpful error messages for users
- Log detailed information for debugging
- Handle edge cases gracefully

Security Considerations
-----------------------

- Validate all user inputs through security layer
- Use path normalization and symlink resolution
- Never log sensitive information (API keys, file contents)
- Follow principle of least privilege

Performance
-----------

- Use async/await for I/O operations
- Implement proper caching strategies
- Profile code for bottlenecks
- Optimize token usage for API calls

Environment Variables
=====================

Development environment variables:

.. code-block:: bash

   # Required for testing
   export OPENAI_API_KEY="your-test-api-key"

   # Optional development settings
   export OSTRUCT_LOG_LEVEL="DEBUG"
   export OSTRUCT_CACHE_DIR="./dev-cache"

Getting Help
============

If you encounter issues during development:

1. **Check existing issues** on GitHub
2. **Run diagnostics**:

   .. code-block:: bash

      # Check Python version
      python --version

      # Check Poetry installation
      poetry --version

      # Check dependencies
      poetry show

3. **Ask for help** in GitHub discussions
4. **Review documentation** for troubleshooting tips

Next Steps
==========

After setting up your development environment:

1. Review the :doc:`style_guide` for coding standards
2. Read :doc:`how_to_contribute` for the contribution process
3. Explore existing tests to understand testing patterns
4. Start with a simple bug fix or documentation improvement

Happy coding! 🚀