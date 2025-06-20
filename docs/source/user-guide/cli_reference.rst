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

.. note::
   **New in v0.8.0**: Enhanced file routing with three flexible syntax options:

   1. **Auto-naming** (``-ft config.yaml``) - Generates variable names automatically
   2. **Two-argument** (``-ft config settings.yaml``) - Explicit variable naming
   3. **Alias flags** (``--fta config settings.yaml``) - Two-argument with tab completion

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

.. note::
   **File Content Access**: In templates, use ``{{ variable.content }}`` to access file contents.

   Example: ``{{ config_yaml.content }}`` for the file content.

Two-Argument Syntax
~~~~~~~~~~~~~~~~~~~

.. note::
   **Important**: The basic ``-ft`` flag only supports auto-naming. For custom variable names, use ``--fta``.

.. code-block:: bash

   # Two-argument syntax is NOT supported by -ft:
   # ostruct run task.j2 schema.json -ft config settings.yaml    # ❌ This will fail

   # Use --fta instead for custom variable names:
   # See "Two-Argument Alias Syntax" section below

Two-Argument Alias Syntax
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   --fta, --file-for-template-alias NAME PATH

   # Examples (supports tab completion for paths)
   ostruct run task.j2 schema.json --fta config settings.yaml
   ostruct run task.j2 schema.json --fta data input.json

.. note::
   **Important**: To access file content in templates, use ``{{ variable.content }}``, not just ``{{ variable }}``.

   Example: ``{{ config.content }}`` to get file contents.

Directory Template Access (Auto-Naming)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   -dt, --dir-for-template DIRECTORY

   # Example
   ostruct run task.j2 schema.json -dt ./config_files    # → config_files variable

Directory Template Access (Custom Alias)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   --dta, --dir-for-template-alias NAME DIRECTORY

   # Examples (supports tab completion for paths)
   ostruct run task.j2 schema.json --dta app_config ./settings
   ostruct run task.j2 schema.json --dta source_code ./src

.. tip::
   **When to Use Directory Aliases**: Use ``--dta`` for reusable templates that need stable variable names regardless of actual directory names. Use ``-dt`` for specific directory structures where the auto-generated name is acceptable.

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

Two-Argument Syntax
~~~~~~~~~~~~~~~~~~~

.. note::
   **Important**: The basic ``-fc`` flag only supports auto-naming. For custom variable names, use ``--fca``.

.. code-block:: bash

   # Two-argument syntax is NOT supported by -fc:
   # ostruct run analyze.j2 schema.json -fc dataset data.csv    # ❌ This will fail

   # Use --fca instead for custom variable names:
   # See "Two-Argument Alias Syntax" section below

Two-Argument Alias Syntax
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   --fca, --file-for-code-interpreter-alias NAME PATH

   # Examples
   ostruct run analyze.j2 schema.json --fca dataset data.csv
   ostruct run analyze.j2 schema.json --fca sales sales_data.xlsx

Directory Code Interpreter Access (Auto-Naming)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   -dc, --dir-for-code-interpreter DIRECTORY

   # Example
   ostruct run analyze.j2 schema.json -dc ./datasets      # → datasets variable

Directory Code Interpreter Access (Custom Alias)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   --dca, --dir-for-code-interpreter-alias NAME DIRECTORY

   # Examples (supports tab completion for paths)
   ostruct run analyze.j2 schema.json --dca training_data ./data
   ostruct run analyze.j2 schema.json --dca code_files ./src

.. tip::
   **When to Use Directory Aliases**: Use ``--dca`` for analysis templates that need to work with different datasets or directories. Use ``-dc`` when the directory name clearly indicates its contents.

Code Interpreter Options
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   --code-interpreter-download-dir DIRECTORY    # Where to save generated files (default: ./downloads)
   --code-interpreter-cleanup                   # Clean up uploaded files after execution (default: true)

.. note::
   **File Download Issue**: When using Code Interpreter with structured output (JSON schemas), OpenAI's API may not generate file download annotations, preventing automatic file downloads. Use the feature flag workaround if you encounter this issue.

.. code-block:: bash

   # Enable reliable file downloads (workaround for OpenAI bug)
   ostruct run template.j2 schema.json -fc data.csv --enable-feature ci-download-hack

   # Force single-pass mode (disable workaround)
   ostruct run template.j2 schema.json -fc data.csv --disable-feature ci-download-hack

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

Two-Argument Syntax
~~~~~~~~~~~~~~~~~~~

.. note::
   **Important**: The basic ``-fs`` flag only supports auto-naming. For custom variable names, use ``--fsa``.

.. code-block:: bash

   # Two-argument syntax is NOT supported by -fs:
   # ostruct run search.j2 schema.json -fs manual docs.pdf    # ❌ This will fail

   # Use --fsa instead for custom variable names:
   # See "Two-Argument Alias Syntax" section below

Two-Argument Alias Syntax
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   --fsa, --file-for-search-alias NAME PATH

   # Examples
   ostruct run search.j2 schema.json --fsa manual docs.pdf
   ostruct run search.j2 schema.json --fsa knowledge kb.txt

Directory File Search Access (Auto-Naming)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   -ds, --dir-for-search DIRECTORY

   # Example
   ostruct run search.j2 schema.json -ds ./documentation  # → documentation variable

Directory File Search Access (Custom Alias)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   --dsa, --dir-for-search-alias NAME DIRECTORY

   # Examples (supports tab completion for paths)
   ostruct run search.j2 schema.json --dsa knowledge_base ./docs
   ostruct run search.j2 schema.json --dsa user_manuals ./manuals

.. tip::
   **When to Use Directory Aliases**: Use ``--dsa`` for search templates that need to work with different documentation sets. Use ``-ds`` when the directory name clearly describes the content type.

File Search Options
~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   --file-search-vector-store-name NAME         # Name for vector store (default: ostruct_search)
   --file-search-cleanup                        # Clean up vector stores after use (default: true)
   --file-search-retry-count COUNT              # Retry attempts for operations (default: 3)
   --file-search-timeout SECONDS               # Timeout for indexing (default: 60.0)

Directory Routing Design Pattern
================================

ostruct provides a **consistent design pattern** for routing both files and directories to tools. Understanding when to use each syntax ensures your templates are robust and reusable.

When to Use Each Syntax
-----------------------

.. list-table:: Directory Routing Decision Guide
   :header-rows: 1
   :widths: 25 35 40

   * - Use Case
     - Syntax Choice
     - Example
   * - **Specific directory structure**
     - Auto-naming (``-dt``, ``-dc``, ``-ds``)
     - ``-dc ./datasets`` → ``datasets`` variable
   * - **Generic/reusable templates**
     - Alias flags (``--dta``, ``--dca``, ``--dsa``)
     - ``--dca code ./src`` → ``code`` variable
   * - **Template knows directory names**
     - Auto-naming
     - Template expects ``{{ config_files }}``
   * - **Template needs stable variables**
     - Alias flags
     - Template uses ``{{ source_code }}`` regardless of actual directory

**Directory Routing Flexibility**

Directory aliases enable generic templates to work with any directory structure:

.. code-block:: bash

   # Auto-naming: Variable names depend on directory structure
   ostruct run template.j2 schema.json -dc ./project_a/src        # → src variable
   ostruct run template.j2 schema.json -dc ./project_b/source     # → source variable

   # Alias naming: Stable variable names regardless of structure
   ostruct run template.j2 schema.json --dca code ./project_a/src     # → code variable
   ostruct run template.j2 schema.json --dca code ./project_b/source  # → code variable

Practical Examples
------------------

**Template Development Workflow**

.. code-block:: bash

   # 1. Start with auto-naming for quick prototyping
   ostruct run code_review.j2 schema.json -dc ./src

   # 2. Move to aliases for production templates
   ostruct run code_review.j2 schema.json --dca source_code ./src

**Multi-Directory Analysis**

.. code-block:: bash

   # Analyze different types of content with stable variable names
   ostruct run security_scan.j2 schema.json \
     --dca source_code ./src \
     --dta config_files ./config \
     --dsa documentation ./docs

**Template Compatibility**

.. code-block:: jinja

   {# Template works with any directory structure #}
   {% for file in source_code %}
   File: {{ file.name }}
   Content: {{ file.content }}
   {% endfor %}

   {% for doc in documentation %}
   Documentation: {{ doc.name }}
   {% endfor %}

**Directory Structure Flexibility**

.. code-block:: bash

   # Same template works with different project structures

   # Project A structure
   ostruct run analysis.j2 schema.json --dca code ./src --dta configs ./settings

   # Project B structure
   ostruct run analysis.j2 schema.json --dca code ./source --dta configs ./config

   # Project C structure
   ostruct run analysis.j2 schema.json --dca code ./app --dta configs ./env

Template Design Patterns
-------------------------

**Generic Templates with Stable Variables**

.. code-block:: bash

   # Use aliases for templates that work with any project structure
   ostruct run analysis.j2 schema.json --dca code ./src

.. code-block:: jinja

   {# Template works regardless of actual directory structure #}
   {% for file in code %}
   File analysis: {{ file.name }}
   {% endfor %}

**Specific Templates with Auto-Naming**

.. code-block:: bash

   # Use auto-naming when template expects specific directory names
   ostruct run project_scanner.j2 schema.json -dc ./src -dc ./tests

.. code-block:: jinja

   {# Template designed for specific project structure #}
   Source files:
   {% for file in src %}
   - {{ file.name }}
   {% endfor %}

   Test files:
   {% for file in tests %}
   - {{ file.name }}
   {% endfor %}

File Routing Best Practices and Advanced Patterns
==================================================

Auto-Naming Convention Details
------------------------------

**Variable Name Generation Rules**

ostruct generates variable names from file paths using these transformation rules:

.. list-table::
   :header-rows: 1
   :widths: 35 35 30

   * - File Path Pattern
     - Generated Variable
     - Applied Rule
   * - ``config.yaml``
     - ``config_yaml``
     - Replace dots with underscores
   * - ``my-file.txt``
     - ``my_file_txt``
     - Replace hyphens with underscores
   * - ``hello.world.json``
     - ``hello_world_json``
     - Replace all non-alphanumeric with underscores
   * - ``123data.csv``
     - ``_123data_csv``
     - Prepend underscore if starts with digit
   * - ``data@file.txt``
     - ``data_file_txt``
     - Replace symbols with underscores
   * - ``My File (1).doc``
     - ``My_File__1__doc``
     - Replace spaces and parentheses with underscores

**Nested Directory Handling**

For files in nested directories, auto-naming uses **only the filename**, not the full path:

.. code-block:: bash

   # Nested path examples
   ostruct run task.j2 schema.json -ft config/database/settings.yaml
   # → Variable: settings_yaml (NOT config_database_settings_yaml)

   ostruct run task.j2 schema.json -ft data/2024/Q1/sales.csv
   # → Variable: sales_csv (NOT data_2024_Q1_sales_csv)

   ostruct run task.j2 schema.json -ft src/main/java/App.java
   # → Variable: App_java (NOT src_main_java_App_java)

**Complex Path Examples**

.. code-block:: bash

   # Special characters and spaces
   ostruct run task.j2 schema.json -ft "user data/file (backup).json"
   # → Variable: file__backup__json

   # Version numbers and dates
   ostruct run task.j2 schema.json -ft data-v2.1_2024-03-15.csv
   # → Variable: data_v2_1_2024_03_15_csv

   # Multiple extensions
   ostruct run task.j2 schema.json -ft archive.tar.gz
   # → Variable: archive_tar_gz

Variable Name Collision Resolution
----------------------------------

**Collision Detection**

ostruct detects and prevents variable name collisions across all file routing types and CLI variables:

.. code-block:: bash

   # This will cause a collision error:
   ostruct run task.j2 schema.json \
     -ft data.csv \
     -fc data.json \
     -V data=test
   # Error: Variable 'data_csv', 'data_json', and 'data' would collide when normalized

**Resolution Strategies**

1. **Use explicit naming** (recommended):

.. code-block:: bash

   # Clear, non-colliding names
   ostruct run task.j2 schema.json \
     -ft template_data data.csv \
     --fca analysis_data data.json \
     -V env_data=test

2. **Rename one of the files**:

.. code-block:: bash

   # Rename files to avoid collisions
   ostruct run task.j2 schema.json \
     -ft config_data.csv \
     -fc analysis_data.json

3. **Use different variable names**:

.. code-block:: bash

   # Use two-argument syntax for control
   ostruct run task.j2 schema.json \
     -ft csv_source data.csv \
     -fc json_source data.json

**Built-in Variable Protection**

These variable names are reserved and cannot be used:

- ``template`` - Reserved for template metadata
- ``schema`` - Reserved for schema information
- ``request`` - Reserved for request context
- ``response`` - Reserved for response data
- ``system`` - Reserved for system information

Legacy Flag Interaction
-----------------------

**Mixing Legacy and New Flags**

You can mix legacy flags (``-f``, ``-d``, ``-p``) with new routing flags, but be aware of variable name conflicts:

.. code-block:: bash

   # Safe mixing - different variable names
   ostruct run task.j2 schema.json \
     -f old_config config.yaml \
     -ft new-settings.json
   # Variables: old_config, new_settings_json

   # Potential conflict - similar names
   ostruct run task.j2 schema.json \
     -f data data.csv \
     -ft data.json
   # Error: Variables 'data' and 'data_json' may be confusing in templates

**Migration Strategy**

When migrating from legacy to new syntax:

.. code-block:: bash

   # Old syntax (still works)
   ostruct run task.j2 schema.json -f config config.yaml -f data data.csv

   # New syntax (recommended)
   ostruct run task.j2 schema.json -ft config.yaml -ft data.csv
   # Variables: config_yaml, data_csv

   # Or with explicit naming
   ostruct run task.j2 schema.json --fta config config.yaml --fta data data.csv

Syntax Selection Best Practices
-------------------------------

**When to Use Auto-Naming (``-ft path``)**

✅ **Good for:**

- Quick prototyping and one-off analyses
- Scripts where variable names don't need to be stable
- Simple file names that generate clear variable names

.. code-block:: bash

   # Clear, obvious variable names
   ostruct run analyze.j2 schema.json -ft config.yaml -fc sales_data.csv
   # Variables: config_yaml, sales_data_csv

❌ **Avoid when:**

- File names are ambiguous (``data.csv``, ``file.txt``)
- Building reusable templates that others will use
- File names contain special characters or are very long

**When to Use Alias Syntax (``--fta name path``)**

✅ **Good for:**

- Reusable templates where variable names need to be stable
- Complex file paths where auto-naming is unclear
- Team environments where consistency matters

.. code-block:: bash

   # Clear, semantic variable names
   ostruct run project_report.j2 schema.json \
     --fta project_config ./config/complex-project-settings.yaml \
     --fca quarterly_data ./data/Q4-2024/sales/regional-breakdown.xlsx

**Additional Benefits of Alias Syntax**

✅ **Also good for:**

- Interactive use where you want tab completion for paths
- Complex directory structures
- When you frequently use the same files with different names

.. code-block:: bash

   # Tab completion helps with complex paths
   ostruct run analysis.j2 schema.json \
     --fta config ./deeply/nested/config/production/settings.yaml \
     --fca dataset ./data/2024/Q4/processed/clean_sales_data.csv

**Hybrid Approach Example**

For maximum clarity, use a combination of syntaxes:

.. code-block:: bash

   # Combine syntaxes based on needs
   ostruct run comprehensive_analysis.j2 schema.json \
     -ft simple_config.yaml \                     # Auto-naming for simple files
     --fta database_config ./config/db/prod.yaml \  # Alias for complex paths
     --fca analysis ./data/clean_dataset.csv \        # Alias for semantic clarity
     -V environment=production                       # CLI variables as needed

Error Prevention and Debugging
------------------------------

**Common Naming Issues and Solutions**

.. code-block:: bash

   # Problem: Ambiguous auto-generated names
   ostruct run task.j2 schema.json -ft file1.txt -ft file2.txt
   # Variables: file1_txt, file2_txt (confusing in templates)

   # Solution: Use semantic names
   ostruct run task.j2 schema.json --fta input_spec file1.txt --fta output_spec file2.txt

**Variable Name Validation**

ostruct validates all variable names to ensure they're valid Python/Jinja2 identifiers:

.. code-block:: bash

   # Invalid variable names (will cause errors)
   ostruct run task.j2 schema.json -ft "123-invalid" file.txt     # Starts with number
   ostruct run task.j2 schema.json -ft "my-var" file.txt          # Contains hyphen
   ostruct run task.j2 schema.json -ft "class" file.txt           # Python keyword

   # Valid alternatives
   ostruct run task.j2 schema.json -ft "_123_valid" file.txt      # Prefixed underscore
   ostruct run task.j2 schema.json -ft "my_var" file.txt          # Underscores OK
   ostruct run task.j2 schema.json -ft "file_class" file.txt      # Avoid keywords

**Debugging Variable Names**

To see what variables will be created before running:

.. code-block:: bash

   # Dry run to check variable names (if implemented)
   ostruct run task.j2 schema.json --dry-run \
     -ft config.yaml \
     -fc data/sales.csv \
     --fsa manual docs.pdf

   # Check template for undefined variables
   ostruct run task.j2 schema.json --validate-only \
     -ft config.yaml

Template Usage Patterns
-----------------------

**Accessing Auto-Named Variables**

.. code-block:: jinja

   {# Auto-named variables from file paths #}
   Configuration: {{ config_yaml.content }}
   Sales data: {{ sales_data_csv.content }}
   Documentation: {{ user_manual_pdf.content }}

**Handling Multiple Files of Same Type**

.. code-block:: bash

   # Use descriptive names to distinguish files
   ostruct run compare.j2 schema.json \
     --fta baseline_config ./configs/baseline.yaml \
     --fta production_config ./configs/production.yaml \
     --fta staging_config ./configs/staging.yaml

.. code-block:: jinja

   {# Clear distinction in templates #}
   Baseline: {{ baseline_config.content }}
   Production: {{ production_config.content }}
   Staging: {{ staging_config.content }}

**Best Template Practices**

.. code-block:: jinja

   {# Document expected variables at top of template #}
   {#
   Expected variables:
   - config_data: Main configuration file
   - sales_info: Sales data for analysis
   - user_manual: Documentation reference
   #}

   {% if not config_data.content %}
     {% error "Configuration file is required" %}
   {% endif %}

       Analysis based on: {{ config_data.name }}
    Data source: {{ sales_info.name }} ({{ sales_info.size }} bytes)

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

Configuration Loading and Precedence
====================================

ostruct uses a hierarchical system for loading configurations. Settings are applied
with the following order of precedence (highest priority first):

1.  **Direct CLI Flags**: Options specified directly on the command line (e.g., ``--model gpt-4o``, ``--timeout 300``) always take the highest precedence, overriding all other sources.

2.  **Environment Variables**: Specific settings can be configured via environment variables. These override values from configuration files but are overridden by CLI flags.
    Key environment variables include:
    - ``OPENAI_API_KEY``: Your OpenAI API key.
    - ``MCP_<NAME>_URL``: URLs for named MCP servers (e.g., ``MCP_STRIPE_URL=https://mcp.stripe.com``).
    - ``OSTRUCT_DISABLE_REGISTRY_UPDATE_CHECKS``: Disable model registry update checks.

    .. tip::
       ostruct automatically loads ``.env`` files from the current directory. Environment variables take precedence over ``.env`` file values.

3.  **Configuration File via ``--config`` Flag**: If you specify a configuration file using the ``--config /path/to/your/ostruct.yaml`` flag, settings from this file override any project-specific or global user configurations.

4.  **Project-Specific Configuration (``./ostruct.yaml``)**: An ``ostruct.yaml`` file located in the current working directory is loaded next. This allows for project-specific default settings.

5.  **Global User Configuration (``~/.ostruct/config.yaml``)**: If no project-specific configuration is found, ostruct looks for a global configuration file at ``~/.ostruct/config.yaml`` (or the equivalent user configuration directory on your OS).

6.  **Internal Pydantic Model Defaults**: The lowest precedence is given to the default values defined within ostruct's internal Pydantic configuration models. These are used if a setting is not found in any of the above sources.

**Example ``ostruct.yaml``:**

.. code-block:: yaml

   # ostruct.yaml
   models:
     default: gpt-4o-mini       # Default model for all runs
     # You can define other model presets here

   tools:
     code_interpreter:
       auto_download: true
       output_directory: "./ci_output" # Default download dir for CI files
     file_search:
       max_results: 15
       default_vector_store_name: "project_kb"

   operation:
     timeout_minutes: 30       # Default operation timeout
     require_approval: "never" # MCP tool approval level

   limits:
     max_cost_per_run: 5.00    # Fail if estimated cost exceeds $5.00
     warn_expensive_operations: true

   # mcp:
   #   my_custom_mcp: "https://example.com/mcp_endpoint"

This system allows for flexible configuration, from global defaults to highly specific per-run overrides.

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

Universal Tool Control
======================

ostruct provides universal flags to enable or disable any built-in tool for the current run, overriding all other configuration methods.

.. note::
   **New in v0.8.3**: Universal tool toggle flags provide a standardized way to control tool enablement across all built-in tools.

Basic Tool Toggle Usage
-----------------------

.. code-block:: bash

   --enable-tool TOOL                           # Enable a specific tool (repeatable)
   --disable-tool TOOL                          # Disable a specific tool (repeatable)

**Supported Tools:**

- ``code-interpreter`` - Python execution and data analysis
- ``web-search`` - Real-time web search capabilities
- ``file-search`` - Vector-based document search
- ``mcp`` - Model Context Protocol server integration

**Examples:**

.. code-block:: bash

   # Enable web search for this run only
   ostruct run research.j2 schema.json --enable-tool web-search

   # Disable code interpreter even if files are provided
   ostruct run task.j2 schema.json -fc data.csv --disable-tool code-interpreter

   # Enable multiple tools
   ostruct run analysis.j2 schema.json --enable-tool web-search --enable-tool file-search

   # Override configuration defaults
   ostruct run task.j2 schema.json --disable-tool web-search --enable-tool code-interpreter

Tool Toggle Precedence
-----------------------

Universal tool toggles take **highest precedence** over all other configuration methods:

1. **Universal toggles** (``--enable-tool``, ``--disable-tool``) - **Highest priority**
2. Legacy tool flags (``--web-search``, ``--no-web-search``) - **Deprecated**
3. Configuration file settings (``ostruct.yaml``)
4. Implicit activation (providing files auto-enables tools)

.. warning::
   **Conflict Detection**: Using both ``--enable-tool`` and ``--disable-tool`` for the same tool will result in an error.

   .. code-block:: bash

      # This will fail with an error
      ostruct run task.j2 schema.json --enable-tool web-search --disable-tool web-search

Legacy Tool Flags (Deprecated)
-------------------------------

.. deprecated:: 0.8.3
   The ``--web-search`` and ``--no-web-search`` flags are deprecated. Use ``--enable-tool web-search`` and ``--disable-tool web-search`` instead. Legacy flags will be removed in v0.9.0.

.. code-block:: bash

   # Deprecated (will show warning)
   --web-search                                 # Use --enable-tool web-search
   --no-web-search                              # Use --disable-tool web-search

Web Search Integration
======================

ostruct integrates with OpenAI's web search tool to provide real-time information and current data in your structured outputs.

.. note::
   **Privacy Notice**: When using ``--enable-tool web-search``, search queries derived from your prompts and template content may be sent to external search services via OpenAI.

Basic Web Search Usage
----------------------

.. code-block:: bash

   --enable-tool web-search                     # Enable web search tool
   --disable-tool web-search                    # Explicitly disable web search

   # Examples
   ostruct run research.j2 schema.json --enable-tool web-search -V topic="latest AI developments"
   ostruct run analysis.j2 schema.json --disable-tool web-search  # Disable if enabled by default

Web Search Configuration
------------------------

.. code-block:: bash

   --user-country COUNTRY                       # Country for geographically tailored results
   --user-city CITY                             # City for location-specific results
   --user-region REGION                         # Region/state for local relevance
   --search-context-size SIZE                   # Content retrieval amount (low|medium|high)

**Examples:**

.. code-block:: bash

   # Location-specific search
   ostruct run news.j2 schema.json --enable-tool web-search \\
     --user-country "US" \\
     --user-city "San Francisco" \\
     --user-region "California"

   # High-detail content retrieval
   ostruct run research.j2 schema.json --enable-tool web-search \\
     --search-context-size high

Web Search in Templates
-----------------------

Use the ``web_search_enabled`` template variable to provide conditional instructions:

.. code-block:: jinja

   {% if web_search_enabled %}
   {# Note to AI: Web search is available. Please use it for current information. #}
   Research the latest developments in {{ topic }} using web search.
   Focus on information from the last 30 days and cite all sources.
   {% else %}
   {# Note to AI: Web search not available. Use training data. #}
   Analyze {{ topic }} based on available training data.
   Note any limitations due to knowledge cutoff.
   {% endif %}

**Best Practices for Web Search Templates:**

1. **Include Source Citations**: Always request sources in your schema
2. **Avoid Inline Citations**: Use dedicated source fields instead of [1], [2] markers
3. **Request Current Information**: Explicitly ask for recent data when needed
4. **Handle Both Modes**: Design templates that work with and without web search

Model Compatibility
-------------------

Web search is supported by these models:

- **GPT-4o series**: All variants support web search
- **GPT-4.1 series**: All variants except nano support web search
- **O-series models**: All reasoning models (o1, o3, o4) support web search

**Unsupported models:**
- GPT-4.1-nano (explicitly unsupported)
- Older GPT models (3.5-turbo, GPT-4 classic)

Security Considerations
-----------------------

.. warning::
   **Search Query Privacy**: Search queries may include content from your prompts and templates.

**Privacy Best Practices:**

- Avoid sensitive information in prompts when using web search
- Use generic terms rather than internal project names
- Review template variables for confidential data
- Test with public information first

**Platform Protections:**

- **Azure OpenAI**: Web search automatically disabled with warning
- **Rate Limits**: Uses your OpenAI API quota
- **Existing API Key**: No separate authentication needed

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

Progress Reporting Levels (v0.8.0+)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

ostruct provides three levels of progress reporting to help you monitor long-running operations.

The default level is ``basic`` for all environments. Use ``--progress-level none`` for scripts and CI/CD pipelines where you want silent operation.

**--progress-level none** (Silent operation)

.. code-block:: bash

   ostruct run analysis.j2 schema.json -fc large_data.csv --progress-level none

Output: No progress indicators, only final results.

**--progress-level basic** (Default)

.. code-block:: bash

   ostruct run analysis.j2 schema.json -fc large_data.csv --progress-level basic

.. code-block:: text

   ✓ Template loaded and validated
   ✓ Files processed (1 file, 2.4MB)
   ⏳ Generating response...
   ✓ Response received (3,421 tokens)
   ✓ Output validated against schema

**--progress-level detailed** (For debugging and monitoring)

.. code-block:: bash

   ostruct run analysis.j2 schema.json -fc large_data.csv --progress-level detailed

.. code-block:: text

   [00:00] 🔄 Initializing ostruct run
   [00:01] 📄 Loading template: analysis.j2
   [00:01] 📋 Loading schema: schema.json
   [00:01] ✓ Template validation passed
   [00:02] 📁 Processing files:
           • large_data.csv → Code Interpreter (2.4MB)
   [00:03] 🔄 Template optimization applied:
           • Moved large_data.csv to appendix (saved 1,247 tokens)
   [00:03] 🤖 Requesting OpenAI API:
           • Model: gpt-4o
           • Input tokens: 2,156
           • Estimated cost: $0.0432
   [00:05] ⏳ Generating response... (streaming)
   [00:12] ✓ Response received:
           • Output tokens: 1,265
           • Total cost: $0.0558
           • Duration: 9.2s
   [00:12] 🔍 Validating output against schema
   [00:12] ✓ Validation successful
   [00:12] 💾 Writing output to file
   [00:12] ✅ Complete (total time: 12.4s)

**Progress with Multi-Tool Operations:**

.. code-block:: bash

   ostruct run comprehensive.j2 schema.json \\
     -fc data.csv \\
     -fs docs.pdf \\
     --progress-level detailed

.. code-block:: text

   [00:00] 🔄 Initializing multi-tool analysis
   [00:01] 📁 Processing files:
           • data.csv → Code Interpreter (1.2MB)
           • docs.pdf → File Search (892KB)
   [00:02] 🔄 Code Interpreter: Uploading data.csv
   [00:03] ✓ Code Interpreter: File uploaded (file_id: abc123)
   [00:03] 🔄 File Search: Processing docs.pdf
   [00:05] ✓ File Search: Vector store created (vs_xyz789)
   [00:05] 🔄 Template optimization applied (3 optimizations)
   [00:06] 🤖 Creating assistant with tools
   [00:07] ⏳ Generating response with tool access...
   [00:15] 🔧 Tool call: Code Interpreter execution
   [00:18] 🔧 Tool call: File Search query
   [00:20] ✓ Response with tool results received
   [00:20] ✅ Complete (total time: 20.1s)

**Error Handling with Progress:**

.. code-block:: text

   [00:05] ❌ Error: Template validation failed
           • Line 15: Unknown variable 'undefined_var'
           • Suggestion: Check variable names match file routing

   [00:08] ⚠️  Warning: Large file upload (5.2MB)
           • File: large_dataset.csv
           • Consider: Breaking into smaller files

   [00:12] ❌ API Error: Rate limit exceeded
           • Retrying in 60 seconds...
           • Use --rate-limit to avoid this

**Examples:**

.. code-block:: bash

   # Detailed debugging for development
   ostruct run task.j2 schema.json -ft data.txt \\
     --verbose \\
     --debug-validation \\
     --progress-level detailed

   # Silent operation for scripts/CI/CD
   ostruct run task.j2 schema.json -ft data.txt \\
     --progress-level none \\
     --output-file results.json

   # Monitor expensive operations
   ostruct run analysis.j2 schema.json -fc large_dataset.csv \\
     --progress-level detailed \\
     --timeout 1800

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
        --fta config config.yaml \\
   --fca data input.csv

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

Troubleshooting File Routing
=============================

Common File Routing Issues
--------------------------

**Variable name conflicts:**

.. code-block:: bash

   # Problem: Conflicting variable names
   ostruct run task.j2 schema.json -ft data.csv -fc data.json
   # Error: Variables 'data_csv' and 'data_json' may be confusing

   # Solution: Use explicit naming
   ostruct run task.j2 schema.json --fta input_data data.csv --fca analysis_data data.json

**Nested path confusion:**

.. code-block:: bash

   # Problem: Complex nested paths
   ostruct run task.j2 schema.json -ft ./very/deep/nested/config.yaml
   # Variable: config_yaml (path information lost)

   # Solution: Use descriptive names for complex paths
   ostruct run task.j2 schema.json --fta deep_config ./very/deep/nested/config.yaml

**Auto-naming issues:**

.. code-block:: bash

   # Problem: Ambiguous auto-generated names
   ostruct run task.j2 schema.json -ft file1.txt -ft file2.txt
   # Variables: file1_txt, file2_txt (hard to distinguish in templates)

   # Solution: Use semantic naming
   ostruct run task.j2 schema.json --fta input_spec file1.txt --fta output_spec file2.txt

**Template variable access errors:**

.. code-block:: jinja

   {# Problem: Forgetting .content #}
   {{ my_file }}  <!-- Shows object description, not content -->

   {# Solution: Always use .content for file content #}
   {{ my_file.content }}  <!-- Actual file content -->

**Legacy flag mixing confusion:**

.. code-block:: bash

   # Problem: Mixing different syntaxes inconsistently
   ostruct run task.j2 schema.json -f old_var data.csv -ft new_data.json
   # Variables: old_var, new_data_json (inconsistent naming)

   # Solution: Choose one consistent approach
   ostruct run task.j2 schema.json --fta old_data data.csv --fta new_data new_data.json

Error Messages and Solutions
----------------------------

**"Variable name collision detected"**

• **Cause**: Multiple files generate the same variable name
• **Solution**: Use explicit naming with two-argument syntax
• **Prevention**: Check auto-generated names for conflicts

**"Invalid variable name"**

• **Cause**: Auto-generated name contains invalid characters
• **Solution**: Use explicit variable names that are valid Python identifiers
• **Prevention**: Avoid files with only special characters in names

**"Guidance message appears in output"**

• **Cause**: Template uses ``{{ variable }}`` instead of ``{{ variable.content }}``
• **Solution**: Always use ``.content`` to access file contents
• **Prevention**: Document expected variables at top of templates

**"Path outside allowed directories"**

• **Cause**: File path violates security restrictions
• **Solution**: Use ``-A`` to add allowed directories or move files to allowed locations
• **Prevention**: Set up proper ``--base-dir`` and allowed directory structure

**"File not found"**

• **Cause**: Path is incorrect or file doesn't exist
• **Solution**: Verify file paths, use absolute paths, or set ``--base-dir``
• **Prevention**: Use tab completion with alias flags (``--fta``, ``--fca``, ``--fsa``)

Directory Routing Issues
------------------------

**"Missing required template variable" with directory routing**

.. code-block:: bash

   # Problem: Auto-naming creates unpredictable variables
   ostruct run template.j2 schema.json -dc ./src
   # Error: Template expects 'code' but gets 'main_py', 'utils_py'

.. code-block:: bash

   # Solution: Use directory aliases for stable variable names
   ostruct run template.j2 schema.json --dca code ./src
   # Creates stable 'code' variable regardless of directory contents

**"Template variables change between runs"**

• **Cause**: Directory contents changed, affecting auto-generated variable names
• **Solution**: Use alias syntax (``--dta``, ``--dca``, ``--dsa``) for consistent variables
• **Prevention**: Use aliases for templates that need to work across different projects

**"Directory routing vs file routing confusion"**

.. code-block:: bash

   # Problem: Mixing individual files and directories
   ostruct run task.j2 schema.json -fc important.py -dc ./src
   # Variables: important_py, main_py, utils_py (inconsistent naming)

.. code-block:: bash

   # Solution: Use consistent alias patterns
   ostruct run task.j2 schema.json --fca key_file important.py --dca source_code ./src
   # Variables: key_file, source_code (predictable and semantic)

**"Directory alias vs auto-naming decision"**

Use **auto-naming** (``-dt``, ``-dc``, ``-ds``) when:

• Template is specific to known directory structure
• One-off analysis where variable names don't matter
• Directory contents are predictable and stable

Use **alias syntax** (``--dta``, ``--dca``, ``--dsa``) when:

• Template is generic and reusable across projects
• Variable names must be stable regardless of directory contents
• Template doesn't know specific filenames in advance
• Creating reusable workflows and CI/CD automation

Feature Flags
=============

ostruct supports experimental feature flags that can be enabled or disabled on a per-run basis:

**Syntax**

.. code-block:: bash

   --enable-feature FEATURE_NAME     # Enable an experimental feature
   --disable-feature FEATURE_NAME    # Disable an experimental feature

**Available Features**

- ``ci-download-hack``: Enable two-pass sentinel mode for reliable Code Interpreter file downloads when using structured output (JSON schemas). This works around an OpenAI API bug where file download annotations are not generated in structured output mode.

**Examples**

.. code-block:: bash

   # Enable reliable Code Interpreter file downloads
   ostruct run analysis.j2 schema.json -fc data.csv --enable-feature ci-download-hack

   # Force single-pass mode (disable workaround)
   ostruct run analysis.j2 schema.json -fc data.csv --disable-feature ci-download-hack

   # Multiple features can be specified
   ostruct run template.j2 schema.json --enable-feature ci-download-hack --enable-feature other-feature

**Configuration Override**

Feature flags override configuration file settings for that specific run. For persistent settings, use the configuration file instead:

.. code-block:: yaml

   # ostruct.yaml
   tools:
     code_interpreter:
       download_strategy: "two_pass_sentinel"  # Equivalent to --enable-feature ci-download-hack

Environment Variables
=====================

ostruct supports several environment variables for configuration:

**Registry Updates**

- ``OSTRUCT_DISABLE_REGISTRY_UPDATE_CHECKS``: Set to "1", "true", or "yes" to disable automatic model registry update notifications

**OpenAI Configuration**

- ``OPENAI_API_KEY``: Your OpenAI API key (required)
- ``OPENAI_API_BASE``: Custom API base URL (optional)
- ``OPENAI_API_VERSION``: API version to use (optional)
- ``OPENAI_API_TYPE``: API type (e.g., "azure") (optional)

**MCP Server Configuration**

- ``MCP_<NAME>_URL``: Custom MCP server URLs (e.g., ``MCP_STRIPE_URL=https://mcp.stripe.com``)

**Examples**

.. code-block:: bash

   # Disable registry update checks
   export OSTRUCT_DISABLE_REGISTRY_UPDATE_CHECKS=1
   ostruct run template.j2 schema.json

   # Set custom OpenAI base URL
   export OPENAI_API_BASE=https://api.example.com/v1
   ostruct run template.j2 schema.json

Getting Help
============

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
