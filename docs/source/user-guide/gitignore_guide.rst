Gitignore Support Guide
=======================

This guide covers ostruct's built-in gitignore support for intelligent file collection when working with directories and repositories.

Overview
--------

When collecting files from directories recursively, ostruct automatically respects ``.gitignore`` files by default. This prevents sensitive files (like ``.env``, ``node_modules/``, or ``__pycache__/``) from being accidentally included in your prompts or uploaded to AI tools.

**Key Benefits:**

- **Security**: Prevents accidental inclusion of sensitive files (API keys, credentials)
- **Efficiency**: Excludes build artifacts, dependencies, and temporary files
- **Clean prompts**: Focuses on relevant source files only
- **Repository-aware**: Works with any Git repository's existing ignore patterns

Default Behavior
----------------

By default, ostruct:

- ✅ **Respects** ``.gitignore`` files when collecting directory files
- ✅ **Searches** for ``.gitignore`` in the target directory and parent directories
- ✅ **Applies** standard gitignore pattern matching rules
- ✅ **Logs** when files are excluded due to gitignore patterns

.. code-block:: bash

   # This respects .gitignore by default
   ostruct run analyze.j2 schema.json --dir source ./project --recursive

   # Output shows gitignore filtering in action:
   # INFO: Using gitignore file: ./project/.gitignore
   # INFO: Collected 45 files (23 excluded by gitignore)

CLI Options
-----------

Control gitignore behavior with these command-line options:

.. option:: --ignore-gitignore

   Disable gitignore filtering and collect all files.

   .. code-block:: bash

      # Collect ALL files, ignoring .gitignore
      ostruct run analyze.j2 schema.json --dir source ./project --recursive --ignore-gitignore

.. option:: --gitignore-file PATH

   Use a custom gitignore file instead of the default ``.gitignore``.

   .. code-block:: bash

      # Use custom ignore patterns
      ostruct run analyze.j2 schema.json --dir source ./project --recursive --gitignore-file .custom-ignore

Environment Variables
---------------------

Configure default gitignore behavior using environment variables:

.. envvar:: OSTRUCT_IGNORE_GITIGNORE

   Set to ``"true"`` to ignore .gitignore files by default.

   .. code-block:: bash

      export OSTRUCT_IGNORE_GITIGNORE=true
      # Now --ignore-gitignore is the default behavior

.. envvar:: OSTRUCT_GITIGNORE_FILE

   Default path to gitignore file (relative to target directory).

   .. code-block:: bash

      export OSTRUCT_GITIGNORE_FILE=.custom-ignore
      # Now ostruct looks for .custom-ignore instead of .gitignore

Configuration File
------------------

Set gitignore defaults in your ``ostruct.yaml`` configuration:

.. code-block:: yaml

   file_collection:
     ignore_gitignore: false        # Respect .gitignore (default)
     gitignore_file: ".gitignore"   # Default gitignore file name

   # Or disable gitignore by default:
   file_collection:
     ignore_gitignore: true         # Ignore .gitignore files

Common Use Cases
----------------

Repository Analysis
~~~~~~~~~~~~~~~~~~~

When analyzing code repositories, gitignore support keeps your prompts clean:

.. code-block:: bash

   # Analyze only source files, excluding build artifacts
   ostruct run code-review.j2 schema.json --dir ci:codebase ./my-project --recursive

   # Files automatically excluded:
   # - node_modules/
   # - __pycache__/
   # - .env
   # - dist/
   # - *.log

Data Processing Projects
~~~~~~~~~~~~~~~~~~~~~~~~

For data science projects, exclude large datasets and model files:

.. code-block:: bash

   # Include only code and configuration, exclude data files
   ostruct run analyze-ml.j2 schema.json --dir source ./ml-project --recursive

   # With .gitignore containing:
   # data/
   # models/
   # *.pkl
   # *.h5

Custom Ignore Patterns
~~~~~~~~~~~~~~~~~~~~~~

Use project-specific ignore patterns:

.. code-block:: bash

   # Use custom ignore file for specific analysis
   ostruct run security-scan.j2 schema.json \
     --dir source ./project \
     --recursive \
     --gitignore-file .security-ignore

Documentation Projects
~~~~~~~~~~~~~~~~~~~~~~

When processing documentation, exclude generated files:

.. code-block:: bash

   # Process source docs only, exclude build output
   ostruct run doc-analysis.j2 schema.json --dir fs:docs ./docs --recursive

   # With .gitignore containing:
   # _build/
   # .doctrees/
   # *.pdf

Gitignore Pattern Examples
--------------------------

Common patterns that work with ostruct's gitignore support:

**Development Files:**

.. code-block:: text

   # Dependencies
   node_modules/
   __pycache__/
   .venv/

   # Build outputs
   dist/
   build/
   *.o
   *.pyc

   # IDE files
   .vscode/
   .idea/
   *.swp

**Sensitive Files:**

.. code-block:: text

   # Environment and secrets
   .env
   .env.local
   config/secrets.yaml

   # API keys and credentials
   *.key
   *.pem
   credentials.json

**Large Files:**

.. code-block:: text

   # Data and models
   data/
   datasets/
   models/
   *.pkl
   *.h5
   *.model

**Negation Patterns:**

.. code-block:: text

   # Ignore all .txt files except README
   *.txt
   !README.txt

   # Ignore data/ but keep sample data
   data/
   !data/samples/

Troubleshooting
---------------

Files Still Being Included
~~~~~~~~~~~~~~~~~~~~~~~~~~~

If files are being included despite gitignore patterns:

1. **Check pattern syntax**: Ensure patterns follow gitignore rules
2. **Verify file location**: Gitignore must be in target directory or parent
3. **Test patterns**: Use ``git check-ignore`` to test patterns
4. **Enable logging**: Use ``--verbose`` to see gitignore processing

.. code-block:: bash

   # Debug gitignore processing
   ostruct run template.j2 schema.json --dir source ./project --recursive --verbose

   # Check if git would ignore a file
   cd project && git check-ignore path/to/file

Files Being Excluded Unexpectedly
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If important files are being excluded:

1. **Check for broad patterns**: Look for overly inclusive patterns like ``*``
2. **Use negation**: Add ``!important-file.txt`` to include specific files
3. **Disable temporarily**: Use ``--ignore-gitignore`` to see all files
4. **Custom gitignore**: Create a project-specific ignore file

.. code-block:: bash

   # See all files without gitignore filtering
   ostruct run template.j2 schema.json --dir source ./project --recursive --ignore-gitignore

Performance Considerations
~~~~~~~~~~~~~~~~~~~~~~~~~~

For large repositories:

- **Gitignore improves performance** by reducing file count
- **Pattern complexity** affects processing time
- **Deep directory structures** may slow gitignore evaluation

.. code-block:: bash

   # Monitor performance with verbose logging
   ostruct run template.j2 schema.json --dir source ./large-repo --recursive --verbose

Best Practices
--------------

Repository Setup
~~~~~~~~~~~~~~~~

1. **Use standard patterns**: Start with language-specific gitignore templates
2. **Include sensitive files**: Always ignore credentials, API keys, and secrets
3. **Exclude build artifacts**: Don't include generated or compiled files
4. **Document custom patterns**: Comment unusual patterns in .gitignore

Template Design
~~~~~~~~~~~~~~~

1. **Expect filtered files**: Design templates assuming gitignore filtering
2. **Handle missing files gracefully**: Use Jinja2 conditionals for optional files
3. **Provide fallbacks**: Include instructions for when files are missing

.. code-block:: jinja

   {% if config_files %}
   ## Configuration Files
   {% for file in config_files %}
   ### {{ file.name }}
   {{ file.content }}
   {% endfor %}
   {% else %}
   *No configuration files found. Use --ignore-gitignore if needed.*
   {% endif %}

Security Considerations
~~~~~~~~~~~~~~~~~~~~~~~

1. **Never disable for sensitive repos**: Keep gitignore enabled for repositories with secrets
2. **Review custom patterns**: Ensure custom gitignore files don't expose sensitive data
3. **Use project-specific configs**: Different projects may need different ignore patterns
4. **Audit file lists**: Periodically review what files are being collected

.. code-block:: bash

   # Audit file collection without uploading
   ostruct run template.j2 schema.json --dir source ./project --recursive --dry-run

Integration Examples
--------------------

Code Review Workflow
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Review only source code, exclude dependencies and build files
   ostruct run code-review.j2 review-schema.json \
     --dir ci:codebase ./project \
     --recursive \
     --file prompt:guidelines review-guidelines.md

Multi-Tool Analysis
~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Share filtered codebase between Code Interpreter and File Search
   ostruct run comprehensive-analysis.j2 schema.json \
     --dir ci,fs:codebase ./project \
     --recursive \
     --file prompt:requirements analysis-requirements.md

Documentation Processing
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Process documentation with custom ignore patterns
   ostruct run doc-summarizer.j2 schema.json \
     --dir fs:docs ./docs \
     --recursive \
     --gitignore-file .docs-ignore \
     --file prompt:style style-guide.md

See Also
--------

- :doc:`cli_reference`: Complete CLI option reference
- :doc:`template_guide`: Template file access patterns
- :doc:`tool_integration`: Multi-tool file routing
- :doc:`advanced_patterns`: Advanced file collection patterns
