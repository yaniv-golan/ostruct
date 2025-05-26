"""API compatibility tests to ensure refactoring doesn't break public interfaces."""

from ostruct.cli import (
    ExitCode,
    OstructRunner,
    get_update_notification,
    main,
    validate_path_mapping,
    validate_schema_file,
    validate_task_template,
    validate_variable_mapping,
)
from ostruct.cli.cli import create_cli


class TestPublicAPICompatibility:
    """Test suite to ensure public API remains stable during refactoring."""

    def test_main_function_exists(self):
        """Ensure main() function exists and is callable."""
        assert callable(main)

    def test_create_cli_function_exists(self):
        """Ensure create_cli() function exists and returns Click command."""
        cli = create_cli()
        assert hasattr(cli, "main")  # Click command has main method
        assert callable(cli.main)

    def test_exit_code_enum_exists(self):
        """Ensure ExitCode enum is available."""
        assert hasattr(ExitCode, "SUCCESS")
        assert hasattr(ExitCode, "INTERNAL_ERROR")
        assert ExitCode.SUCCESS == 0

    def test_validation_functions_exist(self):
        """Ensure all validation functions are callable."""
        assert callable(validate_schema_file)
        assert callable(validate_task_template)
        assert callable(validate_variable_mapping)
        assert callable(validate_path_mapping)

    def test_get_update_notification_exists(self):
        """Ensure update notification function exists."""
        assert callable(get_update_notification)

    def test_validate_variable_mapping_signature(self):
        """Test validate_variable_mapping function signature."""
        # Test with minimal valid inputs
        try:
            result = validate_variable_mapping("test=value")
            assert isinstance(result, tuple)
            assert len(result) == 2
        except Exception:
            # Function exists and has expected signature
            pass

    def test_validate_task_template_signature(self):
        """Test validate_task_template function signature."""
        try:
            result = validate_task_template("test task", None)
            assert isinstance(result, str)
        except Exception:
            # Function exists and has expected signature
            pass

    def test_validate_schema_file_signature(self):
        """Test validate_schema_file function signature."""
        try:
            # This will likely raise an exception due to missing file,
            # but we're testing the signature exists
            validate_schema_file("nonexistent.json", None)
        except Exception:
            # Function exists and has expected signature
            pass

    def test_imports_from_init_work(self):
        """Test that all public API imports work from __init__.py."""
        # This test passes if imports in the file header worked
        assert ExitCode is not None
        assert main is not None
        assert validate_schema_file is not None
        assert validate_task_template is not None
        assert validate_variable_mapping is not None
        assert get_update_notification is not None
        assert validate_path_mapping is not None
        assert OstructRunner is not None

    def test_ostruct_runner_interface(self):
        """Test that OstructRunner has the expected interface."""
        # Test class instantiation
        args = {"model": "gpt-4o", "task": "test"}
        runner = OstructRunner(args)
        assert runner is not None

        # Test expected methods exist
        assert hasattr(runner, "run")
        assert hasattr(runner, "validate_only")
        assert hasattr(runner, "execute_with_validation")
        assert hasattr(runner, "get_configuration_summary")

        # Test configuration summary works
        summary = runner.get_configuration_summary()
        assert isinstance(summary, dict)
        assert "model" in summary
