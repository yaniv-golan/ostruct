OST Front-matter Reference Guide
=================================

This reference guide covers the complete YAML front-matter structure for OST files - **Self-executing ostruct prompts**.

What are OST Files?
===================

OST files are **self-executing ostruct prompts** that package everything needed for AI-powered data processing into a single, executable file.

**Regular ostruct workflow:**
- Execute with: ``ostruct run template.j2 schema.json --var name=value --file data.csv``
- Requires separate template file, schema file, and command-line configuration
- User must know the specific variables, file types, and options needed

**OST file workflow:**
- Execute with: ``./my-tool.ost "input text" --format json`` or ``ostruct runx my-tool.ost --help``
- Everything bundled: template + schema + CLI configuration in one file
- Self-documenting with built-in help (``--help`` flag automatically generated)
- Command-line arguments are predefined and validated

**Key Differences:**

.. list-table::
   :header-rows: 1
   :widths: 30 35 35

   * - Aspect
     - Regular ostruct templates
     - OST files (Self-executing prompts)
   * - Execution
     - ``ostruct run template.j2 schema.json``
     - ``./tool.ost`` or ``ostruct runx tool.ost``
   * - Schema
     - Separate ``.json`` file required
     - Embedded in YAML front-matter
   * - Configuration
     - Command-line flags and variables
     - Pre-configured CLI with custom arguments
   * - Help
     - Generic ``ostruct run --help``
     - Custom ``./tool.ost --help`` with tool-specific options
   * - Portability
     - Requires multiple files + knowledge
     - Single file, self-contained
   * - User Experience
     - Power users, developers
     - End users, simplified workflows

.. note::
   This guide is designed for non-Python users who need to understand the OST format. No programming knowledge is required.

OST File Structure
==================

OST files have three main sections:

1. **Shebang Line** - Makes the file executable on Unix systems
2. **YAML Front-matter** - Contains CLI metadata and schema (between ``---`` markers)
3. **Template Content** - Jinja2 template that generates the AI prompt

Basic Structure
---------------

.. code-block:: text

   #!/usr/bin/env -S ostruct runx
   ---
   cli:
     name: my-tool
     description: Description of what this tool does
     # ... CLI configuration

   schema: |
     {
       "type": "object",
       "properties": {
         "result": {"type": "string"}
       }
     }

   defaults:
     # ... default values

   global_args:
     # ... global argument policies
   ---
   # Your Jinja2 template content goes here
   Process this input: {{ input_text }}

Required Sections
=================

cli
---

The ``cli`` section defines the command-line interface for your template.

**Required Fields:**

.. code-block:: yaml

   cli:
     name: my-tool-name
     description: Brief description of what the tool does

**Optional Fields:**

.. code-block:: yaml

   cli:
     name: my-tool-name
     description: Brief description of what the tool does
     positional:
       - name: input_text
         help: The text to process
         default: "Hello World"
     options:
       format:
         names: ["--format", "-f"]
         help: Output format
         default: "json"
         choices: ["json", "yaml", "text"]

schema
------

The ``schema`` section contains the JSON schema that defines the structure of the output.

.. code-block:: yaml

   schema: |
     {
       "type": "object",
       "properties": {
         "result": {
           "type": "string",
           "description": "The processed result"
         },
         "format": {
           "type": "string",
           "description": "The output format used"
         }
       },
       "required": ["result", "format"]
     }

.. tip::
   Use the Schema Generator tool to create schemas automatically:

   .. code-block:: bash

      tools/schema-generator/run.sh -o my_schema.json my_template.j2

CLI Configuration
=================

Positional Arguments
--------------------

Define required or optional positional arguments:

.. code-block:: yaml

   cli:
     positional:
       - name: input_text
         help: The text to analyze
         # Optional: default value
         default: "Sample text"
       - name: output_file
         help: Where to save results
         # No default = required argument

Options (Flags)
---------------

Define command-line options with various behaviors:

Basic String Option
~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   cli:
     options:
       format:
         names: ["--format", "-f"]
         help: Output format
         default: "json"
         choices: ["json", "yaml", "text"]

Boolean Flag
~~~~~~~~~~~~

**Method 1: Using action (recommended)**

.. code-block:: yaml

   cli:
     options:
       verbose:
         names: ["--verbose", "-v"]
         help: Enable verbose output
         action: "store_true"  # Creates a boolean flag

**Method 2: Using type**

.. code-block:: yaml

   cli:
     options:
       debug:
         names: ["--debug"]
         help: Enable debug mode
         type: "bool"
         default: false

Repeatable Option
~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   cli:
     options:
       tags:
         names: ["--tag", "-t"]
         help: Add a tag (can be used multiple times)
         action: "append"  # Allows multiple values

File Input Option
~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   cli:
     options:
       config_file:
         names: ["--config"]
         help: Configuration file
         type: "file"
         target: "prompt"  # Template access only

       data_file:
         names: ["--data"]
         help: Data file for analysis
         type: "file"
         target: "ci"  # Code Interpreter

       docs_file:
         names: ["--docs"]
         help: Documentation file
         type: "file"
         target: "fs"  # File Search

Directory Input Option
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   cli:
     options:
       source_dir:
         names: ["--source"]
         help: Source directory
         type: "directory"
         target: "prompt"

Collection Input Option
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   cli:
     options:
       source_files:
         names: ["--files"]
         help: Collection of files matching a pattern
         type: "collection"
         target: "prompt"

       test_files:
         names: ["--tests"]
         help: Test files for analysis
         type: "collection"
         target: "ci"  # Code Interpreter

**What it does:** Collection type accepts glob patterns and collects multiple files that match the pattern. Unlike directory type which includes all files in a directory, collection type gives you precise control over which files are included.

**Usage Examples:**

.. code-block:: bash

   # Collect all Python files
   my-tool --files "**/*.py"

   # Collect specific test files
   my-tool --tests "test_*.py"

   # Multiple patterns (if action: append is used)
   my-tool --files "*.py" --files "*.js"

Action Parameters
=================

The ``action`` parameter controls how command-line arguments are processed:

store (default)
---------------

Stores a single value:

.. code-block:: yaml

   format:
     names: ["--format"]
     action: "store"  # Default - can be omitted
     help: Output format

store_true
----------

Creates a boolean flag that defaults to ``False``:

.. code-block:: yaml

   verbose:
     names: ["--verbose", "-v"]
     action: "store_true"
     help: Enable verbose output

Usage: ``./my_tool.ost --verbose`` sets ``verbose = True``

store_false
-----------

Creates a boolean flag that defaults to ``True``:

.. code-block:: yaml

   no_color:
     names: ["--no-color"]
     action: "store_false"
     help: Disable colored output

Usage: ``./my_tool.ost --no-color`` sets ``no_color = False``

append
------

Allows multiple values for the same option:

.. code-block:: yaml

   tags:
     names: ["--tag", "-t"]
     action: "append"
     help: Add a tag (repeatable)

Usage: ``./my_tool.ost --tag work --tag urgent`` creates ``tags = ["work", "urgent"]``

count
-----

Counts how many times an option is used:

.. code-block:: yaml

   verbosity:
     names: ["--verbose", "-v"]
     action: "count"
     help: Increase verbosity level

Usage: ``./my_tool.ost -vvv`` sets ``verbosity = 3``

CLI-Level Global Arguments
===========================

The ``global_args`` section can be placed either at the top level or within the ``cli`` section. When placed within the CLI section, it provides tool-specific global argument policies:

.. code-block:: yaml

   cli:
     name: my-tool
     description: My custom tool
     global_args:
       model:
         mode: "fixed"
         value: "gpt-4o"
       --temperature:
         mode: "allowed"
         allowed: [0.1, 0.5, 1.0]
       pass_through_global: false

**CLI-Level vs Top-Level global_args:**

- **CLI-level**: Tool-specific policies that override any top-level settings
- **Top-level**: Default policies for the entire OST file
- **Precedence**: CLI-level settings take priority over top-level settings

**When to Use CLI-Level:**

- When you need different policies per tool in complex OST files
- When the tool requires specific model restrictions
- When you want to prevent certain global flags from being used

**Example: Model Restriction**

.. code-block:: yaml

   cli:
     name: secure-analyzer
     description: Security analysis tool
     global_args:
       model:
         mode: "fixed"
         value: "gpt-4o"  # Force secure model
       pass_through_global: false  # Block unknown flags
     options:
       target:
         names: ["--target"]
         help: File to analyze

This ensures the security tool always uses a specific model and prevents users from changing critical settings.

File Routing Targets
====================

The ``target`` parameter controls where files are sent:

prompt (default)
----------------

Files are available in the template but not uploaded to external services:

.. code-block:: yaml

   config_file:
     names: ["--config"]
     type: "file"
     target: "prompt"  # Template access only

Template usage: ``{{ config_file.content }}``

ci (Code Interpreter)
---------------------

Files are uploaded to OpenAI's Code Interpreter for analysis:

.. code-block:: yaml

   data_file:
     names: ["--data"]
     type: "file"
     target: "ci"  # Code Interpreter analysis

The AI can execute Python code to analyze the file.

fs (File Search)
----------------

Files are uploaded to OpenAI's File Search for semantic search:

.. code-block:: yaml

   docs_file:
     names: ["--docs"]
     type: "file"
     target: "fs"  # File Search

The AI can search through the document content.

ud (User Data)
--------------

Files are sent to vision models for analysis:

.. code-block:: yaml

   pdf_file:
     names: ["--pdf"]
     type: "file"
     target: "ud"  # User-data for vision models

Currently supports PDF files for vision analysis.

auto
----

Automatically routes files based on type detection:

.. code-block:: yaml

   auto_file:
     names: ["--auto"]
     type: "file"
     target: "auto"  # Auto-route by file type

Text files go to ``prompt``, binary files to ``ud``.

Validation and Choices
======================

Restrict Input Values
---------------------

Use ``choices`` to limit allowed values:

.. code-block:: yaml

   format:
     names: ["--format", "-f"]
     choices: ["json", "yaml", "text"]
     default: "json"
     help: Output format

Type Validation
---------------

Specify expected data types:

.. code-block:: yaml

   count:
     names: ["--count", "-c"]
     type: "int"
     default: 10
     help: Number of items to process

   threshold:
     names: ["--threshold"]
     type: "float"
     default: 0.5
     help: Threshold value (0.0-1.0)

Required Arguments
------------------

Use ``required`` to make arguments mandatory:

.. code-block:: yaml

   input_file:
     names: ["--input", "-i"]
     help: Input file to process
     type: "file"
     required: true  # User must provide this argument
     target: "prompt"

   api_key:
     names: ["--api-key"]
     help: API key for authentication
     required: true  # No default value, must be provided

**Note**: Arguments with no ``default`` value are automatically required. Use ``required: true`` to explicitly mark optional arguments as mandatory.

Default Values
==============

The ``defaults`` section provides default values for template variables:

.. code-block:: yaml

   defaults:
     format: "json"
     verbose: false
     max_items: 100
     tags: []  # Empty list for append actions

These defaults are used when users don't provide values.

Global Arguments Policy
=======================

The ``global_args`` section controls how users can interact with ostruct's global flags.

Flag Naming Convention
----------------------

**Important**: Global argument keys must use the exact flag format with dashes:

.. code-block:: yaml

   global_args:
     --model:        # Correct: with dashes
       mode: "allowed"
       allowed: ["gpt-4o", "gpt-4o-mini"]

     model:          # INCORRECT: will cause validation errors
       mode: "allowed"

**Rule**: Use the complete flag name including dashes (e.g., ``--model``, ``--temperature``, ``--enable-tool``) exactly as you would type it on the command line.

Policy Configuration
--------------------

.. code-block:: yaml

   global_args:
     pass_through_global: true  # Allow unknown flags

     --model:
       mode: "allowed"
       allowed: ["gpt-4o", "gpt-4.1", "o1"]
       default: "gpt-4.1"

     --temperature:
       mode: "fixed"
       value: "0.7"

     --enable-tool:
       mode: "blocked"

     --verbose:
       mode: "pass-through"

Policy Modes
------------

allowed
~~~~~~~

Restricts users to specific values:

.. code-block:: yaml

   --model:
     mode: "allowed"
     allowed: ["gpt-4o", "gpt-4.1"]
     default: "gpt-4.1"

fixed
~~~~~

Locks a flag to a specific value:

.. code-block:: yaml

   --temperature:
     mode: "fixed"
     value: "0.7"

Users cannot override this value.

blocked
~~~~~~~

Completely prevents users from using a flag:

.. code-block:: yaml

   --enable-tool:
     mode: "blocked"

Any attempt to use this flag will result in an error.

pass-through
~~~~~~~~~~~~

Allows any value (default behavior):

.. code-block:: yaml

   --verbose:
     mode: "pass-through"

Global Flags
============

The ``global_flags`` section provides a list of default global flags that are always passed to ostruct, unless overridden by user input:

.. code-block:: yaml

   global_flags:
     - "--model"
     - "gpt-4o-mini"
     - "--temperature"
     - "0.7"
     - "--progress"
     - "none"

**Format:** A list of strings alternating between flags and their values.

**Usage Notes:**

- Flags are always passed to the underlying ``ostruct run`` command
- User-provided flags with ``allowed`` or ``pass-through`` policies will override these defaults
- Flags with ``fixed`` policies ignore both user input and global_flags defaults
- Use this for setting consistent tool defaults across template invocations

**Example with Policy Interaction:**

.. code-block:: yaml

   global_flags:
     - "--model"
     - "gpt-4o-mini"
     - "--temperature"
     - "0.5"

   global_args:
     --model:
       mode: "allowed"
       allowed: ["gpt-4o", "gpt-4o-mini"]
       # User can override the global_flags default
     --temperature:
       mode: "fixed"
       value: "0.7"
       # Fixed value ignores global_flags default

Complete Example
================

Here's a complete OST template that demonstrates all features:

.. code-block:: text

   #!/usr/bin/env -S ostruct runx
   ---
   cli:
     name: text-analyzer
     description: Analyzes text content and extracts insights

     positional:
       - name: input_text
         help: Text to analyze
         default: "Sample text for analysis"

     options:
       format:
         names: ["--format", "-f"]
         help: Output format
         choices: ["json", "yaml", "text"]
         default: "json"

       verbose:
         names: ["--verbose", "-v"]
         help: Enable verbose output
         action: "store_true"

       max_length:
         names: ["--max-length"]
         help: Maximum text length to process
         type: "int"
         default: 1000

       tags:
         names: ["--tag", "-t"]
         help: Add analysis tags (repeatable)
         action: "append"

       config_file:
         names: ["--config"]
         help: Configuration file
         type: "file"
         target: "prompt"

       data_file:
         names: ["--data"]
         help: Data file for Code Interpreter analysis
         type: "file"
         target: "ci"

   schema: |
     {
       "type": "object",
       "properties": {
         "analysis": {
           "type": "object",
           "properties": {
             "sentiment": {"type": "string"},
             "key_themes": {
               "type": "array",
               "items": {"type": "string"}
             },
             "word_count": {"type": "integer"},
             "tags": {
               "type": "array",
               "items": {"type": "string"}
             }
           },
           "required": ["sentiment", "key_themes", "word_count"]
         },
         "format": {"type": "string"},
         "verbose": {"type": "boolean"}
       },
       "required": ["analysis", "format", "verbose"]
     }

   defaults:
     format: "json"
     verbose: false
     max_length: 1000
     tags: []

   global_args:
     pass_through_global: true

     --model:
       mode: "allowed"
       allowed: ["gpt-4o", "gpt-4.1", "o1"]
       default: "gpt-4.1"

     --temperature:
       mode: "fixed"
       value: "0.7"

     --enable-tool:
       mode: "blocked"
   ---
   # Text Analysis Template

   Analyze the following text and provide insights:

   **Input Text:** {{ input_text }}
   **Format:** {{ format }}
   **Verbose Mode:** {{ verbose }}
   **Max Length:** {{ max_length }}

   {% if tags %}
   **Analysis Tags:** {{ tags | join(", ") }}
   {% endif %}

   {% if config_file is defined %}
   **Configuration:**
   {{ config_file.content }}
   {% endif %}

   {% if data_file is defined %}
   **Data File Available:** {{ data_file.name }}
   {% endif %}

   {% if verbose %}
   Please provide detailed analysis including:
   - Sentiment analysis with confidence scores
   - Key themes with supporting evidence
   - Word count and readability metrics
   - Detailed explanations for each finding
   {% else %}
   Please provide concise analysis including:
   - Overall sentiment
   - Main themes
   - Word count
   {% endif %}

   Return the analysis in the specified format ({{ format }}).

Usage Examples
==============

Once you've created an OST template, you can use it like a native CLI tool:

Basic Usage
-----------

.. code-block:: bash

   # Simple execution
   ./text-analyzer.ost "This is amazing news!"

   # With options
   ./text-analyzer.ost "Analyze this text" --format yaml --verbose

   # With tags
   ./text-analyzer.ost "Sample text" --tag urgent --tag review

   # With files
   ./text-analyzer.ost "Process this" --config settings.yaml --data report.csv

Help and Debugging
------------------

.. code-block:: bash

   # Get help (automatically generated)
   ./text-analyzer.ost --help

   # Dry run to test without API calls
   ostruct runx text-analyzer.ost "test input" --dry-run

   # Debug template rendering
   ostruct runx text-analyzer.ost "test input" --template-debug vars

Cross-Platform Usage
--------------------

.. code-block:: bash

   # Unix/Linux/macOS: Direct execution
   ./text-analyzer.ost "input text"

   # Windows: Via ostruct command
   ostruct runx text-analyzer.ost "input text"

   # All platforms: Via ostruct command
   ostruct runx text-analyzer.ost "input text"

Best Practices
==============

1. **Use Descriptive Names**

   .. code-block:: yaml

      # Good
      input_file:
        names: ["--input-file"]
        help: Input file to process

      # Avoid
      file:
        names: ["--file"]
        help: File

2. **Provide Clear Help Text**

   .. code-block:: yaml

      format:
        names: ["--format", "-f"]
        help: Output format (json, yaml, or text)
        choices: ["json", "yaml", "text"]

3. **Set Sensible Defaults**

   .. code-block:: yaml

      defaults:
        format: "json"
        verbose: false
        max_items: 100

4. **Use Appropriate File Targets**

   .. code-block:: yaml

      # Configuration files → prompt
      config:
        target: "prompt"

      # Data for analysis → ci
      dataset:
        target: "ci"

      # Documents for search → fs
      documentation:
        target: "fs"

5. **Test with Dry Run**

   Always test your templates before live execution:

   .. code-block:: bash

      ostruct runx my-tool.ost "test input" --dry-run

6. **Handle Optional Variables**

   .. code-block:: jinja

      {% if config_file is defined %}
      Configuration: {{ config_file.content }}
      {% endif %}

Common Patterns
===============

Configuration File Pattern
---------------------------

.. code-block:: yaml

   cli:
     options:
       config:
         names: ["--config", "-c"]
         help: Configuration file
         type: "file"
         target: "prompt"
         default: "config.yaml"

Template usage:

.. code-block:: jinja

   {% if config is defined %}
   Configuration settings:
   {{ config.content }}
   {% endif %}

Data Analysis Pattern
---------------------

.. code-block:: yaml

   cli:
     options:
       data:
         names: ["--data", "-d"]
         help: Data file for analysis
         type: "file"
         target: "ci"

       output_dir:
         names: ["--output-dir", "-o"]
         help: Output directory for results
         default: "./results"

Multi-Tool Pattern
-------------------

.. code-block:: yaml

   cli:
     options:
       analysis_data:
         names: ["--data"]
         type: "file"
         target: "ci"  # Code Interpreter

       documentation:
         names: ["--docs"]
         type: "file"
         target: "fs"  # File Search

       config:
         names: ["--config"]
         type: "file"
         target: "prompt"  # Template only

Troubleshooting
===============

Common Issues
-------------

**Template variables not found:**

.. code-block:: jinja

   # Wrong
   {{ my_file }}

   # Correct
   {{ my_file.content }}

**Boolean flags not working:**

.. code-block:: yaml

   # Wrong
   verbose:
     names: ["--verbose"]
     type: "boolean"

   # Correct
   verbose:
     names: ["--verbose"]
     action: "store_true"

**File not accessible:**

Check the target specification:

.. code-block:: yaml

   # For template access
   config:
     target: "prompt"

   # For Code Interpreter
   data:
     target: "ci"

**Schema validation errors:**

Use the Schema Generator tool:

.. code-block:: bash

   tools/schema-generator/run.sh -o schema.json template.ost

Debug Commands
--------------

.. code-block:: bash

   # Show available variables
   ostruct runx my-tool.ost --template-debug vars

   # Show template expansion
   ostruct runx my-tool.ost --template-debug post-expand

   # Dry run with debug
   ostruct runx my-tool.ost "test" --dry-run --verbose

See Also
========

- :doc:`cli_reference` - Complete CLI documentation
- :doc:`template_guide` - Template creation guide
- :doc:`quickstart` - Getting started tutorial
- :doc:`examples` - Practical examples

Validation Rules Reference
==========================

OST frontmatter is validated according to these rules:

Top-Level Fields
----------------

**Allowed fields:** ``cli``, ``schema``, ``defaults``, ``global_args``, ``global_flags``

Any other top-level fields will result in a validation error.

Required Sections
-----------------

**cli section:**
  - Must be a YAML object
  - Must contain ``name`` (non-empty string)
  - Must contain ``description`` (non-empty string)

**schema section:**
  - Must be a non-empty string containing valid JSON schema

CLI Section Validation
----------------------

**positional** (optional):
  - Must be a list of objects
  - Each positional argument must have a ``name`` field (non-empty string)

**options** (optional):
  - Must be a YAML object or list
  - No specific field validation (handled by Click at runtime)

Global Arguments Validation
---------------------------

**global_args location:** Can be at top-level OR inside CLI section

**pass_through_global field:**
  - Must be a boolean value when present
  - Controls whether unknown global flags are allowed

**Policy objects:** All other fields in global_args must be objects with:
  - Required ``mode`` field with value: ``"fixed"``, ``"pass-through"``, ``"allowed"``, or ``"blocked"``
  - Additional fields depend on mode (e.g., ``value`` for fixed, ``allowed`` list for allowed mode)

**global_flags** (optional):
  - Must be a list of strings
  - Strings cannot be empty (will cause validation error)
  - Format: alternating flag names and values (``["--flag", "value", "--other-flag", "other-value"]``)

Error Messages
--------------

**Common validation errors:**

.. code-block:: text

   # Unknown top-level field
   Unknown top-level field 'version'. Allowed fields are: cli, defaults, global_args, global_flags, schema

   # Missing required CLI fields
   'cli' section is missing required field 'name'
   'cli' section is missing required field 'description'

   # Invalid schema
   'schema' must be a non-empty string

   # Invalid global args
   Global arg 'model' config must be an object
   Global arg 'model' must have 'mode' field
   Global arg 'model' mode must be one of: fixed, pass-through, allowed, blocked

Argument Parsing Rules
======================

- **Order matters**: Place flags/options before positional arguments to avoid ambiguity.
- **Example**: my_tool.ost --format json input.txt (good); my_tool.ost input.txt --format json (may fail if --format is unknown to template).
- **Separator**: Use ``--`` to explicitly end flag parsing if needed (e.g., my_tool.ost --format json -- input.txt).

This matches behavior in many CLI tools for predictable parsing.

Argument Parsing Tips
====================

- **Recommended**: Use `--flag=value` format for flags with values to avoid order issues (e.g., --progress=basic input.txt).
- **Order**: Prefer flags before positionals for best compatibility.
- **Separator**: Use `--` to end flag parsing if needed, but prefer = format for reliability.
