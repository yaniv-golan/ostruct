CLI Reference
=============

Complete reference for the ``ostruct`` command-line interface. This guide covers all options, file routing syntaxes, and advanced features with verified flag names and examples.

.. note::
   **New to ostruct?** Start with the :doc:`quickstart` guide for a hands-on introduction.

Basic Usage
-----------

.. code-block:: bash

   ostruct run TEMPLATE_FILE SCHEMA_FILE [OPTIONS]

**Required Arguments:**

- ``TEMPLATE_FILE``: Path to Jinja2 template file (typically with ``.j2`` extension)
- ``SCHEMA_FILE``: JSON Schema file that defines the structure of the output

Command Structure
-----------------

The CLI revolves around a single subcommand called ``run``. All file processing, model configuration, and tool integration happens through this command with various options.

File and Directory Management
-----------------------------

**File Attachment System**:

- ``--file [targets:]alias path``: Attach file with explicit tool targeting
- ``--dir [targets:]alias path``: Attach directory with explicit tool targeting
- ``--collect [targets:]alias @filelist``: Attach file collection from list

**Targets**: ``prompt`` (template-only, default), ``ci`` (code-interpreter), ``fs`` (file-search)

**Examples**:

- ``--file config settings.yaml``: Template access only
- ``--file ci:data analysis.csv``: Upload to Code Interpreter
- ``--file fs:docs manual.pdf``: Upload to File Search
- ``--file ci,fs:shared data.json``: Multi-tool routing

**Security & Path Control**:

- ``--recursive``: Process directories and patterns recursively
- ``-S, --path-security [permissive|warn|strict]``: Path security mode (default: warn)
- ``--allow DIR``: Add an allowed directory for security (repeatable)
- ``--allow-list FILE``: File containing allowed directory paths

Variables
---------

- ``-V, --var name=value``: Define a simple string variable
- ``-J, --json-var name='{"key":"value"}'``: Define a JSON variable

Model Configuration
-------------------

- ``-m, --model TEXT``: OpenAI model (supported: gpt-4o, o1, o3-mini) (default: gpt-4o)
- ``--temperature FLOAT``: Sampling temperature (0.0-2.0)
- ``--max-output-tokens INT``: Maximum output tokens
- ``--top-p FLOAT``: Top-p sampling parameter (0.0-1.0)
- ``--frequency-penalty FLOAT``: Frequency penalty (-2.0-2.0)
- ``--presence-penalty FLOAT``: Presence penalty (-2.0-2.0)
- ``--reasoning-effort [low|medium|high]``: Control model reasoning effort

System Prompt Configuration
---------------------------

- ``--sys-prompt TEXT``: Provide system prompt directly
- ``--sys-prompt-file FILE``: Load system prompt from file
- ``--ignore-task-sysprompt``: Ignore system prompt in template frontmatter

API Configuration
-----------------

- ``--api-key TEXT``: OpenAI API key (defaults to OPENAI_API_KEY env var)
- ``--timeout FLOAT``: API timeout in seconds (default: 60.0)
- ``--config PATH``: Configuration file path (default: ostruct.yaml)

Output and Debugging
--------------------

- ``--output-file FILE``: Write output to file instead of stdout
- ``--dry-run``: Validate and render template without making API calls
- ``--progress [none|basic|detailed]``: Control progress display (default: basic)
- ``--verbose``: Enable verbose logging

Tool Integration
----------------

**Web Search**:

- ``--enable-tool web-search``: Enable OpenAI web search tool for up-to-date information
- ``--disable-tool web-search``: Explicitly disable web search
- ``--ws-context-size [low|medium|high]``: Control content retrieval amount
- ``--ws-country TEXT``: Specify user country for geographically tailored results
- ``--ws-region TEXT``: Specify user region/state for search results
- ``--ws-city TEXT``: Specify user city for search results

**MCP Servers**:

- ``--mcp-server [LABEL@]URL``: Connect to Model Context Protocol server
- ``--mcp-headers TEXT``: JSON string of headers for MCP servers
- ``--mcp-require-approval [always|never]``: Approval level for MCP tool usage
- ``--mcp-allowed-tools TEXT``: Allowed tools per server

**Code Interpreter Options**:

- ``--ci-cleanup``: Clean up uploaded files after execution (default: True)
- ``--ci-download-dir DIR``: Directory to save generated files

**File Search Options**:

- ``--fs-cleanup``: Clean up uploaded files and vector stores (default: True)
- ``--fs-store-name TEXT``: Name for the vector store
- ``--fs-timeout FLOAT``: Timeout for vector store indexing (default: 60.0)
- ``--fs-retries INT``: Number of retry attempts (default: 3)

Logging Configuration
---------------------

The CLI writes logs to the following files in ``~/.ostruct/logs/``:

- ``ostruct.log``: General application logs (debug, errors, status)
- ``openai_stream.log``: OpenAI streaming operations logs

**Logging Control**:

1. Command-line options:
   - ``--verbose``: Enable verbose logging (sets log level to DEBUG)
   - ``--debug-openai-stream``: Enable detailed OpenAI API stream logging
   - ``--debug-validation``: Enable schema validation debug logging

2. Environment variables (template processing limits):
   - ``OSTRUCT_TEMPLATE_FILE_LIMIT``: Max individual file size for template access (default: 65536 bytes)
   - ``OSTRUCT_TEMPLATE_TOTAL_LIMIT``: Max total file size for template processing (default: 1048576 bytes)
   - ``OSTRUCT_TEMPLATE_PREVIEW_LIMIT``: Max characters in template debug previews (default: 4096)

Example:

.. code-block:: bash

   # Set template processing limits
   export OSTRUCT_TEMPLATE_FILE_LIMIT=131072  # 128KB
   export OSTRUCT_TEMPLATE_TOTAL_LIMIT=2097152  # 2MB

   # Run with verbose logging (controlled via CLI flags)
   ostruct run task.j2 schema.json --verbose

Quick Reference Commands
------------------------

.. code-block:: bash

   # Show complete help
   ostruct --help
   ostruct run --help

   # Show quick reference with new attachment syntax
   ostruct quick-ref

   # Get JSON help for programmatic consumption (experimental)
   ostruct run --help-json

   # Update model registry
   ostruct update-registry

.. warning::
   **Experimental Feature: --help-json**

   The ``--help-json`` option is **experimental** and subject to change. The JSON format it produces is **not yet stable** and is likely to change in future versions without notice.

   - **Use with caution** in production scripts or automation
   - **Format may change** between versions without backward compatibility
   - **Intended for development** and testing purposes only

Attachment System
=================

The file routing system uses explicit target/alias attachment syntax for precise control over how files are processed and which tools they're sent to.

The new attachment system uses explicit target/alias syntax for precise control over file routing:

.. code-block:: bash

   # Basic attachment (template access only - default)
   --file alias path

   # Explicit tool targeting
   --file target:alias path
   --file ci:data ./analysis.csv        # Code Interpreter
   --file fs:docs ./documentation       # File Search
   --file prompt:config ./config.yaml   # Template only

   # Multi-tool attachment
   --file ci,fs:shared ./data.json      # Both CI and FS

Attachment Options
------------------

.. option:: -F, --file [TARGETS:]ALIAS PATH

   Attach file with explicit tool targeting.

   :param TARGETS: Optional comma-separated list of targets (prompt, ci, fs)
   :param ALIAS: Variable name for template access
   :param PATH: Path to file

   **Examples:**

   .. code-block:: bash

      --file data file.txt                    # Template only (default)
      --file ci:analysis data.csv             # Code Interpreter
      --file fs:docs manual.pdf               # File Search
      --file prompt,ci:config settings.json  # Template and CI

.. option:: -D, --dir [TARGETS:]ALIAS PATH

   Attach directory with explicit tool targeting.

   **Examples:**

   .. code-block:: bash

      --dir source ./src                     # Template only
      --dir ci:datasets ./data               # Code Interpreter
      --dir fs:knowledge ./documentation    # File Search

.. option:: -C, --collect [TARGETS:]ALIAS @FILELIST

   Attach file collection from list.

   **Examples:**

   .. code-block:: bash

      --collect files @list.txt              # Template only
      --collect ci:data @datasets.txt        # Code Interpreter

File Reference System
---------------------

Ostruct provides an **optional** file reference system using the ``file_ref()`` function with automatic XML appendix generation. This is an alternative to manually accessing files in templates - use whichever approach fits your needs.

**Choose Your Approach:**

- **Automatic**: Use ``file_ref()`` for XML appendix at prompt end (good for reference material)
- **Manual**: Access files directly with ``{{ alias.content }}`` for custom formatting and placement

**Template Usage:**

Use the ``file_ref()`` function to reference attached files by their alias:

.. code-block:: jinja

   {# Automatic XML appendix approach #}
   Analyze the code in {{ file_ref("source") }}.
   Review the config in {{ file_ref("settings") }}.

   {# Manual formatting approach #}
   ## Configuration
   ```yaml
   {{ settings.content }}
   ```

   ## Source Files
   {% for file in source %}
   ### {{ file.name }}
   {{ file.content }}
   {% endfor %}

This renders as:

.. code-block:: text

   Analyze the code in <source>.
   Review the config in <settings>.

**XML Appendix:**

When using ``file_ref()``, referenced files automatically appear in a structured XML appendix at the end of your prompt:

.. code-block:: xml

   <files>
     <dir alias="source" path="src/">
       <file path="main.py">
         <content><![CDATA[...]]></content>
       </file>
     </dir>
     <file alias="settings" path="config.yaml">
       <content><![CDATA[...]]></content>
     </file>
   </files>

**File Placement Considerations:**

LLMs process prompts sequentially and pay more attention to content at the end. Consider:

- **Manual inclusion**: Place files where they're most relevant in your analysis flow
- **XML appendix**: Files appear at the very end, ideal for supporting documentation
- **Mixed approach**: Use both - manual for immediate analysis, ``file_ref()`` for reference

See :doc:`template_guide` for complete file reference documentation.

Tool Targets
------------

The new system supports explicit targeting to specific tools:

.. list-table:: Tool Targets
   :widths: 15 15 70
   :header-rows: 1

   * - Target
     - Alias
     - Description
   * - ``prompt``
     - (default)
     - Available in template only - no upload to tools
   * - ``code-interpreter``
     - ``ci``
     - Upload to Code Interpreter for execution and analysis
   * - ``file-search``
     - ``fs``
     - Upload to File Search vector store for document retrieval

Security Modes
--------------

Control file access with enhanced security options:

.. option:: -S, --path-security MODE

   Set path security mode for file access validation.

   :param MODE: Security level (permissive, warn, strict)

   - ``permissive``: Allow all file access (default)
   - ``warn``: Allow with warnings for unauthorized paths
   - ``strict``: Only allow explicitly permitted paths

.. option:: --allow DIR

   Add allowed directory for security (can be used multiple times).

.. option:: --allow-file FILE

   Allow specific file access.

.. option:: --allow-list FILE

   Load allowed paths from file.

Usage Examples
==============

Template Access Examples
------------------------

Files attached with ``prompt`` target (default) are available in templates but not uploaded to external services.

.. code-block:: bash

   # Template-only access (default behavior)
   ostruct run task.j2 schema.json --file config config.yaml
   ostruct run task.j2 schema.json --file prompt:data input.json

   # Directory attachment for template access
   ostruct run task.j2 schema.json --dir settings ./config

**Template Access**: Use ``{{ alias.content }}`` or ``{{ alias }}`` to access file content in templates.

Code Interpreter Examples
-------------------------

Files attached with ``ci`` target are uploaded to OpenAI's Code Interpreter for execution and analysis.

.. code-block:: bash

   # Upload files for data analysis
   ostruct run analyze.j2 schema.json --file ci:dataset data.csv
   ostruct run analyze.j2 schema.json --file ci:script analysis.py

   # Upload directories for computational processing
   ostruct run analyze.j2 schema.json --dir ci:data ./datasets

.. warning::
   **Data Upload**: Files with ``ci`` target are uploaded to OpenAI's execution environment.

File Search Examples
--------------------

Files attached with ``fs`` target are uploaded to File Search vector store for document retrieval.

.. code-block:: bash

   # Upload documents for semantic search
   ostruct run search.j2 schema.json --file fs:manual documentation.pdf
   ostruct run search.j2 schema.json --file fs:knowledge kb.txt

   # Upload directory for document collection
   ostruct run search.j2 schema.json --dir fs:docs ./documentation

Multi-Tool Integration Examples
-------------------------------

Share files between multiple tools for comprehensive workflows:

.. code-block:: bash

   # Share data between Code Interpreter and File Search
   ostruct run workflow.j2 schema.json --file ci,fs:shared data.json

   # Complex multi-tool workflow
   ostruct run complex.j2 schema.json \
     --file prompt:config settings.yaml \
     --file ci:data analysis.csv \
     --file fs:docs manual.pdf \
     --file ci,fs:shared reference.json

File Collection Examples
------------------------

Process multiple files from lists:

.. code-block:: bash

   # Basic file collection
   ostruct run batch.j2 schema.json --collect files @file-list.txt

   # Upload collection to Code Interpreter
   ostruct run analyze.j2 schema.json --collect ci:datasets @data-files.txt

File Type Limitations
=====================

Text File Processing
--------------------

ostruct processes files as text content for template rendering. When templates
access file content (``{{ file.content }}``), the file must be decodable as UTF-8 text.

**Supported file types:**

- Text files (.txt, .md, .rst, .py, .js, .html, .css, etc.)
- Configuration files (.json, .yaml, .toml, .ini, etc.)
- Code files in any text-based language
- CSV and other text-based data formats

**Binary files** (images, executables, compressed files, etc.) cannot be accessed
via ``.content`` in templates. However, you can still access metadata:

.. code-block:: jinja

   <!-- This works for any file type -->
   File name: {{ binary_file.name }}
   File path: {{ binary_file.path }}

   <!-- This fails for binary files -->
   File content: {{ binary_file.content }}  ❌

**Validation with --dry-run:**

Use ``--dry-run`` to catch binary file access errors before execution:

.. code-block:: bash

   # This will fail validation if template tries to access binary content
   ostruct run template.j2 schema.json --file data image.png --dry-run

**Workarounds for Binary Files:**

1. **Use Code Interpreter** for binary file analysis:

   .. code-block:: bash

      # Upload binary files to Code Interpreter for analysis
      ostruct run analyze.j2 schema.json --file ci:data report.xlsx

2. **Access only metadata** in templates:

   .. code-block:: jinja

      {% for file in files %}
      Processing: {{ file.name }} ({{ file.size }} bytes)
      {% endfor %}

3. **Filter by file extension** in templates:

   .. code-block:: jinja

      {% for file in files %}
      {% if file.name.endswith(('.txt', '.md', '.py')) %}
      Content: {{ file.content }}
      {% else %}
      Binary file: {{ file.name }}
      {% endif %}
      {% endfor %}

Other Options
=============

Variables and Template Context
------------------------------

.. option:: -V, --var NAME=VALUE

   Set template variable with simple string value.

   **Examples:**

   .. code-block:: bash

      -V env=production -V debug=false

.. option:: -J, --json-var NAME=JSON

   Set template variable with JSON value.

   **Examples:**

   .. code-block:: bash

      -J config='{"timeout":30,"retries":3}'

Model and API Options
---------------------

.. option:: --model MODEL_NAME

   Specify OpenAI model to use (default: gpt-4o).

   Model names are automatically validated against the OpenAI model registry.
   Only models that support structured output are available for selection.

   **Examples:**

   .. code-block:: bash

      # Use specific model (validated automatically)
      ostruct run template.j2 schema.json --model gpt-4o-mini

      # See all available models with details
      ostruct list-models

      # Invalid models are rejected with helpful suggestions
      ostruct run template.j2 schema.json --model invalid-model
      # Error: Invalid model 'invalid-model'. Available models: gpt-4o, gpt-4o-mini, o1 (and 15 more).
      #        Run 'ostruct list-models' to see all 18 available models.

   **Shell Completion:**

   When shell completion is enabled, the ``--model`` parameter will auto-complete
   with available model names:

   .. code-block:: bash

      ostruct run template.j2 schema.json --model <TAB>
      # Shows: gpt-4o  gpt-4o-mini  o1  o1-mini  o3-mini  ...

   **Model Registry Updates:**

   The model list is automatically updated when you run ``ostruct update-registry``.
   If you encounter model validation errors, try updating your registry first.

.. option:: --timeout SECONDS

   Set timeout for API requests (default: 7200).

.. option:: --max-retries COUNT

   Maximum retry attempts for failed requests (default: 3).

Output and Execution Options
----------------------------

.. option:: --dry-run

   Validate inputs, render templates, and show execution plan without API calls.

   Performs comprehensive validation including:

   - Input file existence and accessibility
   - Template syntax validation
   - Schema structure validation
   - **Template rendering validation** (including binary file content access)
   - Security constraint verification

   This catches template errors early, such as attempting to access content
   of binary files that cannot be decoded as text.

.. option:: --dry-run-json

   Output execution plan as JSON (requires --dry-run).

.. option:: --run-summary-json

   Output run summary as JSON to stderr.

.. option:: -o, --output FILE

   Write output to file instead of stdout.

Tool Configuration Options
--------------------------

.. option:: --ci-duplicate-outputs {overwrite|rename|skip}

   Control how Code Interpreter handles duplicate output file names.

   :param overwrite: Replace existing files (default)
   :param rename: Generate unique names (file_1.txt, file_2.txt)
   :param skip: Skip files that already exist

   **Examples:**

   .. code-block:: bash

      # Generate unique names for duplicate files
      ostruct run analysis.j2 schema.json --file ci:data data.csv --ci-duplicate-outputs rename

      # Skip files that already exist
      ostruct run analysis.j2 schema.json --file ci:data data.csv --ci-duplicate-outputs skip

      # Overwrite existing files (default behavior)
      ostruct run analysis.j2 schema.json --file ci:data data.csv --ci-duplicate-outputs overwrite

   **Configuration File:**

   You can set the default behavior in ``ostruct.yaml``:

   .. code-block:: yaml

      tools:
        code_interpreter:
          duplicate_outputs: "rename"  # overwrite|rename|skip
          output_validation: "basic"   # basic|strict|off

.. option:: --ci-download-dir DIRECTORY

   Specify directory for Code Interpreter output files.

   **Examples:**

   .. code-block:: bash

      # Save outputs to custom directory
      ostruct run analysis.j2 schema.json --file ci:data data.csv --ci-download-dir ./results

Debug and Progress Options
--------------------------

.. option:: --debug

   Enable debug-level logging.

.. option:: --verbose

   Enable verbose output.

.. option:: --progress [none|basic|detailed]

   Control progress display during execution.

   :param none: Disable all progress indicators (silent operation)
   :param basic: Show key progress steps (default)
   :param detailed: Show detailed progress with additional information

   **Examples:**

   .. code-block:: bash

      # Silent operation (no progress indicators)
      ostruct run task.j2 schema.json --progress none

      # Basic progress (default)
      ostruct run task.j2 schema.json --progress basic

      # Detailed progress with additional information
      ostruct run task.j2 schema.json --progress detailed

   **Use Cases:**

   - ``--progress none``: Ideal for CI/CD pipelines and automated scripts where you want clean output
   - ``--progress basic``: Default behavior showing key milestones like file processing and API calls
   - ``--progress detailed``: Useful for debugging and monitoring long-running operations



.. option:: --template-debug CAPACITIES

   Enable template debugging with specific capacities.

   Available capacities: vars, preview, steps, optimization, pre-expand, post-expand, optimization-steps

   Use comma-separated list for multiple capacities, or 'all' for everything.

   **Examples:**

   .. code-block:: bash

      --template-debug vars              # Show variables only
      --template-debug vars,preview      # Show variables and content previews
      --template-debug post-expand       # Show final expanded template
      --template-debug all               # Show all debugging information

   .. tip::
      **Advanced Template Analysis**: For comprehensive template analysis beyond basic debugging, use the Template Analyzer meta-tool:

      .. code-block:: bash

         tools/template-analyzer/run.sh my_template.j2 my_schema.json

      This provides detailed analysis including security, performance, best practices, and OpenAI compliance checking with interactive HTML reports.

Model Name Validation
---------------------

ostruct validates model names against the OpenAI model registry to ensure compatibility.

**Available Commands:**

1. Check available models: ``ostruct list-models``
2. Update model registry: ``ostruct update-registry``

**Common Model Names:**

- **Current**: ``gpt-4o``, ``o1``, ``o3-mini``
- **Common Issues**: Check for typos like ``gpt4o`` → ``gpt-4o``

Progress Options
----------------

Control progress display during execution with a single ``--progress`` option.

**Available Options:**

- ``--progress none``: Silent operation (ideal for CI/CD pipelines)
- ``--progress basic``: Key progress steps (default)
- ``--progress detailed``: Detailed progress with additional information

See Also
========

* :doc:`quickstart` - Getting started guide
* :doc:`examples` - Practical examples and use cases
* :doc:`template_guide` - Template authoring guide
* :doc:`template_quick_reference` - Template syntax reference
* :doc:`tool_integration` - Multi-tool integration patterns
