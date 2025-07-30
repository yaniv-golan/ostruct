"""Tests for import structure and patching behavior."""

import importlib
import sys
from unittest.mock import patch

# Get the real module object (not the Click Group)
FILES_MODULE = sys.modules["ostruct.cli.commands.files"]


class TestImportStructure:
    """Test that imports work as expected across different environments."""

    def test_files_command_imports(self):
        """Validate that files command imports work correctly."""
        import questionary
        from ostruct.cli.cache_utils import get_default_cache_path
        from ostruct.cli.commands.files import files
        from ostruct.cli.file_search import FileSearchManager
        from ostruct.cli.upload_cache import UploadCache
        from ostruct.cli.upload_manager import SharedUploadManager

        # Ensure the function exists where we expect it
        assert callable(get_default_cache_path)

        # The Click group should NOT have these attributes (we removed the backward-compat hack)
        assert not hasattr(files, "get_default_cache_path")
        assert not hasattr(files, "UploadCache")
        assert not hasattr(files, "FileSearchManager")
        assert not hasattr(files, "SharedUploadManager")
        assert not hasattr(files, "questionary")

        # But the modules should be importable directly
        assert UploadCache is not None
        assert FileSearchManager is not None
        assert SharedUploadManager is not None
        assert questionary is not None

    def test_template_filters_imports(self):
        """Validate that template filters and globals are properly registered."""
        from ostruct.cli.template_env import create_jinja_env

        env, _ = create_jinja_env()

        # dir_of has been fully removed; ensure it is not present
        assert "dir_of" not in env.globals
        assert "type_of" in env.globals, "type_of function should be available"
        assert "debug" in env.globals, "debug function should be available"

        # Test that functions are actually callable
        assert callable(env.globals["type_of"])
        assert callable(env.globals["debug"])

    def test_cli_utils_imports(self):
        """Validate that CLI utils imports work correctly."""
        from ostruct.cli.utils.client_utils import create_openai_client
        from ostruct.cli.utils.error_utils import ErrorCollector
        from ostruct.cli.utils.json_output import JSONOutputHandler
        from ostruct.cli.utils.progress_utils import ProgressHandler

        # Ensure functions/classes exist and are callable/instantiable
        assert callable(create_openai_client)
        assert ErrorCollector is not None
        assert JSONOutputHandler is not None
        assert ProgressHandler is not None

    def test_cli_module_structure(self):
        """Validate that CLI module structure is consistent."""
        import ostruct.cli

        # Test that the main CLI module has expected attributes
        assert hasattr(ostruct.cli, "main")
        assert hasattr(ostruct.cli, "create_cli")
        assert hasattr(ostruct.cli, "ExitCode")

        # Test that utils is properly structured as a package
        from ostruct.cli import utils

        assert hasattr(utils, "ErrorCollector")
        assert hasattr(utils, "JSONOutputHandler")
        assert hasattr(utils, "ProgressHandler")

    def test_patch_targets_exist(self):
        """Validate that patching via FILES_MODULE works correctly."""

        # Ensure the real module has the attributes we need to patch
        assert hasattr(FILES_MODULE, "UploadCache")
        assert hasattr(FILES_MODULE, "get_default_cache_path")
        assert hasattr(FILES_MODULE, "FileSearchManager")
        assert hasattr(FILES_MODULE, "SharedUploadManager")

        # Patch UploadCache via the real module object
        with patch.object(
            FILES_MODULE, "UploadCache", autospec=True
        ) as mock_cache:
            # Import from the real module should get our mock
            assert FILES_MODULE.UploadCache is mock_cache

        # Patch get_default_cache_path via the real module object
        with patch.object(
            FILES_MODULE, "get_default_cache_path", return_value="/tmp/mock"
        ):
            # Function call should return our mocked value
            assert FILES_MODULE.get_default_cache_path() == "/tmp/mock"

    def test_responses_api_imports(self):
        """Validate that responses API test imports work correctly."""
        # Test the import that was failing in CI
        from ostruct.cli.utils.client_utils import create_openai_client

        assert callable(create_openai_client)

        # Test that the CLI module structure is correct
        import ostruct.cli.utils

        assert hasattr(ostruct.cli.utils, "client_utils")


class TestEnvironmentConsistency:
    """Test that the environment behaves consistently across different setups."""

    def test_module_loading_order(self):
        """Ensure importing modules in various orders does not raise and alias remains usable."""
        import sys

        import ostruct.cli.cache_utils

        # Import in one order
        import ostruct.cli.commands.files  # Click group alias
        import ostruct.cli.upload_cache

        # Re-import (reload) in different order
        importlib.reload(ostruct.cli.cache_utils)
        importlib.reload(ostruct.cli.upload_cache)

        # The alias should still be present and patchable
        assert "ostruct.cli.commands.files" in sys.modules
        # The module should expose click utilities whereas the group is available via commands.files
        from ostruct.cli.commands import files as files_group_again

        assert hasattr(
            files_group_again, "command"
        ), "Group should have click Group behaviour"

    def test_virtualenv_independence(self):
        """Test that imports work regardless of virtualenv configuration."""
        # This is a basic smoke test - the real test is running in different environments
        import os
        import sys

        # Basic environment info
        python_path = sys.executable
        virtual_env = os.environ.get("VIRTUAL_ENV")

        # Just ensure basic imports work
        from ostruct.cli.commands.files import files
        from ostruct.cli.template_env import create_jinja_env

        assert files is not None
        assert callable(create_jinja_env)

        # Log environment info for debugging
        print(f"Python: {python_path}")
        print(f"Virtual env: {virtual_env}")
        print(f"Python path length: {len(sys.path)}")
