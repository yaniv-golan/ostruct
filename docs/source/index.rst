ostruct-cli
===========

``ostruct-cli`` is a command-line tool for generating structured output from OpenAI models. It combines the power of OpenAI's language models with the reliability of JSON Schema validation to ensure consistent, well-structured responses.

Key Features
============

- **Schema-First Approach**: Define your output structure using JSON Schema (validation is always performed automatically)
- **Template-Based Input**: Use Jinja2 templates with support for YAML frontmatter, system prompts, and shared system prompt includes
- **Multi-Tool Integration**: Native support for Code Interpreter, File Search, Web Search, and MCP servers
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
        --fta content input.txt \
        -m gpt-4o

Documentation
=============

.. toctree::
   :maxdepth: 2
   :caption: 📖 User Guides:

   user-guide/introduction
   user-guide/quickstart
   user-guide/ostruct_template_scripting_guide
   user-guide/prompt_scripting_guide
   user-guide/template_quick_reference
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

File & Directory Routing
~~~~~~~~~~~~~~~~~~~~~~~~

**Template Access (Local Only)**:

- ``-ft, --file-for-template FILE``: Files available in template only (auto-naming)
- ``--fta, --file-for-template-alias NAME PATH``: Files for template with custom aliases
- ``-dt, --dir-for-template DIR``: Directories for template access (auto-naming)
- ``--dta, --dir-for-template-alias NAME PATH``: Directories for template with custom aliases

**Code Interpreter (Execution & Analysis)**:

- ``-fc, --file-for-code-interpreter FILE``: Upload files for code execution (auto-naming)
- ``--fca, --file-for-code-interpreter-alias NAME PATH``: Files for code execution with custom aliases
- ``-dc, --dir-for-code-interpreter DIR``: Upload directories for analysis (auto-naming)
- ``--dca, --dir-for-code-interpreter-alias NAME PATH``: Directories for code execution with custom aliases

**File Search (Document Retrieval)**:

- ``-fs, --file-for-search FILE``: Upload files for semantic vector search (auto-naming)
- ``--fsa, --file-for-search-alias NAME PATH``: Files for search with custom aliases
- ``-ds, --dir-for-search DIR``: Upload directories for semantic search (auto-naming)
- ``--dsa, --dir-for-search-alias NAME PATH``: Directories for search with custom aliases

**Advanced Routing**:

- ``--file-for TOOL PATH``: Route files to specific tools (code-interpreter, file-search, template)

**Legacy Compatibility**:

- ``-f, --file NAME PATH``: Associate a file with a variable name (template access only)
- ``-d, --dir NAME DIR``: Associate a directory with a variable name (template access only)
- ``-p, --pattern NAME PATTERN``: Associate a glob pattern with a variable name

**Security & Path Control**:

- ``-R, --recursive``: Process directories and patterns recursively
- ``--base-dir DIR``: Base directory for resolving relative paths
- ``-A, --allow DIR``: Add an allowed directory for security (repeatable)
- ``--allowed-dir-file FILE``: File containing allowed directory paths

Variables
~~~~~~~~~

- ``-V, --var name=value``: Define a simple string variable
- ``-J, --json-var name='{"key":"value"}'``: Define a JSON variable

Multi-Tool Integration
~~~~~~~~~~~~~~~~~~~~~~

**Web Search**:

- ``--enable-tool web-search``: Enable OpenAI web search tool for up-to-date information
- ``--disable-tool web-search``: Explicitly disable web search
- ``--search-context-size [low|medium|high]``: Control content retrieval amount
- ``--user-country TEXT``: Specify user country for geographically tailored results
- ``--user-region TEXT``: Specify user region/state for search results
- ``--user-city TEXT``: Specify user city for search results

**MCP Servers**:

- ``--mcp-server [LABEL@]URL``: Connect to Model Context Protocol server
- ``--mcp-headers TEXT``: JSON string of headers for MCP servers
- ``--mcp-require-approval [always|never]``: Approval level for MCP tool usage
- ``--mcp-allowed-tools TEXT``: Allowed tools per server

**Code Interpreter Options**:

- ``--code-interpreter-cleanup``: Clean up uploaded files after execution (default: True)
- ``--code-interpreter-download-dir DIR``: Directory to save generated files

**File Search Options**:

- ``--file-search-cleanup``: Clean up uploaded files and vector stores (default: True)
- ``--file-search-vector-store-name TEXT``: Name for the vector store
- ``--file-search-timeout FLOAT``: Timeout for vector store indexing (default: 60.0)
- ``--file-search-retry-count INT``: Number of retry attempts (default: 3)

Model Parameters
~~~~~~~~~~~~~~~~

- ``-m, --model TEXT``: OpenAI model (supported: gpt-4o, o1, o3-mini) (default: gpt-4o)
- ``--temperature FLOAT``: Sampling temperature (0.0-2.0)
- ``--max-output-tokens INT``: Maximum output tokens
- ``--top-p FLOAT``: Top-p sampling parameter (0.0-1.0)
- ``--frequency-penalty FLOAT``: Frequency penalty (-2.0-2.0)
- ``--presence-penalty FLOAT``: Presence penalty (-2.0-2.0)
- ``--reasoning-effort [low|medium|high]``: Control model reasoning effort

System Prompt
~~~~~~~~~~~~~

- ``--sys-prompt TEXT``: Provide system prompt directly
- ``--sys-file FILE``: Load system prompt from file
- ``--ignore-task-sysprompt``: Ignore system prompt in template frontmatter

API Configuration
~~~~~~~~~~~~~~~~~

- ``--api-key TEXT``: OpenAI API key (defaults to OPENAI_API_KEY env var)
- ``--timeout FLOAT``: API timeout in seconds (default: 60.0)
- ``--config PATH``: Configuration file path (default: ostruct.yaml)

Output Control
~~~~~~~~~~~~~~

- ``--output-file FILE``: Write output to file instead of stdout
- ``--dry-run``: Validate and render template without making API calls

Debug & Progress
~~~~~~~~~~~~~~~~

**Progress Control**:

- ``--progress-level [none|basic|detailed]``: Set progress reporting level (default: basic)
- ``--no-progress``: Disable all progress indicators
- ``--verbose``: Enable verbose logging

**Template Debugging**:

- ``--debug-templates``: Enable detailed template expansion debugging
- ``--show-templates``: Show expanded templates before sending to API
- ``--show-context``: Show template variable context summary
- ``--show-context-detailed``: Show detailed template variable context
- ``--help-debug``: Show comprehensive template debugging help

**Optimization Debugging**:

- ``--no-optimization``: Skip template optimization entirely
- ``--show-optimization-diff``: Show template optimization changes
- ``--show-optimization-steps``: Show detailed optimization step tracking
- ``--optimization-step-detail [summary|detailed]``: Level of optimization detail
- ``--show-pre-optimization``: Show template content before optimization

**Validation & Schema**:

- ``--debug-validation``: Show detailed schema validation debugging
- ``--show-model-schema``: Display the generated Pydantic model schema
- ``--debug-openai-stream``: Enable low-level debug output for OpenAI streaming
- ``--debug``: Enable debug-level logging including template expansion

.. note::
   If you use the standalone binary release, download and extract the appropriate folder for your OS (e.g., ``ostruct-windows-amd64``, ``ostruct-macos-amd64``, ``ostruct-linux-amd64``) and run the executable from within that folder. Do not move the executable out of the folder, as it depends on bundled libraries in the same directory.
