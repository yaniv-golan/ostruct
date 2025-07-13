Examples Standard
=================

This document defines the standard interface for ostruct examples. All examples in the ``examples/`` directory must follow this specification to ensure consistency, testability, and maintainability.

Overview
--------

Examples provide a **standardized testing interface** via ``make`` while preserving **flexible implementation** underneath. This separation allows:

- **Consistent CI/testing**: All examples support the same make targets
- **Implementation flexibility**: Examples can use any internal structure
- **Easy maintenance**: Clear separation between interface and implementation

Example Discovery
-----------------

Examples are discovered by finding directories containing a ``Makefile`` within the ``examples/`` tree:

- **Direct examples**: ``examples/category/example-name/Makefile``
- **Nested examples**: ``examples/category/group/example-name/Makefile``
- **Multi-level nesting**: Any depth is supported

Each directory with a ``Makefile`` is considered an independent example.

Required Interface
------------------

Every example **MUST** provide a ``Makefile`` with these targets:

Core Targets
~~~~~~~~~~~~

.. code-block:: makefile

   # Test with dry-run (no API calls) - fast validation
   test-dry:
    # Validate templates, schemas, and configuration
    # Should complete in <5 seconds

   # Test with minimal live API call - verify connectivity
   test-live:
    # Single API call with small input
    # Should complete in <30 seconds

   # Run the example with default parameters
   run:
    # Execute the example with sensible defaults
    # Should demonstrate the example's main functionality

   # Clean up generated files
   clean:
    # Remove output files, downloads, temporary data
    # Should restore directory to clean state

   # Show available targets and usage
   help:
    # Display available make targets and example usage

Implementation Requirements
~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. **Self-contained**: Each target should work without external setup
2. **Idempotent**: Running targets multiple times should be safe
3. **Documented**: ``make help`` should explain what the example does
4. **Robust**: Handle missing dependencies gracefully with clear error messages

Internal Structure Flexibility
------------------------------

Examples can use any internal structure that works for their use case:

Simple Examples
~~~~~~~~~~~~~~~

.. code-block:: text

   examples/tools/file-search-basics/
   ├── Makefile
   ├── run.sh
   ├── templates/main.j2
   └── schemas/main.json

Complex Examples
~~~~~~~~~~~~~~~~

.. code-block:: text

   examples/analysis/argument-aif/
   ├── Makefile
   ├── pipeline.sh
   ├── templates/
   │   ├── 01_outline.j2
   │   ├── 02_extract.j2
   │   └── 03_synthesize.j2
   ├── schemas/
   │   ├── outline.json
   │   └── extraction.json
   └── scripts/
       └── post_process.py

Multi-Pass Examples
~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   examples/analysis/pitch-distiller/
   ├── Makefile
   ├── run.sh
   ├── templates/
   │   ├── pass1_core.j2
   │   └── pass2_taxonomy.j2
   └── schemas/
       ├── pass1_core.json
       └── pass2_taxonomy.json

Testing Integration
-------------------

The test suite validates examples by:

1. **Discovery**: Finding all ``Makefile`` files in the examples tree
2. **Validation**: Ensuring required targets exist and are executable
3. **Dry-run testing**: Running ``make test-dry`` for fast validation
4. **Live testing**: Running ``make test-live`` for API connectivity (optional)

Migration Guide
---------------

For New Examples
~~~~~~~~~~~~~~~~

1. Create your example with whatever structure works best
2. Add a ``Makefile`` with the required targets
3. Ensure ``make test-dry`` validates your templates/schemas
4. Ensure ``make test-live`` does a minimal API test

For Existing Examples
~~~~~~~~~~~~~~~~~~~~~

1. Add a ``Makefile`` to your example directory
2. Map your existing scripts to the standard targets:

   .. code-block:: makefile

      test-dry:
       ./run.sh --dry-run

      test-live:
       ./run.sh --test-mode

      run:
       ./run.sh

      clean:
       rm -rf output/ downloads/ *.json

Best Practices
--------------

1. **Keep** ``test-dry`` **fast**: No network calls, minimal computation
2. **Make** ``test-live`` **minimal**: Single API call with small input
3. **Document dependencies**: Use ``make help`` to list requirements
4. **Handle errors gracefully**: Provide clear error messages for missing tools
5. **Use relative paths**: Keep examples portable across environments

Example Makefile Template
--------------------------

.. code-block:: makefile

   # Example: Basic Analysis Tool
   # Analyzes text files using ostruct templates

   .PHONY: test-dry test-live run clean help

   # Default target
   help:
    @echo "Available targets:"
    @echo "  test-dry  - Validate templates and schemas (no API calls)"
    @echo "  test-live - Run minimal live test with API"
    @echo "  run       - Execute analysis with default input"
    @echo "  clean     - Remove generated files"
    @echo "  help      - Show this help message"

   test-dry:
    @echo "Validating templates and schemas..."
    ostruct run templates/main.j2 schemas/main.json --dry-run \
     -V "input_text=Sample text for validation"

   test-live:
    @echo "Running minimal live test..."
    ostruct run templates/main.j2 schemas/main.json \
     -V "input_text=Test" \
     --output-file /tmp/test_output.json
    @rm -f /tmp/test_output.json

   run:
    @echo "Running analysis with default input..."
    ./run.sh data/sample.txt

   clean:
    @echo "Cleaning up generated files..."
    rm -rf output/ downloads/ *.json temp/

This standard provides consistency while preserving the flexibility that makes each example unique and useful.
