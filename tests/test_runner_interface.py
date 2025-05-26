"""Test the OstructRunner interface."""


from ostruct.cli import OstructRunner


class TestOstructRunner:
    """Test the OstructRunner class interface."""

    def test_runner_creation(self):
        """Test that OstructRunner can be created with args."""
        args = {
            "model": "gpt-4o",
            "task": "test task",
            "schema": {
                "type": "object",
                "properties": {"result": {"type": "string"}},
            },
            "dry_run": True,
        }

        runner = OstructRunner(args)
        assert runner is not None
        assert runner.args == args

    def test_configuration_summary(self):
        """Test configuration summary generation."""
        args = {
            "model": "gpt-4o",
            "task": "test task",
            "schema": {"type": "object"},
            "dry_run": True,
            "verbose": False,
            "mcp_servers": ["server1", "server2"],
            "code_interpreter_files": ["file1.py"],
            "file_search_dirs": ["./docs"],
        }

        runner = OstructRunner(args)
        summary = runner.get_configuration_summary()

        assert summary["model"] == "gpt-4o"
        assert summary["dry_run"] is True
        assert summary["verbose"] is False
        assert summary["mcp_servers"] == 2
        assert summary["code_interpreter_enabled"] is True
        assert summary["file_search_enabled"] is True
        assert summary["template_source"] == "string"
        assert summary["schema_source"] == "inline"

    def test_configuration_summary_with_files(self):
        """Test configuration summary with file sources."""
        args = {
            "model": "gpt-3.5-turbo",
            "task_file": "task.txt",
            "schema_file": "schema.json",
            "dry_run": False,
        }

        runner = OstructRunner(args)
        summary = runner.get_configuration_summary()

        assert summary["model"] == "gpt-3.5-turbo"
        assert summary["dry_run"] is False
        assert summary["mcp_servers"] == 0
        assert summary["code_interpreter_enabled"] is False
        assert summary["file_search_enabled"] is False
        assert summary["template_source"] == "file"
        assert summary["schema_source"] == "file"

    def test_runner_interface_exists(self):
        """Test that all expected methods exist on OstructRunner."""
        args = {"model": "gpt-4o", "task": "test"}
        runner = OstructRunner(args)

        # Check that all expected async methods exist
        assert hasattr(runner, "run")
        assert callable(runner.run)

        assert hasattr(runner, "validate_only")
        assert callable(runner.validate_only)

        assert hasattr(runner, "execute_with_validation")
        assert callable(runner.execute_with_validation)

        # Check sync method
        assert hasattr(runner, "get_configuration_summary")
        assert callable(runner.get_configuration_summary)

    def test_runner_import_from_public_api(self):
        """Test that OstructRunner can be imported from the public API."""
        # This test passes if the import in the file header worked
        assert OstructRunner is not None

        # Test that it's also available from the main module
        import ostruct.cli

        assert hasattr(ostruct.cli, "OstructRunner")
        assert ostruct.cli.OstructRunner is OstructRunner
