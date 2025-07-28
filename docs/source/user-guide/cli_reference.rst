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

ostruct provides several commands for different use cases:

**Main Commands:**

- ``ostruct run TEMPLATE_FILE SCHEMA_FILE [OPTIONS]`` - Execute templates with separate schema files
- ``ostruct runx TEMPLATE_FILE [ARGS]`` - Execute OST files (self-executing ostruct prompts)
- ``ostruct files COMMAND`` - Manage file uploads and cache inventory
- ``ostruct scaffold COMMAND`` - Generate template files and project scaffolding
- ``ostruct setup COMMAND`` - Environment setup and configuration
- ``ostruct models list`` - List available OpenAI models
- ``ostruct models update`` - Update model registry

.. note::
   **Deprecated Commands**: The standalone ``ostruct list-models`` and ``ostruct update-registry`` commands are deprecated and will be removed in the next minor version. Use the ``models`` subcommands instead.

**Command Details:**

The ``run`` command is the primary interface for traditional ostruct usage. All file processing, model configuration, and tool integration happens through this command with various options.

The ``runx`` command executes OST files (self-executing ostruct prompts) that contain embedded schemas and CLI metadata in their YAML front-matter.

File and Directory Management
-----------------------------

**File Attachment System**:

- ``--file [targets:]alias path``: Attach file with explicit tool targeting
- ``--dir [targets:]alias path``: Attach directory with explicit tool targeting
- ``--collect [targets:]alias @filelist``: Attach file collection from list

**Targets**: ``prompt`` (template-only, default), ``ci`` (code-interpreter), ``fs`` (file-search), ``ud`` (user-data, PDF files for vision models), ``auto`` (auto-route based on content type)

**Auto-routing**: The ``auto`` target uses file type detection to automatically route files:

- **Text files** → ``prompt`` (template access)
- **Binary files** → ``ud`` (user-data for vision models)
- **Detection method**: Uses enhanced detection (Magika) if available, otherwise extension-based detection
- **Install enhanced detection**: ``pip install ostruct-cli[enhanced-detection]``

**Examples**:

- ``--file config settings.yaml``: Template access only
- ``--file ci:data analysis.csv``: Upload to Code Interpreter
- ``--file fs:docs manual.pdf``: Upload to File Search
- ``--file ud:deck pitch.pdf``: Attach PDF for vision model analysis (user-data)
- ``--file auto:content document.txt``: Auto-route based on file type (text → prompt, binary → user-data)
- ``--file ci,fs:shared data.json``: Multi-tool routing

**Security & Path Control**:

- ``--recursive``: Apply recursive processing to all --dir and --collect attachments
- ``--pattern GLOB``: Apply glob pattern to all --dir and --collect attachments
- ``-S, --path-security [permissive|warn|strict]``: Path security mode (default: warn)
- ``--allow DIR``: Add an allowed directory for security (repeatable)
- ``--allow-list FILE``: File containing allowed directory paths
- ``--allow-insecure-url URL``: Explicitly allow a specific HTTP or private-IP URL (repeatable)
- ``--strict-urls/--no-strict-urls``: Toggle strict URL validation (default: strict)
- *User-data limits*: PDF uploads are capped at **512 MB** (warning above 50 MB)
- ``--max-file-size SIZE``: Maximum file size for template processing (supports KB, MB, GB suffixes or "unlimited"/"none")

**File Collection Options**:

- ``--ignore-gitignore``: Ignore .gitignore files when collecting directory files (default: respect .gitignore)
- ``--gitignore-file PATH``: Use custom gitignore file instead of default .gitignore

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

**Tool Choice**:

- ``--tool-choice [auto|none|required|code-interpreter|file-search|web-search]``: Explicitly control how (or whether) tools are used in this run. The default *auto* behaviour lets
  the model pick any advertised tool. Use **none** to disable tool calls entirely (template-only),
  **required** to force that at least one tool is invoked, or specify a single tool name to restrict
  the run to that tool alone (e.g. ``--tool-choice file-search``). This option overrides
  ``--enable-tool/--disable-tool`` resolution but does not implicitly enable a tool that has been
  disabled.

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
   - ``OSTRUCT_TEMPLATE_FILE_LIMIT``: Max individual file size for template access (default: unlimited, supports size suffixes or "unlimited"/"none")
   - ``OSTRUCT_TEMPLATE_TOTAL_LIMIT``: Max total file size for template processing (default: 1048576 bytes)
   - ``OSTRUCT_TEMPLATE_PREVIEW_LIMIT``: Max characters in template debug previews (default: 4096)

3. Environment variables (file collection configuration):
   - ``OSTRUCT_IGNORE_GITIGNORE``: Set to "true" to ignore .gitignore files by default (default: "false")
   - ``OSTRUCT_GITIGNORE_FILE``: Default path to gitignore file (default: ".gitignore")

Example:

.. code-block:: bash

   # Set template processing limits
   export OSTRUCT_TEMPLATE_FILE_LIMIT=128KB  # 128KB (or "unlimited"/"none" for no limit)
   export OSTRUCT_TEMPLATE_TOTAL_LIMIT=2097152  # 2MB

   # Configure gitignore behavior
   export OSTRUCT_IGNORE_GITIGNORE=true  # Ignore .gitignore by default
   export OSTRUCT_GITIGNORE_FILE=.custom-ignore  # Use custom gitignore file

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
   ostruct models update

.. warning::
   **Experimental Feature: --help-json**

   The ``--help-json`` option is **experimental** and subject to change. The JSON format it produces is **not yet stable** and is likely to change in future versions without notice.

   - **Use with caution** in production scripts or automation
   - **Format may change** between versions without backward compatibility
   - **Intended for development** and testing purposes only

OST (Self-Executing Templates) Commands
=======================================

The ``runx`` command executes OST files (self-executing ostruct prompts) that contain embedded schemas and CLI metadata in their YAML front-matter.

ostruct runx
------------

Execute an OST (Self-Executing Template) file.

.. code-block:: text

   Usage: ostruct runx [OPTIONS] TEMPLATE_FILE [ARGS]...

   Execute an OST file (self-executing ostruct prompt).
   This command executes .ost files that contain embedded schemas and CLI metadata in their
   YAML front-matter. Each OST file acts as a self-contained tool with its own argument parsing,
   help system, and policy enforcement.

   TEMPLATE_FILE: Path to the .ost file (self-executing ostruct prompt) to execute
   ARGS: Arguments to pass to the template

   Examples:
     ostruct runx hello.ost --name "World"
     ostruct runx analysis.ost data.csv --format json

   Options:
     TEMPLATE_FILE  (PATH) [required]
     ARGS           (TEXT)
     --help    -h   Show this message and exit.

**Key Features:**

- **Embedded Schema**: Schema is defined in the template's YAML front-matter
- **Custom CLI**: Each template defines its own command-line interface
- **Policy Enforcement**: Global argument policies control ostruct flag usage
- **Cross-Platform**: Works on Unix/Linux/macOS via shebang, Windows via command
- **Self-Contained**: Templates are portable and include all necessary metadata

**Usage Examples:**

.. code-block:: bash

   # Execute OST template directly
   ostruct runx my_tool.ost "input text" --format json

   # Unix/Linux/macOS: Direct execution via shebang
   ./my_tool.ost "input text" --format json

   # Get help for the template (auto-generated)
   ostruct runx my_tool.ost --help

   # Dry run to test without API calls
   ostruct runx my_tool.ost "test input" --dry-run

Template Scaffolding Commands
=============================

The ``scaffold`` command helps you generate template files and project scaffolding.

ostruct scaffold
----------------

Generate template files and project scaffolding.

.. code-block:: text

   Usage: ostruct scaffold [OPTIONS] COMMAND [ARGS]...

   Generate template files and project scaffolding.

   Options:
     --help    Show this message and exit.

   Commands:
     template  Generate a template file.

ostruct scaffold template
~~~~~~~~~~~~~~~~~~~~~~~~~

Generate a template file with optional CLI front-matter.

.. code-block:: text

   Usage: ostruct scaffold template [OPTIONS] OUTPUT_FILE

   Generate a template file.
   OUTPUT_FILE: Path where the template file will be created

   Options:
     OUTPUT_FILE           (PATH) [required]
     --cli                 Generate an OST (Self-Executing Template) with CLI front-matter
     --name TEXT           Name for the CLI tool (default: derived from filename)
     --description TEXT    Description for the CLI tool (default: generic description)
     --no-examples         Don't show usage examples after creation
     --windows-launcher    Generate Windows launcher files (.exe and .cmd) alongside OST
     --help                Show this message and exit.

**Usage Examples:**

.. code-block:: bash

   # Generate a basic Jinja2 template
   ostruct scaffold template analysis.j2

   # Generate an OST template with CLI interface
   ostruct scaffold template text-analyzer.ost --cli

   # Generate with custom name and description
   ostruct scaffold template my-tool.ost --cli \
     --name "data-processor" \
     --description "Processes and analyzes data files"

Environment Setup Commands
==========================

The ``setup`` command provides environment configuration for ostruct.

ostruct setup
-------------

Environment setup and configuration commands.

.. code-block:: text

   Usage: ostruct setup [OPTIONS] COMMAND [ARGS]...

   Environment setup and configuration commands.

   Options:
     --help    Show this message and exit.

   Commands:
     windows-register    Register OST file associations and PATHEXT on Windows.
     windows-unregister  Unregister OST file associations and PATHEXT on Windows.

**Subcommands:**

ostruct setup windows-register
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Register OST file associations and PATHEXT on Windows.

This command configures Windows to recognize ``.ost`` files and allows them to be executed directly from the command line.

**What it does:**

- Registers ``.ost`` file association with ostruct
- Adds ``.OST`` to the ``PATHEXT`` environment variable
- Enables direct execution of OST files in Command Prompt and PowerShell

**Usage:**

.. code-block:: bash

   # Register OST file associations (Windows only)
   ostruct setup windows-register

**Requirements:**

- Windows operating system
- Administrator privileges (for system-wide registration)
- ostruct-cli installed and available in PATH

.. note::
   **Security Note**: The Windows launcher executable is generated using distlib's simple-launcher technology. This is the same trusted binary infrastructure that pip itself uses for console scripts. Since this binary is already present on every system with pip installed, it significantly reduces the likelihood of antivirus false positives compared to custom executable generation. For more details, see the `distlib documentation <https://github.com/pypa/distlib/issues/192>`_ and `PyPI project page <https://pypi.org/project/distlib/>`_.

ostruct setup windows-unregister
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Unregister OST file associations and PATHEXT on Windows.

This command removes the Windows file associations and PATHEXT modifications created by ``windows-register``.

**Usage:**

.. code-block:: bash

   # Unregister OST file associations (Windows only)
   ostruct setup windows-unregister

**Use Cases:**

- Uninstalling ostruct
- Switching to a different OST handler
- Troubleshooting file association issues

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

Tool Token Consumption
~~~~~~~~~~~~~~~~~~~~~~

File Search and Code Interpreter tools consume additional tokens beyond your template content:

**File Search:**
- Automatically injects 15K-25K tokens of retrieved content per query
- Multiple files = multiple content injections
- Source: `OpenAI Community Discussion <https://community.openai.com/t/processing-large-documents-128k-limit/620347>`_

**Code Interpreter:**
- Base session cost: ~387 tokens per session
- File processing overhead varies by operation
- Source: `OpenAI Documentation <https://platform.openai.com/docs/assistants/tools/code-interpreter>`_

**Token Validation:**
ostruct validates that your template + template files fit within the context window.
Tool files are not counted in this validation, but tools will consume additional tokens at runtime.

Security Modes
--------------

Control file access with enhanced security options:

.. option:: -S, --path-security MODE

   Set path security mode for file access validation.

   :param MODE: Security level (permissive, warn, strict)

   - ``permissive``: Allow all file access (no warnings)
   - ``warn``: Allow with helpful security notices for external files (default)
   - ``strict``: Only allow explicitly permitted paths

   **Warning behavior in warn mode:**

   - Shows user-friendly security notices for files outside project directory
   - Provides actionable CLI guidance (exact flags to resolve warnings)
   - Deduplicates warnings (one warning per file per session)
   - Includes contextual file type information (document, data file, etc.)
   - Shows security summary at end if multiple external files accessed

.. option:: --allow DIR

   Add allowed directory for security (can be used multiple times).

   Grants access to the specified directory and all its contents.
   Resolves security warnings for files within this directory.

.. option:: --allow-file FILE

   Allow specific file access.

   Grants access to one specific file only. More restrictive than ``--allow``
   but useful when you need access to a single external file.

.. option:: --allow-list FILE

   Load allowed paths from file.

   Each line in the file should contain one directory path. Blank lines
   and lines starting with ``#`` are ignored.

.. option:: --allow-insecure-url URL

   Explicitly allow a specific HTTP or private-IP URL (repeatable).

.. option:: --strict-urls/--no-strict-urls

   Toggle strict URL validation (default: strict).

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

File Attachment Helpers
========================

ostruct provides two workflows for handling files in templates:

**Text Workflow (XML Appendix)**

For including file content as text in an XML appendix:

.. code-block:: jinja

   Review the configuration in {{ get_embed_ref("config") }}.

   {{ embed_text("config") }}

**Binary Workflow (Vision/Code Interpreter)**

For direct model access to files (vision, code execution):

.. code-block:: jinja

   Analyze {{ get_file_ref("chart.png") }} for trends.

   {{ attach_file("chart.png") }}

Template Helper Reference
-------------------------

.. function:: attach_file(path)

   Attach a file for binary model access (vision/code interpreter).

   :param path: Path to file to attach
   :returns: Placeholder (replaced with API structures)
   :side-effects: Registers file for binary attachment

.. function:: get_file_ref(path)

   Get the deterministic label for a file.

   :param path: Path to file
   :returns: Label string (e.g., "FILE A", "document-1")

.. function:: embed_text(alias)

   Schedule file content for XML appendix inclusion.

   :param alias: File alias from CLI attachment
   :returns: Empty string
   :side-effects: Registers alias for appendix inclusion

.. function:: get_embed_ref(alias)

   Get reference tag for embedded content.

   :param alias: File alias from CLI attachment
   :returns: Reference string (e.g., "<config>")

.. function:: file_ref(alias)

   **Deprecated:** Use ``get_embed_ref()`` + ``embed_text()`` instead.

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

Directory Collection with Gitignore Support
-------------------------------------------

Control file collection from directories using gitignore patterns:

.. code-block:: bash

   # Respect .gitignore files (default behavior)
   ostruct run analyze.j2 schema.json --dir source ./project --recursive

   # Ignore .gitignore files and collect all files
   ostruct run analyze.j2 schema.json --dir source ./project --recursive --ignore-gitignore

   # Use custom gitignore file
   ostruct run analyze.j2 schema.json --dir source ./project --recursive --gitignore-file .custom-ignore

   # Upload to Code Interpreter with gitignore filtering
   ostruct run analyze.j2 schema.json --dir ci:codebase ./src --recursive

.. note::
   **Gitignore Behavior**: When collecting files from directories recursively, ostruct respects ``.gitignore`` files by default. This prevents sensitive files (like ``.env``, ``node_modules/``, or ``__pycache__/``) from being included. Use ``--ignore-gitignore`` to override this behavior when needed.

   For comprehensive gitignore usage, patterns, and troubleshooting, see the :doc:`gitignore_guide`.

Global Directory Processing Flags
---------------------------------

The ``--recursive`` and ``--pattern`` flags apply **globally** to all ``--dir`` and ``--collect`` attachments in a single command, following standard CLI conventions:

.. code-block:: bash

   # Both directories become recursive
   ostruct run template.j2 schema.json \
     --dir src ./source \
     --dir tests ./test_files \
     --recursive

   # Both directories get the pattern applied
   ostruct run template.j2 schema.json \
     --dir code ./src \
     --dir configs ./config \
     --pattern "*.py"

   # Combined: both directories are recursive with pattern
   ostruct run template.j2 schema.json \
     --dir ci:codebase ./src \
     --dir ci:tests ./tests \
     --recursive --pattern "*.py"

.. note::
   **Global Flag Behavior**: Unlike some CLI tools that apply flags only to the preceding argument, ostruct applies ``--recursive`` and ``--pattern`` to **all applicable attachments** in the command. This follows the same pattern as tools like ``cp``, ``rsync``, and ``ls`` where flags affect all targets.

**Examples of global behavior:**

.. code-block:: bash

   # Standard: All directories become recursive
   ostruct run analyze.j2 schema.json \
     --dir source ./src \
     --dir docs ./documentation \
     --dir tests ./test_suite \
     --recursive

   # Mixed targets: Only directories are affected by flags
   ostruct run process.j2 schema.json \
     --file config ./config.yaml \
     --dir ci:data ./datasets \
     --dir fs:docs ./docs \
     --file prompt:readme ./README.md \
     --recursive --pattern "*.json"
   # Result: config.yaml and README.md are unaffected
   #         datasets/ and docs/ are both recursive with *.json pattern

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
      ostruct models list

      # Invalid models are rejected with helpful suggestions
      ostruct run template.j2 schema.json --model invalid-model
      # Error: Invalid model 'invalid-model'. Available models: gpt-4o, gpt-4o-mini, o1 (and 15 more).
      #        Run 'ostruct models list' to see all 18 available models.

   **Shell Completion:**

   When shell completion is enabled, the ``--model`` parameter will auto-complete
   with available model names:

   .. code-block:: bash

      ostruct run template.j2 schema.json --model <TAB>
      # Shows: gpt-4o  gpt-4o-mini  o1  o1-mini  o3-mini  ...

   **Model Registry Updates:**

   The model list is automatically updated when you run ``ostruct models update``.
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

Upload Cache Options
--------------------

.. seealso::
   For comprehensive information about the upload cache system, including configuration, TTL management, and troubleshooting, see :doc:`upload_cache_guide`.

.. option:: --files-label-style {alpha,filename}

   Label style for file attachments (default: alpha).

   Controls how files are labeled in template helpers and references.

   - ``alpha``: Generate labels like "FILE A", "FILE B", "FILE C"
   - ``filename``: Use basenames like "config.yaml", "data.txt"

   **Examples:**

   .. code-block:: bash

      # Use filename-based labels
      ostruct run template.j2 schema.json --files-label-style filename

      # Use alphabetic labels (default)
      ostruct run template.j2 schema.json --files-label-style alpha

.. option:: --cache-uploads / --no-cache-uploads

   Enable or disable the persistent upload cache (default: enabled).

   When enabled, ostruct caches uploaded files to avoid duplicate uploads
   across runs, providing significant performance improvements.

   **Examples:**

   .. code-block:: bash

      # Disable cache for this run
      ostruct run template.j2 schema.json --no-cache-uploads

      # Explicitly enable cache (default behavior)
      ostruct run template.j2 schema.json --cache-uploads

.. option:: --cache-preserve / --no-cache-preserve

   Enable or disable TTL-based cache preservation (default: enabled).

   When enabled, cached files are preserved for the configured TTL period.
   When disabled, all cached files are deleted after each run.

   **Examples:**

   .. code-block:: bash

      # Force cleanup of all cached files
      ostruct run template.j2 schema.json --no-cache-preserve

      # Use TTL-based preservation (default)
      ostruct run template.j2 schema.json --cache-preserve

.. option:: --cache-path PATH

   Specify custom path for the upload cache database.

   **Examples:**

   .. code-block:: bash

      # Use custom cache location
      ostruct run template.j2 schema.json --cache-path ~/.my-cache/uploads.db

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

1. Check available models: ``ostruct models list``
2. Update model registry: ``ostruct models update``

**Common Model Names:**

- **Current**: ``gpt-4o``, ``o1``, ``o3-mini``
- **Common Issues**: Check for typos like ``gpt4o`` → ``gpt-4o``

Progress Options
----------------

Control progress display during execution with a single ``--progress`` option.
This option is available for both ``ostruct run`` and ``ostruct files`` commands.

**Available Options:**

- ``--progress none``: Silent operation (ideal for CI/CD pipelines)
- ``--progress basic``: Key progress steps with progress bars for batch operations (default)
- ``--progress detailed``: Basic level plus per-item details and verbose information

**Examples:**

.. code-block:: bash

   # Silent operation (no progress indicators)
   ostruct run task.j2 schema.json --progress none
   ostruct files upload --file data.csv --progress none

   # Basic progress with progress bars (default)
   ostruct run task.j2 schema.json --progress basic
   ostruct files upload --file *.pdf --progress basic

   # Detailed progress with per-item details
   ostruct run task.j2 schema.json --progress detailed
   ostruct files upload --dir ./docs --progress detailed

Troubleshooting
===============

File Type Detection Issues
---------------------------

**"Magika not available" Warning**:

If you see warnings about Magika not being available, this affects auto-routing accuracy but doesn't break functionality:

.. code-block:: text

   WARNING: Magika not available - falling back to extension detection.
   Install with: pip install ostruct-cli[enhanced-detection]

**Solutions**:

1. **Install enhanced detection** (recommended):

   .. code-block:: bash

      pip install ostruct-cli[enhanced-detection]

2. **Use explicit routing** instead of ``auto``:

   .. code-block:: bash

      # Instead of --file auto:content file.txt
      ostruct run template.j2 schema.json --file content file.txt

3. **Alpine Linux users**: Enhanced detection may not install due to compilation requirements. The extension-based fallback works reliably for common file types.

**Supported Extensions (Fallback Mode)**:

Text files automatically routed to template: ``.txt``, ``.md``, ``.rst``, ``.json``, ``.yaml``, ``.yml``, ``.toml``, ``.ini``, ``.cfg``, ``.py``, ``.js``, ``.html``, ``.css``, ``.sql``, ``.sh``, ``.log``, ``.csv``, ``.env``, and 15+ others.

Files Management Commands
=========================

The ``ostruct files`` command provides dedicated file management functionality separate from the main ``ostruct run`` command. These commands help you manage file uploads, cache inventory, and file-tool bindings.

ostruct files upload
--------------------

Upload files with batch support, tool binding, and caching.

.. code-block:: text

   Usage: ostruct files upload [OPTIONS]

   Upload files with batch support and interactive mode.

**File Input Options:**

.. option:: --file PATH

   Upload individual files (repeatable).

   **Examples:**

   .. code-block:: bash

      # Single file
      ostruct files upload --file document.pdf

      # Multiple files
      ostruct files upload --file doc1.pdf --file doc2.csv --file chart.png

      # Glob patterns
      ostruct files upload --file "*.pdf"

.. option:: --dir PATH

   Upload directories recursively (repeatable).

   **Examples:**

   .. code-block:: bash

      # Single directory
      ostruct files upload --dir ./documentation

      # Multiple directories
      ostruct files upload --dir ./docs --dir ./data

.. option:: --collect @FILELIST

   Upload files listed in text file (repeatable).

   **Examples:**

   .. code-block:: bash

      # Single collection
      ostruct files upload --collect @file-list.txt

      # Multiple collections
      ostruct files upload --collect @docs.txt --collect @data.txt

**Tool Binding Options:**

.. option:: --tools TOOLS

   Comma-separated list of tools to bind files to.

   **Available tools:**

   - ``user-data``: Template access only (default)
   - ``file-search``: Upload to File Search vector store
   - ``code-interpreter``: Upload to Code Interpreter

   **Examples:**

   .. code-block:: bash

      # Default (user-data only)
      ostruct files upload --file data.csv

      # File Search
      ostruct files upload --file manual.pdf --tools file-search

      # Code Interpreter
      ostruct files upload --file analysis.py --tools code-interpreter

      # Multiple tools
      ostruct files upload --file data.json --tools file-search,code-interpreter

**Metadata and Organization:**

.. option:: --tag KEY=VALUE

   Add metadata tags to files (repeatable).

   **Examples:**

   .. code-block:: bash

      # Single tag
      ostruct files upload --file report.pdf --tag project=alpha

      # Multiple tags
      ostruct files upload --file data.csv --tag project=beta --tag type=analysis

.. option:: --vector-store NAME

   Named vector store for file search (default: "ostruct").

   **Examples:**

   .. code-block:: bash

      # Custom vector store
      ostruct files upload --file docs.pdf --tools file-search --vector-store project_docs

.. option:: --pattern GLOB

   Global file pattern filter.

   **Examples:**

   .. code-block:: bash

      # Filter by extension
      ostruct files upload --dir ./mixed --pattern "*.pdf"

      # Filter by name pattern
      ostruct files upload --dir ./logs --pattern "error_*.log"

**Execution Options:**

.. option:: --dry-run

   Preview uploads without making API calls.

   **Examples:**

   .. code-block:: bash

      # Preview file upload
      ostruct files upload --file *.pdf --dry-run

.. option:: --progress [none|basic|detailed]

   Control progress display (default: basic).

   **Examples:**

   .. code-block:: bash

      # Silent operation
      ostruct files upload --file data.csv --progress none

      # Detailed progress
      ostruct files upload --dir ./docs --progress detailed

.. option:: --json

   Output machine-readable JSON.

   **Examples:**

   .. code-block:: bash

      # JSON output
      ostruct files upload --file data.csv --json

**Usage Examples:**

.. code-block:: bash

   # Interactive mode (no arguments)
   ostruct files upload

   # Single file with metadata
   ostruct files upload --file chart.png --tag project=alpha --tag type=visualization

   # Batch upload with file search
   ostruct files upload --file doc1.pdf --file doc2.pdf --tools file-search

   # Directory upload with pattern filtering
   ostruct files upload --dir ./docs --pattern '*.pdf' --tools file-search

   # Collection upload with code interpreter
   ostruct files upload --collect @data-files.txt --tools code-interpreter

   # Mixed inputs with multiple tools
   ostruct files upload --file config.yaml --dir ./data --tools file-search,code-interpreter

ostruct files list
------------------

Show cache inventory and file information.

.. code-block:: text

   Usage: ostruct files list [OPTIONS]

   Show cache inventory.

**Options:**

.. option:: --json

   Output machine-readable JSON.

.. option:: --vector-store NAME

   Filter by specific vector store name.

.. option:: --tool TOOL

   Filter by tool bindings (repeatable). Available choices: user-data, ud, code-interpreter, ci, file-search, fs.

.. option:: --tag KEY=VALUE

   Filter by tag metadata (repeatable, AND logic).

.. option:: --columns COLUMNS

   Comma-separated column names: FILE_ID,SIZE,UPLOADED,TOOLS,TAGS,PATH.

.. option:: --no-truncate

   Show full column values without truncation.

.. option:: --max-col-width WIDTH

   Maximum width for variable-width columns (default: 50).

**Examples:**

.. code-block:: bash

   # List all cached files
   ostruct files list

   # JSON output
   ostruct files list --json

   # Filter by vector store
   ostruct files list --vector-store project_docs

   # Filter by tool bindings
   ostruct files list --tool fs --tool ci

   # Filter by tags
   ostruct files list --tag project=alpha --tag type=document

   # Custom columns display
   ostruct files list --columns FILE_ID,TOOLS,PATH

   # No truncation
   ostruct files list --no-truncate

ostruct files gc
----------------

Garbage-collect expired cache entries.

.. code-block:: text

   Usage: ostruct files gc [OPTIONS]

   Garbage-collect expired cache entries.

**Options:**

.. option:: --older-than DURATION

   TTL for garbage collection (e.g., 30d, 7d) (default: 90d).

.. option:: --json

   Output machine-readable JSON.

**Examples:**

.. code-block:: bash

   # Clean files older than 30 days
   ostruct files gc --older-than 30d

   # Clean files older than 7 days with JSON output
   ostruct files gc --older-than 7d --json

ostruct files bind
------------------

Attach cached file to one or more tools.

.. code-block:: text

   Usage: ostruct files bind FILE_ID [OPTIONS]

   Attach cached file to one or more tools.

**Arguments:**

.. option:: FILE_ID

   The file ID of the cached file to bind.

**Options:**

.. option:: --tools TOOL

   Tools to bind the cached file to (repeatable). Available choices: user-data, file-search, code-interpreter.

.. option:: --json

   Output machine-readable JSON.

**Examples:**

.. code-block:: bash

   # Bind file to file-search
   ostruct files bind file_abc123 --tools file-search

   # Bind file to multiple tools
   ostruct files bind file_abc123 --tools file-search --tools code-interpreter

   # JSON output
   ostruct files bind file_abc123 --tools file-search --json

ostruct files rm
----------------

Delete remote file and purge from cache.

.. code-block:: text

   Usage: ostruct files rm FILE_ID [OPTIONS]

   Delete remote file and purge from cache.

**Arguments:**

.. option:: FILE_ID

   The file ID of the file to delete.

**Options:**

.. option:: --json

   Output machine-readable JSON.

**Examples:**

.. code-block:: bash

   # Delete file
   ostruct files rm file_abc123

   # Delete with JSON output
   ostruct files rm file_abc123 --json

ostruct files diagnose
----------------------

Live probes (head / vector / sandbox) to test file accessibility.

.. code-block:: text

   Usage: ostruct files diagnose FILE_ID [OPTIONS]

   Live probes (head / vector / sandbox).

**Arguments:**

.. option:: FILE_ID

   The file ID to diagnose.

**Options:**

.. option:: --json

   Output machine-readable JSON.

**Examples:**

.. code-block:: bash

   # Run diagnostic probes
   ostruct files diagnose file_abc123

   # Diagnostic with JSON output
   ostruct files diagnose file_abc123 --json

**Probe Types:**

- **head**: Tests if file exists and is accessible
- **vector**: Tests file-search functionality with actual vector stores
- **sandbox**: Tests code-interpreter functionality with the file

ostruct files vector-stores
---------------------------

List available vector stores and their contents.

.. code-block:: text

   Usage: ostruct files vector-stores [OPTIONS]

   List available vector stores and their contents.

**Options:**

.. option:: --json

   Output machine-readable JSON.

**Examples:**

.. code-block:: bash

   # List vector stores
   ostruct files vector-stores

   # JSON output
   ostruct files vector-stores --json

File Error Handling
-------------------

The files commands implement comprehensive error handling following Unix conventions. All file-related errors use exit code 9 (``FILE_ERROR``) for consistency.

**Error Categories:**

**File Not Found (Exit Code 9):**

.. code-block:: bash

   # Missing individual file
   ostruct files upload --file nonexistent.txt
   # Output: ❌ Error: File not found: nonexistent.txt

   # Glob pattern with no matches
   ostruct files upload --file "*.nonexistent"
   # Output: ❌ Error: No files match pattern: *.nonexistent

**Directory Errors (Exit Code 9):**

.. code-block:: bash

   # Missing directory
   ostruct files upload --dir nonexistent_dir
   # Output: ❌ Error: Directory not found: nonexistent_dir

   # Path is not a directory
   ostruct files upload --dir regular_file.txt
   # Output: ❌ Error: Path is not a directory: regular_file.txt

**Collection File Errors (Exit Code 9):**

.. code-block:: bash

   # Missing collection file
   ostruct files upload --collect @missing_list.txt
   # Output: ❌ Error: Collection file not found: missing_list.txt

   # File in collection doesn't exist
   ostruct files upload --collect @list_with_missing_files.txt
   # Output: ❌ Error: File not found (from collection list_with_missing_files.txt): missing.txt

**Permission Errors (Exit Code 9):**

.. code-block:: bash

   # Unreadable file
   ostruct files upload --file unreadable.txt
   # Output: ❌ Error: Permission denied: unreadable.txt

**Symlink Errors (Exit Code 9):**

.. code-block:: bash

   # Broken symlink
   ostruct files upload --file broken_link.txt
   # Output: ❌ Error: Broken symlink: broken_link.txt -> /nonexistent/target

**Error Behavior:**

- **Fail Fast**: Stop on first error, don't process any files
- **Early Validation**: Errors are caught before dry-run preview or file processing
- **Consistent Exit Codes**: All file-related errors use exit code 9
- **JSON Error Format**: Structured error output with metadata when using ``--json``

**JSON Error Output:**

.. code-block:: json

   {
     "data": {
       "exit_code": 9,
       "error": "File not found: nonexistent.txt"
     },
     "metadata": {
       "operation": "upload",
       "timestamp": "2024-01-15T10:30:00Z"
     }
   }

**Warning vs Error Cases:**

- **Errors (Exit Code 9)**: Explicitly specified files/directories that don't exist
- **Warnings (Exit Code 0)**: Empty directories, empty collections, no files after pattern filtering

.. code-block:: bash

   # Error: Explicit file missing
   ostruct files upload --file missing.txt
   # Exit code: 9

   # Warning: Empty directory (but continues)
   ostruct files upload --dir empty_directory
   # Exit code: 0, shows: "No files found matching criteria."

   # Warning: Pattern filters out all files (but continues)
   ostruct files upload --file existing.txt --pattern "*.nonexistent"
   # Exit code: 0, shows: "No files found matching criteria."

See Also
========

* :doc:`quickstart` - Getting started guide
* :doc:`examples` - Practical examples and use cases
* :doc:`template_guide` - Template authoring guide
* :doc:`template_quick_reference` - Template syntax reference
* :doc:`upload_cache_guide` - Upload cache configuration and management
* :doc:`tool_integration` - Multi-tool integration patterns
