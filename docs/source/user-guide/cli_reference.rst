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

   # Show quick reference with new attachment syntax
   ostruct quick-ref

   # Get JSON help for programmatic consumption
   ostruct run --help-json

   # Update model registry
   ostruct update-registry

New Attachment System (v0.9.0)
===============================

.. important::
   **Breaking Change in v0.9.0**: The file routing system has been completely replaced with an explicit target/alias attachment system. This provides better control, security, and clarity about how files are processed.

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

.. option:: -A, --file [TARGETS:]ALIAS PATH

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
-------------------------

Files attached with ``prompt`` target (default) are available in templates but not uploaded to external services.

.. code-block:: bash

   # Template-only access (default behavior)
   ostruct run task.j2 schema.json --file config config.yaml
   ostruct run task.j2 schema.json --file prompt:data input.json

   # Directory attachment for template access
   ostruct run task.j2 schema.json --dir settings ./config

**Template Access**: Use ``{{ alias.content }}`` or ``{{ alias }}`` to access file content in templates.

Code Interpreter Examples
--------------------------

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
====================

Text File Processing
-------------------

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
-----------------------------

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

Debug and Help Options
----------------------

.. option:: --debug

   Enable debug-level logging.

.. option:: --verbose

   Enable verbose output.



.. option:: --show-templates

   Show expanded templates before API calls.

.. option:: --show-context

   Show template variable context summary.

Migration from v0.8.x
======================

.. important::
   **Breaking Changes in v0.9.0**: All file routing options have changed. See the migration guide below.

Model Name Validation (v0.8.0+)
--------------------------------

Starting in v0.8.0, ostruct validates model names against the OpenAI model registry.

**What Changed:**

- Invalid model names are now rejected immediately
- Shell completion shows available models
- Help text automatically lists current models

**If You Get Model Validation Errors:**

1. Check available models: ``ostruct list-models``
2. Update your scripts to use valid model names
3. Update your registry if needed: ``ostruct update-registry``

**Common Issues:**

- **Typos**: ``gpt4o`` → ``gpt-4o``
- **Old names**: ``gpt-4-turbo`` → ``gpt-4o``
- **Custom names**: Use ``ostruct list-models`` to see what's available

Quick Migration Reference
--------------------------

.. list-table:: Legacy → New Syntax Migration
   :widths: 50 50
   :header-rows: 1

   * - Legacy (v0.8.x)
     - New (v0.9.0)
   * - ``--file data file.txt``
     - ``--file data file.txt``
   * - ``--dir docs ./docs``
     - ``--dir docs ./docs``
   * - ``--file ci:data data.csv``
     - ``--file ci:data data.csv``
   * - ``--file fs:docs manual.pdf``
     - ``--file fs:docs manual.pdf``
   * - ``--file-for code-interpreter data.csv``
     - ``--file ci:data data.csv``

.. note::
   **Automatic Migration**: Use the migration scripts provided in the documentation for bulk updates to existing scripts.

See Also
========

* :doc:`quickstart` - Getting started guide
* :doc:`examples` - Practical examples and use cases
* :doc:`template_authoring` - Template authoring guide
* :doc:`template_quick_reference` - Template syntax reference
