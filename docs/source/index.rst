ostruct-cli
===========

``ostruct-cli`` is a command-line tool for generating structured output from OpenAI models. It combines the power of OpenAI's language models with the reliability of JSON Schema validation to ensure consistent, well-structured responses.

Key Features
============

- **Schema-First Approach**: Define your output structure using JSON Schema (validation is always performed automatically)
- **Template-Based Input**: Use Jinja2 templates with support for YAML frontmatter, system prompts, and shared system prompt includes
- **Multi-Tool Integration**: Native support for Code Interpreter, File Search, Web Search, and MCP servers
- **Development Tools**: Built-in meta-tools for schema generation and template analysis
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
        --file content input.txt \
        -m gpt-4o

Documentation
=============

.. toctree::
   :maxdepth: 1
   :caption: 📚 Getting Started

   user-guide/introduction
   user-guide/quickstart
   user-guide/examples

.. toctree::
   :maxdepth: 1
   :caption: 📝 Templates

   user-guide/template_guide
   user-guide/template_quick_reference
   user-guide/advanced_patterns

.. toctree::
   :maxdepth: 1
   :caption: 🔧 Reference

   user-guide/cli_reference
   user-guide/upload_cache_guide
   user-guide/gitignore_guide
   user-guide/tool_integration

.. toctree::
   :maxdepth: 1
   :caption: 🚀 Automation

   automate/ci_cd_and_containers
   automate/scripting_and_cost

.. toctree::
   :maxdepth: 1
   :caption: 🛠️ Contributing

   contribute/how_to_contribute
   contribute/style_guide
   contribute/release_workflow

.. toctree::
   :maxdepth: 1
   :caption: 🔒 Security

   security/overview

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

Logging
-------

ostruct writes logs to ``~/.ostruct/logs/`` for debugging and monitoring. Use ``--verbose`` for detailed logging or configure via environment variables. See the :doc:`user-guide/cli_reference` for complete logging configuration options.

Support
-------

- GitHub Issues: https://github.com/yaniv-golan/ostruct/issues
- Documentation: https://ostruct.readthedocs.io/

CLI Interface
-------------

The CLI revolves around a single subcommand called ``run``. Basic usage:

.. code-block:: bash

   ostruct run <TASK_TEMPLATE> <SCHEMA_FILE> [OPTIONS]

**Key Features**:

- **File routing**: ``--file ci:data file.csv`` (Code Interpreter), ``--file fs:docs manual.pdf`` (File Search)
- **Multi-tool integration**: Web Search, Code Interpreter, File Search, MCP Servers
- **Template variables**: ``-V name=value`` for simple variables, ``-J name='{"key":"value"}'`` for JSON
- **Model configuration**: ``--model gpt-4o --temperature 0.7``
- **Debugging**: ``--dry-run``, ``--template-debug vars``, ``--verbose``

For complete CLI documentation, see the :doc:`user-guide/cli_reference`.
