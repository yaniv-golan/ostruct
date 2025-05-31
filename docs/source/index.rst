ostruct-cli
===========

``ostruct-cli`` is a command-line tool for generating structured output from OpenAI models. It combines the power of OpenAI's language models with the reliability of JSON Schema validation to ensure consistent, well-structured responses.

Key Features
============

- **Schema-First Approach**: Define your output structure using JSON Schema (validation is always performed automatically)
- **Template-Based Input**: Use Jinja2 templates with support for YAML frontmatter, system prompts, and shared system prompt includes
- **File Processing**: Handle single files, multiple files, or entire directories with thread-safe operations
- **Cross-Platform**: Robust support for Windows, macOS, and Linux with consistent path handling
- **Security-Focused**: Safe file access with explicit directory permissions and enhanced error handling
- **Structured Output**: Guaranteed valid JSON output matching your schema
- **Token Management**: Automatic token limit validation and handling
- **Model Support**: Optimized handling for both streaming and non-streaming models

Quick Start
-----------

1. Install the package:

   .. code-block:: bash

      pip install ostruct-cli

2. Define your schema (``schema.json``):

   .. code-block:: json

      {
        "type": "object",
        "properties": {
          "summary": {
            "type": "string",
            "description": "Brief summary of the content"
          },
          "topics": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Main topics covered"
          }
        },
        "required": ["summary", "topics"]
      }

3. Create a task template (``task.j2``):

   .. code-block:: text

      ---
      system_prompt: You are an expert content analyzer.
      ---
      Analyze this content and extract key information:

      {{ content.content }}

4. Run the analysis:

   .. code-block:: bash

      ostruct run task.j2 schema.json \
        -f content input.txt \
        -m gpt-4o

Documentation
=============

.. toctree::
   :maxdepth: 2
   :caption: 📖 User Guides:

   user-guide/introduction
   user-guide/quickstart
   user-guide/examples
   user-guide/cli_reference
   user-guide/template_authoring

.. toctree::
   :maxdepth: 2
   :caption: 🤖 Automation:

   automate/ci_cd
   automate/containers
   automate/scripting_patterns
   automate/cost_control

.. toctree::
   :maxdepth: 2
   :caption: 🔒 Security:

   security/overview

.. toctree::
   :maxdepth: 2
   :caption: 🛠️ Contributing:

   contribute/setting_up
   contribute/style_guide
   contribute/how_to_contribute

Why Structured Output?
----------------------

Structured output offers several advantages:

1. **Reliability**: Schema validation ensures responses match your requirements
2. **Consistency**: Get the same structure every time, making responses easier to process
3. **Integration**: JSON output works seamlessly with other tools and systems
4. **Validation**: Catch and handle invalid responses before they reach your application

Handling Large Files
--------------------

When working with large files, the CLI provides several features to help:

1. **Token Validation**: Automatically validates token usage against model limits
2. **Prompt Structure**: Recommends placing content at the end with clear delimiters
3. **Dry Run**: Preview token usage before making API calls (note: `--debug-openai-stream` won't show streaming data during dry runs)
4. **Progress Reporting**: Track processing status for large operations

See the CLI documentation for detailed guidance on handling large files.

Requirements
------------

- Python 3.10 or higher
- OpenAI API key
- ``openai-structured`` >= 2.0.0

Logging
-------

The CLI writes logs to the following files in ``~/.ostruct/logs/``:

- ``ostruct.log``: General application logs (debug, errors, status)
- ``openai_stream.log``: OpenAI streaming operations logs

Logging Configuration
~~~~~~~~~~~~~~~~~~~~~

You can configure logging behavior through:

1. Command-line options:
   - ``--verbose``: Enable verbose logging (sets log level to DEBUG)
   - ``--debug-openai-stream``: Enable detailed OpenAI API stream logging
   - ``--debug-validation``: Enable schema validation debug logging

2. Environment variables:
   - ``OSTRUCT_LOG_LEVEL``: Set the log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
   - ``OSTRUCT_LOG_DIR``: Override the default log directory
   - ``OSTRUCT_LOG_FORMAT``: Customize the log message format

Example:

.. code-block:: bash

   # Set custom log level and directory
   export OSTRUCT_LOG_LEVEL=DEBUG
   export OSTRUCT_LOG_DIR=/path/to/logs

   # Run with verbose logging
   ostruct run task.j2 schema.json --verbose

Support
-------

- GitHub Issues: https://github.com/yaniv-golan/ostruct/issues
- Documentation: https://ostruct.readthedocs.io/

CLI Interface
-------------

The CLI revolves around a single subcommand called ``run``. Basic usage:

.. code-block:: bash

   ostruct run <TASK_TEMPLATE> <SCHEMA_FILE> [OPTIONS]

File & Directory Inputs
~~~~~~~~~~~~~~~~~~~~~~~

- ``-f <NAME> <PATH>``: Map a single file to a variable name
- ``-d <NAME> <DIR>``: Map a directory to a variable name
- ``-p <NAME> <PATTERN>``: Map files matching a glob pattern to a variable name
- ``-R, --recursive``: Enable recursive directory/pattern scanning
- ``--base-dir DIR``: Base directory for resolving relative paths
- ``-A, --allow DIR``: Add an allowed directory for security (repeatable)
- ``--allowed-dir-file FILE``: File containing allowed directory paths

Variables
~~~~~~~~~

- ``-V name=value``: Define a simple string variable
- ``-J name='{"key":"value"}'``: Define a JSON variable

Model Parameters
~~~~~~~~~~~~~~~~

- ``-m, --model MODEL``: Select the OpenAI model (supported: gpt-4o, o1, o3-mini)
- ``--temperature FLOAT``: Set sampling temperature (0.0-2.0)
- ``--max-output-tokens INT``: Set maximum output tokens
- ``--top-p FLOAT``: Set top-p sampling parameter (0.0-1.0)
- ``--frequency-penalty FLOAT``: Adjust frequency penalty (-2.0-2.0)
- ``--presence-penalty FLOAT``: Adjust presence penalty (-2.0-2.0)
- ``--reasoning-effort [low|medium|high]``: Control model reasoning effort

System Prompt
~~~~~~~~~~~~~

- ``--sys-prompt TEXT``: Provide system prompt directly
- ``--sys-file FILE``: Load system prompt from file
- ``--ignore-task-sysprompt``: Ignore system prompt in template frontmatter

API Configuration
~~~~~~~~~~~~~~~~~

- ``--api-key KEY``: OpenAI API key (defaults to OPENAI_API_KEY env var)
- ``--timeout FLOAT``: API timeout in seconds (default: 60.0)

Output Control
~~~~~~~~~~~~~~

- ``--output-file FILE``: Write output to file instead of stdout
- ``--dry-run``: Validate and render template without making API calls

Debug & Progress
~~~~~~~~~~~~~~~~

- ``--debug-validation``: Show detailed schema validation debugging
- ``--debug-openai-stream``: Enable low-level debug output for OpenAI streaming
- ``--progress-level {none,basic,detailed}``: Set progress reporting level
  - ``none``: No progress indicators
  - ``basic``: Show key operation steps (default)
  - ``detailed``: Show all steps with additional info
- ``--show-model-schema``: Display the generated Pydantic model schema
- ``--verbose``: Enable verbose logging
- ``--no-progress``: Disable all progress indicators
