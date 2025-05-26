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

Quick Reference Commands
------------------------

.. code-block:: bash

   # Show complete help
   ostruct --help
   ostruct run --help

   # Show quick reference for file routing
   ostruct quick-ref

   # Update model registry
   ostruct update-registry

File Routing Options
====================

ostruct provides three syntaxes for routing files to different tools, giving you flexibility for various use cases.

.. warning::
   **Security Note**: All file access is validated through the SecurityManager. Files must be within allowed directories for access.

Template Files (📄 Local Access Only)
--------------------------------------

Files routed to template access are available in your Jinja2 template but are **not uploaded** to any external services.

**Use cases:** Configuration files, small reference data, prompt templates

Auto-Naming Syntax
~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   -ft, --file-for-template PATH

   # Examples
   ostruct run task.j2 schema.json -ft config.yaml      # → config_yaml variable
   ostruct run task.j2 schema.json -ft my-file.txt      # → my_file_txt variable

Equals Syntax
~~~~~~~~~~~~~

.. code-block:: bash

   -ft, --file-for-template NAME=PATH

   # Examples
   ostruct run task.j2 schema.json -ft config=settings.yaml    # → config variable
   ostruct run task.j2 schema.json -ft data=input.json        # → data variable

Two-Argument Alias Syntax
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   --fta, --file-for-template-alias NAME PATH

   # Examples (supports tab completion for paths)
   ostruct run task.j2 schema.json --fta config settings.yaml
   ostruct run task.j2 schema.json --fta data input.json

Directory Template Access
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   -dt, --dir-for-template DIRECTORY

   # Example
   ostruct run task.j2 schema.json -dt ./config_files

Code Interpreter Files (💻 Execution + Analysis)
------------------------------------------------

Files routed to Code Interpreter are **uploaded to OpenAI** for Python execution, data analysis, and visualization generation.

**Use cases:** CSV data, Python scripts, data analysis, computational tasks

.. warning::
   **Data Upload**: Files are uploaded to OpenAI's Code Interpreter environment.

Auto-Naming Syntax
~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   -fc, --file-for-code-interpreter PATH

   # Examples
   ostruct run analyze.j2 schema.json -fc data.csv         # → data_csv variable
   ostruct run analyze.j2 schema.json -fc sales_data.xlsx  # → sales_data_xlsx variable

Equals Syntax
~~~~~~~~~~~~~

.. code-block:: bash

   -fc, --file-for-code-interpreter NAME=PATH

   # Examples
   ostruct run analyze.j2 schema.json -fc dataset=data.csv
   ostruct run analyze.j2 schema.json -fc sales=sales_data.xlsx

Two-Argument Alias Syntax
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   --fca, --file-for-code-interpreter-alias NAME PATH

   # Examples
   ostruct run analyze.j2 schema.json --fca dataset data.csv
   ostruct run analyze.j2 schema.json --fca sales sales_data.xlsx

Directory Code Interpreter Access
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   -dc, --dir-for-code-interpreter DIRECTORY

   # Example
   ostruct run analyze.j2 schema.json -dc ./datasets

Code Interpreter Options
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   --code-interpreter-download-dir DIRECTORY    # Where to save generated files (default: ./downloads)
   --code-interpreter-cleanup                   # Clean up uploaded files after execution (default: true)

File Search Files (🔍 Vector Search + Retrieval)
-------------------------------------------------

Files routed to File Search are **uploaded to OpenAI** and processed into a vector store for semantic search and retrieval.

**Use cases:** Documentation, PDFs, knowledge bases, searchable content

.. warning::
   **Data Upload**: Files are uploaded to OpenAI's File Search service and processed into vector stores.

Auto-Naming Syntax
~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   -fs, --file-for-search PATH

   # Examples
   ostruct run search.j2 schema.json -fs docs.pdf          # → docs_pdf variable
   ostruct run search.j2 schema.json -fs manual.txt        # → manual_txt variable

Equals Syntax
~~~~~~~~~~~~~

.. code-block:: bash

   -fs, --file-for-search NAME=PATH

   # Examples
   ostruct run search.j2 schema.json -fs manual=docs.pdf
   ostruct run search.j2 schema.json -fs knowledge=kb.txt

Two-Argument Alias Syntax
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   --fsa, --file-for-search-alias NAME PATH

   # Examples
   ostruct run search.j2 schema.json --fsa manual docs.pdf
   ostruct run search.j2 schema.json --fsa knowledge kb.txt

Directory File Search Access
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   -ds, --dir-for-search DIRECTORY

   # Example
   ostruct run search.j2 schema.json -ds ./documentation

File Search Options
~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   --file-search-vector-store-name NAME         # Name for vector store (default: ostruct_search)
   --file-search-cleanup                        # Clean up vector stores after use (default: true)
   --file-search-retry-count COUNT              # Retry attempts for operations (default: 3)
   --file-search-timeout SECONDS               # Timeout for indexing (default: 60.0)

Advanced File Routing
=====================

Multi-Tool Routing
------------------

Route files to specific tools using the ``--file-for`` option:

.. code-block:: bash

   --file-for TOOL PATH

   # Examples
   ostruct run task.j2 schema.json --file-for code-interpreter data.json
   ostruct run task.j2 schema.json --file-for file-search data.json
   ostruct run task.j2 schema.json --file-for template config.yaml

**Valid tools:** ``template``, ``code-interpreter``, ``file-search``

Legacy File Options
-------------------

Traditional file routing options continue to work for backward compatibility:

.. code-block:: bash

   -f, --file NAME PATH                         # Map file to template variable
   -d, --dir NAME PATH                          # Map directory to template variable
   -p, --pattern NAME PATTERN                   # Map glob pattern to template variable

Variables and Input
===================

String Variables
----------------

.. code-block:: bash

   -V, --var NAME=VALUE

   # Examples
   ostruct run task.j2 schema.json -V env=production -V debug=false

JSON Variables
--------------

.. code-block:: bash

   -J, --json-var NAME='JSON_STRING'

   # Examples
   ostruct run task.j2 schema.json -J config='{"env":"prod","debug":true}'
   ostruct run task.j2 schema.json -J settings='{"timeout":30,"retries":3}'

Model and API Configuration
===========================

Model Selection
---------------

.. code-block:: bash

   -m, --model MODEL_NAME                       # OpenAI model to use (default: gpt-4o)

**Supported models:**
- ``gpt-4o`` - 128k context window (default)
- ``o1`` - 200k context window
- ``o3-mini`` - 200k context window

Model Parameters
----------------

.. code-block:: bash

   --temperature FLOAT                          # Sampling temperature (0.0-2.0)
   --max-output-tokens INT                      # Maximum output tokens
   --top-p FLOAT                                # Top-p sampling (0.0-1.0)
   --frequency-penalty FLOAT                    # Frequency penalty (-2.0-2.0)
   --presence-penalty FLOAT                     # Presence penalty (-2.0-2.0)
   --reasoning-effort LEVEL                     # Reasoning effort (low|medium|high)

API Configuration
-----------------

.. code-block:: bash

   --api-key KEY                                # OpenAI API key (or use OPENAI_API_KEY env var)
   --timeout SECONDS                            # API timeout (default: 60.0)
   --config PATH                                # Configuration file (default: ostruct.yaml)

System Prompts
==============

ostruct provides multiple ways to specify system prompts with clear precedence rules.

Command-Line System Prompts
----------------------------

.. code-block:: bash

   --sys-prompt TEXT                            # Provide system prompt directly
   --sys-file PATH                              # Load system prompt from file
   --ignore-task-sysprompt                      # Ignore system prompt in template frontmatter

**Examples:**

.. code-block:: bash

   # Direct system prompt
   ostruct run task.j2 schema.json --sys-prompt "You are an expert data analyst"

   # From file
   ostruct run task.j2 schema.json --sys-file prompts/analyst.txt

   # Ignore template frontmatter
   ostruct run task.j2 schema.json --ignore-task-sysprompt

Template Frontmatter
--------------------

Add system prompts directly in your template:

.. code-block:: jinja

   ---
   system_prompt: You are an expert analyst specializing in financial data.
   ---
   Analyze this data: {{ data.content }}

**Shared System Prompts:**

Use ``include_system:`` to share common prompt content across templates:

.. code-block:: jinja

   ---
   include_system: shared/expert_base.txt
   system_prompt: Focus on financial metrics and trend analysis.
   ---
   Analyze this data: {{ data.content }}

The ``include_system:`` path is resolved relative to the template file location.

**Precedence Order:**
1. ``--sys-prompt`` (highest priority)
2. ``--sys-file``
3. Template frontmatter (``include_system:`` + ``system_prompt:``)
4. Default system prompt (lowest priority)

Security and Path Management
============================

Path Security
-------------

.. code-block:: bash

   --base-dir DIRECTORY                         # Base directory for relative paths
   -A, --allow DIRECTORY                        # Add allowed directory (repeatable)
   --allowed-dir-file FILE                      # File containing allowed directory paths

**Examples:**

.. code-block:: bash

   # Set base directory
   ostruct run task.j2 schema.json --base-dir /project -ft config.yaml

   # Allow specific directories
   ostruct run task.j2 schema.json -A /data -A /configs -ft file.txt

   # Load allowed directories from file
   ostruct run task.j2 schema.json --allowed-dir-file allowed_dirs.txt

Directory Processing
--------------------

.. code-block:: bash

   -R, --recursive                              # Process directories recursively

MCP Server Integration
======================

Model Context Protocol (MCP) servers extend ostruct's capabilities with external services.

.. warning::
   **External Services**: MCP servers may upload data to external services. Review server documentation for data handling policies.

Basic MCP Usage
---------------

.. code-block:: bash

   --mcp-server [LABEL@]URL                     # Connect to MCP server

   # Examples
   ostruct run task.j2 schema.json --mcp-server https://mcp.example.com/sse
   ostruct run task.j2 schema.json --mcp-server deepwiki@https://mcp.deepwiki.com/sse

MCP Configuration
-----------------

.. code-block:: bash

   --mcp-allowed-tools SERVER:TOOL1,TOOL2      # Restrict tools per server
   --mcp-require-approval LEVEL                # Approval level (always|never, default: never)
   --mcp-headers JSON_STRING                    # Headers for MCP servers

**Examples:**

.. code-block:: bash

   # Restrict tools
   ostruct run task.j2 schema.json \\
     --mcp-server deepwiki@https://mcp.deepwiki.com/sse \\
     --mcp-allowed-tools deepwiki:search,summary

   # Add headers
   ostruct run task.j2 schema.json \\
     --mcp-server secure@https://mcp.example.com \\
     --mcp-headers '{"Authorization": "Bearer token123"}'

Output and Execution Control
============================

Output Options
--------------

.. code-block:: bash

   --output-file FILE                           # Write output to file instead of stdout
   --dry-run                                    # Validate without making API calls

**Examples:**

.. code-block:: bash

   # Save to file
   ostruct run task.j2 schema.json -ft data.txt --output-file result.json

   # Test without API call
   ostruct run task.j2 schema.json -ft data.txt --dry-run

Progress and Debugging
----------------------

.. code-block:: bash

   --verbose                                    # Enable verbose logging
   --no-progress                                # Disable progress indicators
   --progress-level LEVEL                       # Progress verbosity (none|basic|detailed)
   --debug-validation                           # Show detailed validation errors
   --debug-openai-stream                        # Debug OpenAI streaming
   --show-model-schema                          # Show generated Pydantic model schema

**Examples:**

.. code-block:: bash

   # Detailed debugging
   ostruct run task.j2 schema.json -ft data.txt \\
     --verbose \\
     --debug-validation \\
     --progress-level detailed

Timeout Control
---------------

.. code-block:: bash

   --timeout SECONDS                            # Operation timeout (default: 3600)

File Routing Examples
=====================

Single Tool Examples
--------------------

.. code-block:: bash

   # Template-only access (no uploads)
   ostruct run config_analysis.j2 schema.json -ft config.yaml

   # Code Interpreter for data analysis
   ostruct run data_analysis.j2 schema.json -fc sales_data.csv

   # File Search for document retrieval
   ostruct run doc_search.j2 schema.json -fs documentation.pdf

Multi-Tool Examples
-------------------

.. code-block:: bash

   # Combined analysis with all tools
   ostruct run comprehensive.j2 schema.json \\
     -ft config.yaml \\
     -fc data.csv \\
     -fs docs.pdf

   # Custom variable names
   ostruct run analysis.j2 schema.json \\
     --fta app_config config.yaml \\
     --fca sales_data data.csv \\
     --fsa manual docs.pdf

   # Multi-tool routing
   ostruct run task.j2 schema.json \\
     --file-for code-interpreter shared_data.json \\
     --file-for file-search shared_data.json

Directory Processing
--------------------

.. code-block:: bash

   # Process directories with different tools
   ostruct run batch_analysis.j2 schema.json \\
     -dt ./config \\
     -dc ./datasets \\
     -ds ./documentation

   # Recursive processing
   ostruct run deep_analysis.j2 schema.json \\
     -dt ./config \\
     --recursive

Migration from Legacy Syntax
=============================

The enhanced CLI maintains full backward compatibility while offering improved file routing options.

Legacy vs Enhanced Syntax
-------------------------

.. code-block:: bash

   # Before (still works)
   ostruct run template.j2 schema.json \\
     -f config config.yaml \\
     -f data input.csv

   # After (enhanced)
   ostruct run template.j2 schema.json \\
     -ft config=config.yaml \\
     -fc data=input.csv

Variable Naming Patterns
------------------------

Understanding how auto-naming works:

.. list-table::
   :header-rows: 1
   :widths: 40 30 30

   * - File Path
     - Auto Variable Name
     - Description
   * - ``config.yaml``
     - ``config_yaml``
     - Replace non-alphanumeric with underscores
   * - ``my-file.txt``
     - ``my_file_txt``
     - Hyphens become underscores
   * - ``123data.csv``
     - ``_123data_csv``
     - Prepend underscore if starts with digit
   * - ``hello.world.json``
     - ``hello_world_json``
     - Multiple dots become underscores

Best Practices
==============

File Organization
-----------------

1. **Template files**: Keep configuration and small reference files
2. **Code Interpreter**: Use for computational data, analysis, visualizations
3. **File Search**: Use for documents, manuals, knowledge bases

Security Considerations
-----------------------

1. **Review data sensitivity** before uploading to Code Interpreter or File Search
2. **Use allowed directories** (``-A``) to restrict file access
3. **Set base directory** (``--base-dir``) for consistent path resolution
4. **Review MCP server policies** before connecting to external services

Performance Tips
----------------

1. **Use dry-run** (``--dry-run``) to validate templates and estimate tokens
2. **Enable cleanup** for Code Interpreter and File Search to manage quotas
3. **Set appropriate timeouts** for large file processing
4. **Use progress reporting** (``--progress-level detailed``) for long operations

Common Workflows
================

Data Analysis Pipeline
----------------------

.. code-block:: bash

   # 1. Upload data for analysis
   ostruct run analysis.j2 schema.json \\
     -fc sales_data.csv \\
     -fc customer_data.json \\
     --code-interpreter-download-dir ./results

   # 2. Search documentation for context
   ostruct run research.j2 schema.json \\
     -fs business_rules.pdf \\
     -fs process_docs.md

   # 3. Generate comprehensive report
   ostruct run report.j2 schema.json \\
     -ft config.yaml \\
     -fc analysis_results.json \\
     -fs documentation.pdf

Configuration Validation
------------------------

.. code-block:: bash

   # Compare environments
   ostruct run validate.j2 schema.json \\
     -ft dev=dev.yaml \\
     -ft prod=prod.yaml \\
     -fs infrastructure_docs.pdf

Code Review Automation
----------------------

.. code-block:: bash

   # Analyze code with documentation context
   ostruct run code_review.j2 schema.json \\
     -fc source_code/ \\
     -fs coding_standards.md \\
     -ft .eslintrc.json

Troubleshooting
===============

Common Issues
-------------

**File not found errors:**
- Verify file paths are correct
- Check that files are within allowed directories
- Use absolute paths or set ``--base-dir``

**Template rendering errors:**
- Use ``--dry-run`` to test template without API calls
- Check variable names match file routing expectations
- Verify Jinja2 syntax in templates

**API timeout errors:**
- Increase ``--timeout`` for large files
- Use File Search for large documents instead of template access
- Consider breaking large tasks into smaller chunks

**Token limit exceeded:**
- Use ``--dry-run`` to estimate token usage
- Reduce file sizes or use File Search for large documents
- Consider using models with larger context windows

Getting Help
------------

.. code-block:: bash

   # General help
   ostruct --help

   # Command-specific help
   ostruct run --help

   # Quick reference
   ostruct quick-ref

   # Update model information
   ostruct update-registry

For more information, see:

- :doc:`quickstart` - Hands-on tutorial
- :doc:`template_authoring` - Template creation guide
- :doc:`../security/overview` - Security considerations
