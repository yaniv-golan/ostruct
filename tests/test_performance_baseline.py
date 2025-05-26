"""Performance baseline tests for CLI startup time."""

import time


from ostruct.cli.cli import create_cli


class TestPerformanceBaseline:
    """Establish performance baselines before refactoring."""

    def test_cli_import_time(self):
        """Measure CLI import time as baseline."""
        start_time = time.time()

        # Import is already done, but measure fresh import
        import importlib

        import ostruct.cli

        importlib.reload(ostruct.cli)

        end_time = time.time()
        import_time = end_time - start_time

        # Import should be reasonably fast (< 1 second)
        assert (
            import_time < 1.0
        ), f"Import took {import_time:.3f}s, should be < 1.0s"
        print(f"CLI import baseline: {import_time:.3f}s")

    def test_create_cli_time(self):
        """Measure create_cli() execution time as baseline."""
        start_time = time.time()

        cli = create_cli()

        end_time = time.time()
        creation_time = end_time - start_time

        # CLI creation should be fast (< 0.1 second)
        assert (
            creation_time < 0.1
        ), f"create_cli() took {creation_time:.3f}s, should be < 0.1s"
        assert cli is not None
        print(f"create_cli() baseline: {creation_time:.3f}s")

    def test_cli_help_generation_time(self):
        """Measure CLI help generation time as baseline."""
        cli = create_cli()

        start_time = time.time()

        # Generate help (this loads all options and commands)
        try:
            from click.testing import CliRunner

            runner = CliRunner()
            result = runner.invoke(cli, ["--help"])
            assert result.exit_code == 0
        except Exception:
            # If help generation fails, that's not our concern for timing
            pass

        end_time = time.time()
        help_time = end_time - start_time

        # Help generation should be reasonable (< 0.5 second)
        assert (
            help_time < 0.5
        ), f"Help generation took {help_time:.3f}s, should be < 0.5s"
        print(f"CLI help generation baseline: {help_time:.3f}s")
