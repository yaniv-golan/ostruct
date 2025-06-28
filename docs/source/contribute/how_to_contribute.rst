==================
How to Contribute
==================

Welcome to the ostruct community! This guide covers the contribution process, from reporting issues to submitting code changes. We appreciate all contributions that help improve ostruct for everyone.

.. contents:: Table of Contents
   :local:
   :depth: 2

Getting Started
===============

Types of Contributions
----------------------

We welcome various types of contributions:

**Code Contributions**:
- Bug fixes and improvements
- New features and enhancements
- Performance optimizations
- Security improvements

**Documentation**:
- API documentation improvements
- Tutorial and guide enhancements
- Example code and use cases
- Translation efforts

**Community Support**:
- Answering questions in discussions
- Bug report verification
- Feature request validation
- Code review participation

**Quality Assurance**:
- Testing on different platforms
- Performance testing and benchmarking
- Security review and validation
- Accessibility testing

Before You Start
----------------

1. **Review existing issues** on GitHub to avoid duplication
2. **Read the documentation** to understand current functionality
3. **Set up your development environment** following :doc:`setting_up`
4. **Familiarize yourself** with our :doc:`style_guide`
5. **Join the discussions** to introduce yourself and ask questions

Reporting Issues
================

Bug Reports
-----------

When reporting bugs, include:

**Required Information**:

.. code-block:: text

   **Bug Description**
   A clear description of what went wrong.

   **Steps to Reproduce**
   1. Run command: `ostruct run template.j2 schema.json --file ci:data file.py`
   2. Observe error message
   3. See unexpected behavior

   **Expected Behavior**
   Describe what should have happened instead.

   **Environment**
   - OS: [e.g., macOS 13.0, Ubuntu 22.04, Windows 11]
   - Python version: [e.g., 3.11.2]
   - ostruct version: [e.g., 0.8.0]
   - Installation method: [pip, poetry, from source]

   **Additional Context**
   - Configuration files (redacted)
   - Error logs and stack traces
   - Minimal reproducible example

**Bug Report Template**:

Use the GitHub issue template or follow this structure:

.. code-block:: markdown

   ## Bug Report

   ### Description
   Brief description of the issue.

   ### Steps to Reproduce
   1. First step
   2. Second step
   3. See error

   ### Expected Behavior
   What should happen instead.

   ### Actual Behavior
   What actually happened.

   ### Environment
   - Operating System:
   - Python Version:
   - ostruct Version:
   - Installation Method:

   ### Additional Information
   Any other context, logs, or screenshots.

Feature Requests
----------------

When requesting features, provide:

**Feature Description**:
- Clear explanation of the proposed feature
- Use cases and benefits
- Examples of how it would be used
- Impact on existing functionality

**Implementation Suggestions**:
- Potential approaches (if you have ideas)
- Technical considerations
- Breaking change implications
- Alternative solutions considered

**Example Feature Request**:

.. code-block:: markdown

   ## Feature Request

   ### Summary
   Add support for streaming template rendering for large files.

   ### Problem
   Currently, large template files must be loaded entirely into memory,
   causing performance issues and memory constraints.

   ### Proposed Solution
   Implement streaming template renderer that processes templates in chunks:
   - Stream input files rather than loading completely
   - Process templates incrementally
   - Maintain context across chunks

   ### Use Cases
   - Processing large log files (>1GB)
   - Template rendering for data pipelines
   - Memory-constrained environments

   ### Alternatives Considered
   - File splitting preprocessing
   - External streaming tools
   - Pagination approach

Contributing Code
=================

Development Workflow
--------------------

1. **Fork the Repository**

   .. code-block:: bash

      # Fork on GitHub, then clone
      git clone https://github.com/YOUR_USERNAME/ostruct.git
      cd ostruct

      # Add upstream remote
      git remote add upstream https://github.com/yaniv-golan/ostruct.git

2. **Create a Feature Branch**

   .. code-block:: bash

      # Update main branch
      git checkout main
      git pull upstream main

      # Create feature branch
      git checkout -b feature/your-feature-name

3. **Set Up Development Environment**

   .. code-block:: bash

      # Install dependencies
      poetry install --with dev,docs,examples

      # Install pre-commit hooks
      poetry run pre-commit install

4. **Make Your Changes**

   Follow the :doc:`style_guide` for code standards:

   - Write clean, well-documented code
   - Include comprehensive tests
   - Update documentation as needed
   - Follow security best practices

5. **Test Your Changes**

   .. code-block:: bash

      # Run all tests
      poetry run pytest

      # Run type checking
      poetry run mypy src

      # Run linting
      poetry run flake8 src tests

      # Test documentation builds
      cd docs && make html

6. **Commit Your Changes**

   .. code-block:: bash

      # Stage changes
      git add .

      # Commit with descriptive message
      git commit -m "Add streaming template renderer

      - Implement chunk-based template processing
      - Add streaming file reader with buffer management
      - Include memory usage optimization
      - Add comprehensive tests for streaming functionality

      Fixes #123"

7. **Push and Create Pull Request**

   .. code-block:: bash

      # Push to your fork
      git push origin feature/your-feature-name

      # Create pull request on GitHub

Pull Request Process
--------------------

**Pull Request Requirements**:

- [ ] **Clear title and description** explaining the changes
- [ ] **Link to related issues** using "Fixes #123" or "Relates to #456"
- [ ] **All tests pass** (CI will verify this)
- [ ] **Code coverage maintained** or improved
- [ ] **Documentation updated** for user-facing changes
- [ ] **Breaking changes noted** in description and CHANGELOG

**Pull Request Template**:

.. code-block:: markdown

   ## Description
   Brief description of changes and motivation.

   ## Changes Made
   - [ ] Added new feature X
   - [ ] Fixed bug Y
   - [ ] Updated documentation Z

   ## Testing
   - [ ] Unit tests added/updated
   - [ ] Integration tests pass
   - [ ] Manual testing completed

   ## Breaking Changes
   - None / List any breaking changes

   ## Checklist
   - [ ] Code follows style guide
   - [ ] Tests added for new functionality
   - [ ] Documentation updated
   - [ ] CHANGELOG updated (if needed)

**Review Process**:

1. **Automated Checks**: CI runs tests, linting, and security scans
2. **Maintainer Review**: Core maintainers review code and design
3. **Community Feedback**: Other contributors may provide input
4. **Iterative Improvement**: Address feedback and update PR
5. **Final Approval**: Maintainer approves and merges

Code Review Guidelines
----------------------

**As a Contributor**:

- Respond promptly to review feedback
- Ask for clarification if comments are unclear
- Be open to suggestions and alternative approaches
- Update tests and documentation based on feedback
- Keep PR focused and avoid scope creep

**As a Reviewer**:

- Be constructive and specific in feedback
- Explain the reasoning behind suggestions
- Acknowledge good practices and improvements
- Focus on code quality, maintainability, and security
- Approve when changes meet project standards

Testing Requirements
====================

Test Coverage
-------------

All code contributions must include appropriate tests:

**Required Test Types**:

- **Unit Tests**: Test individual functions and classes
- **Integration Tests**: Test component interactions
- **Error Handling Tests**: Verify error conditions
- **Edge Case Tests**: Test boundary conditions

**Test Coverage Standards**:

- Maintain minimum 90% test coverage
- Cover all new functionality completely
- Include both positive and negative test cases
- Test error handling and edge conditions

Example Test Structure
----------------------

.. code-block:: python

   import pytest
   from unittest.mock import patch, MagicMock
   from pathlib import Path

   from ostruct.cli.new_feature import NewFeature
   from ostruct.cli.errors import ValidationError


   class TestNewFeature:
       """Comprehensive tests for NewFeature functionality."""

       @pytest.fixture
       def sample_data(self):
           """Provide sample data for tests."""
           return {
               "input": "test input",
               "expected": "test output"
           }

       @pytest.fixture
       def new_feature(self):
           """Create NewFeature instance for testing."""
           return NewFeature(config={"setting": "value"})

       def test_basic_functionality(self, new_feature, sample_data):
           """Test basic feature operation."""
           result = new_feature.process(sample_data["input"])
           assert result == sample_data["expected"]

       def test_invalid_input_raises_error(self, new_feature):
           """Test that invalid input raises appropriate error."""
           with pytest.raises(ValidationError, match="Invalid input"):
               new_feature.process(None)

       @patch('ostruct.cli.new_feature.external_dependency')
       def test_external_dependency_mocked(self, mock_dependency, new_feature):
           """Test with mocked external dependency."""
           mock_dependency.return_value = "mocked_result"
           result = new_feature.process_with_dependency("input")
           assert result == "processed_mocked_result"

       @pytest.mark.parametrize("input_value,expected", [
           ("test1", "result1"),
           ("test2", "result2"),
           ("edge_case", "edge_result"),
       ])
       def test_multiple_scenarios(self, new_feature, input_value, expected):
           """Test multiple input scenarios."""
           result = new_feature.process(input_value)
           assert result == expected

Documentation Requirements
==========================

Documentation Updates
---------------------

Update documentation for all user-facing changes:

**Required Documentation**:

- **API Documentation**: Docstrings for all public functions and classes
- **User Guide Updates**: If functionality affects user workflows
- **Examples**: Code examples demonstrating new features
- **Migration Guide**: For breaking changes

**Documentation Standards**:

- Use clear, concise language
- Include working code examples
- Maintain consistent terminology
- Cross-reference related functionality
- Test all examples for accuracy

Example Documentation
---------------------

.. code-block:: python

   def new_feature_function(input_data: str, options: Dict[str, Any]) -> str:
       """Process input data with configurable options.

       This function demonstrates how to document new functionality
       with comprehensive examples and clear parameter descriptions.

       Args:
           input_data: The input string to process. Must be non-empty
               and contain valid content.
           options: Configuration options for processing. Supported
               options include 'mode', 'strict', and 'output_format'.

       Returns:
           Processed string based on input and options.

       Raises:
           ValidationError: If input_data is invalid or empty.
           ConfigurationError: If options contain invalid values.

       Example:
           Basic usage with default options:

           >>> result = new_feature_function("hello", {})
           >>> print(result)
           HELLO

           Advanced usage with custom options:

           >>> options = {"mode": "title", "strict": True}
           >>> result = new_feature_function("hello world", options)
           >>> print(result)
           Hello World

       Note:
           This function requires the input to be valid UTF-8 text.
           Binary data should be decoded before processing.

       See Also:
           :func:`related_function`: For related functionality.
           :doc:`../user-guide/template_authoring`: For advanced template patterns.
       """

Community Guidelines
====================

Code of Conduct
---------------

We are committed to providing a welcoming and inclusive environment:

**Our Standards**:

- Use welcoming and inclusive language
- Respect different viewpoints and experiences
- Accept constructive criticism gracefully
- Focus on what's best for the community
- Show empathy towards other community members

**Unacceptable Behavior**:

- Harassment, trolling, or discriminatory comments
- Personal attacks or insults
- Public or private harassment
- Publishing others' private information
- Other conduct inappropriate in a professional setting

Communication Guidelines
------------------------

**GitHub Discussions**:

- Search existing discussions before creating new ones
- Use clear, descriptive titles
- Provide context and examples
- Tag discussions appropriately
- Follow up on your own discussions

**Issue Comments**:

- Stay on topic and relevant to the issue
- Provide additional context or clarification
- Avoid "+1" comments (use emoji reactions instead)
- Be patient with response times

**Pull Request Reviews**:

- Be constructive and specific in feedback
- Acknowledge good work and improvements
- Suggest alternatives when pointing out issues
- Focus on code quality and project goals

Recognition and Attribution
===========================

Contributor Recognition
-----------------------

We recognize all types of contributions:

- **Contributors List**: All contributors are listed in project documentation
- **Release Notes**: Significant contributions are highlighted in releases
- **GitHub Acknowledgments**: PRs and issues include attribution
- **Community Spotlight**: Outstanding contributions may be featured

How to Get Credit
-----------------

- Ensure your GitHub profile is complete
- Use consistent name/email across contributions
- Include your preferred attribution in PR descriptions
- Participate in community discussions

Getting Help
============

If you need assistance:

**Technical Questions**:

- Check existing documentation and examples
- Search GitHub issues and discussions
- Ask in GitHub discussions with clear context
- Join community chat for real-time help

**Process Questions**:

- Review this contribution guide
- Ask in GitHub discussions
- Contact maintainers directly for sensitive issues
- Participate in community meetings

**Bug Report Assistance**:

- Use issue templates when available
- Include all requested information
- Respond to clarification requests
- Test with latest version before reporting

Resources and Links
===================

**Development Resources**:

- :doc:`setting_up`: Development environment setup
- :doc:`style_guide`: Coding standards and best practices
- `GitHub Repository <https://github.com/yaniv-golan/ostruct>`_: Main repository
- `Issue Tracker <https://github.com/yaniv-golan/ostruct/issues>`_: Bug reports and features

**Community Resources**:

- `GitHub Issues <https://github.com/yaniv-golan/ostruct/issues>`_: Community Q&A and discussions
- `Documentation <https://ostruct.readthedocs.io>`_: Complete documentation
- `Examples <https://github.com/yaniv-golan/ostruct/tree/main/examples>`_: Usage examples

**Project Information**:

- `License <https://github.com/yaniv-golan/ostruct/blob/main/LICENSE>`_: MIT License
- `Community Guidelines <https://github.com/yaniv-golan/ostruct>`_: Community guidelines
- `Security Policy <https://github.com/yaniv-golan/ostruct/security/policy>`_: Security reporting

Thank You!
==========

Thank you for your interest in contributing to ostruct! Your contributions help make this project better for everyone. Whether you're fixing a small typo or adding a major feature, every contribution is valuable and appreciated.

We look forward to working with you and seeing what amazing things we can build together! 🚀
