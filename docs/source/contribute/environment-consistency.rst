Environment Consistency Guide
==============================

This guide ensures that local development environments match CI environments to prevent inconsistent behavior.

Quick Verification
------------------

Run the environment verification script:

.. code-block:: bash

   ./scripts/verify-environment.sh

This script will:

- Display all tool versions
- Compare with expected versions from ``pyproject.toml``
- Run health checks on mypy and pre-commit
- Report any inconsistencies

Environment Setup
-----------------

Clean Environment Setup
~~~~~~~~~~~~~~~~~~~~~~~~

If you encounter environment issues, perform a clean setup:

.. code-block:: bash

   # Remove any broken virtual environments
   poetry env remove --all
   rm -rf .venv* rc*_test

   # Configure Poetry (should already be set)
   poetry config virtualenvs.create true
   poetry config virtualenvs.in-project false

   # Fresh install
   poetry install --no-interaction --with dev --extras "docs examples"

Verify Tool Versions
~~~~~~~~~~~~~~~~~~~~~

Check that your local versions match CI expectations:

.. code-block:: bash

   # Check mypy version (should be 1.15.0)
   poetry run mypy --version

   # Check black version (should be 24.8.0)
   poetry run black --version

   # Run the verification script
   ./scripts/verify-environment.sh

Common Issues and Solutions
---------------------------

PyEnv Shim Interference
~~~~~~~~~~~~~~~~~~~~~~~~

**Problem**: ``poetry run mypy`` uses system pyenv shim instead of virtual environment mypy.

**Solution**:

- Ensure Poetry virtual environments are properly configured
- Run ``poetry env info`` to verify the correct virtual environment path
- If needed, remove and recreate the virtual environment

**Detection**: The verification script shows mypy path pointing to ``~/.pyenv/`` instead of the Poetry virtual environment.

Broken Virtual Environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Problem**: Poetry reports "virtual environment seems to be broken"

**Solution**:

.. code-block:: bash

   poetry env remove --all
   poetry install --no-interaction --with dev

Version Mismatches
~~~~~~~~~~~~~~~~~~~

**Problem**: Local tool versions differ from CI

**Solution**:

- Check ``pyproject.toml`` for pinned versions
- Run ``poetry install --sync`` to match exact versions
- Update local environment if needed

CI Environment Verification
----------------------------

The CI workflow includes a "Verify environment versions" step that logs all tool versions. Compare these with your local output from the verification script.

Accessing CI Version Reports
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Go to the GitHub Actions tab
2. Click on the latest CI run
3. Expand the "Verify environment versions" step
4. Compare with your local ``./scripts/verify-environment.sh`` output

Maintaining Consistency
-----------------------

Before Each Release
~~~~~~~~~~~~~~~~~~~

1. Run ``./scripts/verify-environment.sh`` locally
2. Ensure all checks pass
3. Compare with latest CI run output
4. Update documentation if any versions change

When Adding New Tools
~~~~~~~~~~~~~~~~~~~~~

1. Pin exact versions in ``pyproject.toml``
2. Update the verification script to include the new tool
3. Update CI workflow if needed
4. Test both locally and in CI

Troubleshooting
---------------

If you encounter persistent issues:

1. Check for conflicting global tool installations
2. Verify Poetry configuration: ``poetry config --list``
3. Check virtual environment location: ``poetry env info``
4. Compare tool paths: ``poetry run which mypy`` vs ``which mypy``
5. Run the verification script for detailed diagnostics

Integration with Development Workflow
--------------------------------------

Add this to your development routine:

.. code-block:: bash

   # Before starting work
   ./scripts/verify-environment.sh

   # Before committing
   poetry run pre-commit run --all-files

   # Before pushing
   ./scripts/verify-environment.sh

This ensures consistent behavior throughout the development process.
