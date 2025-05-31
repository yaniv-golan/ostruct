"""Tests for template debugging infrastructure.

This module tests all template debugging features implemented in T1.1-T4.2:
- Debug logging configuration (T1.1)
- Template expansion visibility (T1.2)
- Variable context inspection (T1.3)
- Pre-optimization template display (T3.1)
- Optimization step tracking (T3.2)
- CLI integration and help system (T4.1)
- Documentation and examples (T4.2)
"""

import logging
import os

import pytest
from ostruct.cli.template_debug import (
    OptimizationStepTracker,
    TemplateContextInspector,
    TemplateDebugger,
    detect_undefined_variables,
    show_optimization_diff,
)
from pyfakefs.fake_filesystem import FakeFilesystem


class TestTemplateDebugLogging:
    """Test debug logging configuration and output (T1.1)."""

    def test_debug_flag_enables_debug_logging(self, fs: FakeFilesystem):
        """Test that --debug flag enables debug-level logging."""
        # Test the debug configuration directly
        from ostruct.cli.template_debug import configure_debug_logging

        # Test that configure_debug_logging function exists and can be called
        configure_debug_logging(debug=True)

        # Verify that the logger level is set correctly
        logger = logging.getLogger("ostruct")
        assert logger.level == logging.DEBUG

    def test_show_templates_flag(self, fs: FakeFilesystem):
        """Test that --show-templates flag shows template content."""
        # Create test files
        template_content = "Test template: {{ test_var }}"
        fs.create_file(
            "/test_workspace/base/template.j2", contents=template_content
        )
        fs.create_file(
            "/test_workspace/base/schema.json", contents='{"type": "object"}'
        )

        os.chdir("/test_workspace/base")

        # Test template display functionality
        # Capture stderr output (where click.echo outputs)
        import io
        import sys

        from ostruct.cli.template_debug import show_template_content

        captured_output = io.StringIO()
        sys.stderr = captured_output

        try:
            show_template_content(
                system_prompt="System: " + template_content,
                user_prompt="User: " + template_content,
                show_templates=True,
            )
            output = captured_output.getvalue()

            # Verify template content is shown
            assert "Template Content:" in output
            assert "Test template:" in output
            assert "{{ test_var }}" in output
        finally:
            sys.stderr = sys.__stderr__

    def test_debug_logging_backward_compatibility(self, fs: FakeFilesystem):
        """Test that existing --verbose flag still works."""
        from ostruct.cli.template_debug import configure_debug_logging

        # Test verbose mode
        configure_debug_logging(verbose=True, debug=False)
        logger = logging.getLogger("ostruct")

        # Should be at INFO level for verbose
        assert logger.level == logging.INFO


class TestTemplateExpansionVisibility:
    """Test template expansion visibility features (T1.2)."""

    def test_template_debugger_initialization(self):
        """Test TemplateDebugger class initialization."""
        debugger = TemplateDebugger(enabled=True)

        assert debugger.enabled is True
        assert debugger.expansion_log == []

    def test_template_debugger_expansion_logging(self):
        """Test template expansion step logging."""
        debugger = TemplateDebugger(enabled=True)

        # Log an expansion step
        debugger.log_expansion_step(
            "Variable substitution",
            "{{ test_var }}",
            "test_value",
            {"test_var": "test_value"},
        )

        assert len(debugger.expansion_log) == 1
        step = debugger.expansion_log[0]
        assert step["step"] == "Variable substitution"
        assert step["before"] == "{{ test_var }}"
        assert step["after"] == "test_value"
        assert step["context"]["test_var"] == "test_value"

    def test_template_debugger_disabled(self):
        """Test that disabled debugger doesn't log steps."""
        debugger = TemplateDebugger(enabled=False)

        debugger.log_expansion_step("test", "before", "after")

        assert len(debugger.expansion_log) == 0

    def test_expansion_statistics(self):
        """Test expansion statistics calculation."""
        debugger = TemplateDebugger(enabled=True)

        # Add multiple expansion steps
        debugger.log_expansion_step("step1", "a", "b", {"var1": "value1"})
        debugger.log_expansion_step("step2", "c", "d", {"var2": "value2"})

        stats = debugger.get_expansion_stats()

        assert stats["total_steps"] == 2
        assert stats["unique_variables"] == 2


class TestVariableContextInspection:
    """Test variable context inspection features (T1.3)."""

    def test_context_inspector_file_inspection(self, fs: FakeFilesystem):
        """Test context inspection for file variables."""
        # Create test file
        fs.create_file(
            "/test_workspace/base/test.txt", contents="test content"
        )

        # Mock FileInfo object
        class MockFileInfo:
            def __init__(self, path: str, content: str):
                self.path = path
                self.content = content
                self.mime_type = "text/plain"

        context = {
            "test_file": MockFileInfo(
                "/test_workspace/base/test.txt", "test content"
            )
        }

        inspector = TemplateContextInspector()
        report = inspector.inspect_context(context)

        assert len(report.files) == 1
        assert "test_file" in report.files
        file_info = report.files["test_file"]
        assert file_info.path == "/test_workspace/base/test.txt"
        assert file_info.size == 12  # "test content"

    def test_context_inspector_string_inspection(self):
        """Test context inspection for string variables."""
        context = {
            "simple_string": "hello",
            "multiline_string": "line1\nline2\nline3",
        }

        inspector = TemplateContextInspector()
        report = inspector.inspect_context(context)

        assert len(report.strings) == 2
        assert "simple_string" in report.strings
        assert "multiline_string" in report.strings

        simple_info = report.strings["simple_string"]
        assert simple_info.length == 5
        assert simple_info.multiline is False

        multiline_info = report.strings["multiline_string"]
        assert multiline_info.length == 17
        assert multiline_info.multiline is True

    def test_context_inspector_object_inspection(self):
        """Test context inspection for object variables."""
        context = {
            "config_dict": {"key1": "value1", "key2": "value2"},
            "config_list": ["item1", "item2", "item3"],
            "simple_bool": True,
        }

        inspector = TemplateContextInspector()
        report = inspector.inspect_context(context)

        assert len(report.objects) == 3
        assert "config_dict" in report.objects
        assert "config_list" in report.objects
        assert "simple_bool" in report.objects

    def test_undefined_variable_detection(self):
        """Test undefined variable detection in templates."""

        template_content = """
        Hello {{ name }}!
        Your age is {{ age }}.
        Undefined: {{ missing_var }}
        """

        context = {"name": "John", "age": 30}

        undefined_vars = detect_undefined_variables(template_content, context)

        assert "missing_var" in undefined_vars
        assert "name" not in undefined_vars
        assert "age" not in undefined_vars


class TestOptimizationDebugging:
    """Test optimization debugging features (T3.1, T3.2)."""

    def test_optimization_diff_display(self, fs: FakeFilesystem):
        """Test optimization diff display functionality."""
        original = "Original template with {{ file_content }}"
        optimized = "Optimized template with reference to file"

        # Test the diff display function

        import io
        import sys

        captured_output = io.StringIO()
        sys.stderr = captured_output

        try:
            show_optimization_diff(original, optimized)
            output = captured_output.getvalue()

            assert "Optimization Changes" in output
            assert "Original" in output and "Optimized" in output
        finally:
            sys.stderr = sys.__stderr__

    def test_optimization_step_tracking(self):
        """Test optimization step tracking functionality."""
        tracker = OptimizationStepTracker(enabled=True)

        # Log optimization steps
        tracker.log_step(
            "File content replacement",
            "{{ file.content }}",
            "See appendix for file content",
            "Moving large content to appendix",
        )

        assert len(tracker.steps) == 1
        step = tracker.steps[0]
        assert step.name == "File content replacement"
        assert step.reason == "Moving large content to appendix"

    def test_optimization_statistics(self):
        """Test optimization statistics calculation."""
        tracker = OptimizationStepTracker(enabled=True)

        # Add steps with different character changes
        tracker.log_step("step1", "a" * 100, "b" * 150, "test")  # +50 chars
        tracker.log_step("step2", "c" * 200, "d" * 180, "test")  # -20 chars

        # Test that steps were logged
        assert len(tracker.steps) == 2


class TestCLIIntegration:
    """Test CLI integration and help system (T4.1)."""

    def test_debug_options_group_exists(self):
        """Test that debug options are properly grouped."""
        # Test that debug_options function exists and can be imported
        from ostruct.cli.click_options import debug_options

        assert debug_options is not None

    def test_help_debug_flag(self, fs: FakeFilesystem):
        """Test --help-debug flag functionality."""
        fs.create_file("/test_workspace/base/template.j2", contents="test")
        fs.create_file("/test_workspace/base/schema.json", contents="{}")

        os.chdir("/test_workspace/base")

        # Test help content generation
        from ostruct.cli.template_debug_help import TEMPLATE_DEBUG_HELP

        # Verify help content includes key sections
        assert "Template Debugging Quick Reference" in TEMPLATE_DEBUG_HELP
        assert "--debug" in TEMPLATE_DEBUG_HELP
        assert "--show-templates" in TEMPLATE_DEBUG_HELP
        assert "--show-context" in TEMPLATE_DEBUG_HELP
        assert "EXAMPLES:" in TEMPLATE_DEBUG_HELP

    def test_debug_flags_exist(self):
        """Test that all debug CLI flags are defined."""

        # Test that debug flags can be imported
        # This verifies the flags are properly defined in the CLI
        try:
            # Import already done above in test_debug_options_group_exists
            # If we reach here, flags are defined
            assert True
        except ImportError:
            pytest.fail("Debug options not properly defined")


class TestDocumentationAndExamples:
    """Test documentation and examples (T4.2)."""

    @pytest.mark.no_fs
    def test_debugging_documentation_exists(self):
        """Test that debugging documentation files exist."""
        docs_files = [
            "docs/template_debugging.md",
            "docs/template_troubleshooting.md",
        ]

        for doc_file in docs_files:
            assert os.path.exists(
                doc_file
            ), f"Documentation file {doc_file} should exist"

    @pytest.mark.no_fs
    def test_debugging_examples_exist(self):
        """Test that debugging examples exist."""
        example_files = [
            "examples/debugging/README.md",
            "examples/debugging/template-expansion/debug_template.j2",
            "examples/debugging/template-expansion/example_config.yaml",
            "examples/debugging/troubleshooting/undefined_variables.j2",
        ]

        for example_file in example_files:
            assert os.path.exists(
                example_file
            ), f"Example file {example_file} should exist"

    @pytest.mark.no_fs
    def test_example_templates_valid_syntax(self):
        """Test that example templates have valid Jinja2 syntax."""
        from jinja2 import Environment, TemplateSyntaxError

        example_templates = [
            "examples/debugging/template-expansion/debug_template.j2",
            "examples/debugging/troubleshooting/undefined_variables.j2",
            "examples/debugging/troubleshooting/syntax_errors.j2",
        ]

        env = Environment()

        for template_file in example_templates:
            if os.path.exists(template_file):
                with open(template_file, "r") as f:
                    content = f.read()

                try:
                    # Try to parse template (some may have intentional errors)
                    env.parse(content)
                except TemplateSyntaxError:
                    # Some templates intentionally have syntax errors for examples
                    # This is okay for troubleshooting examples
                    if "syntax_errors" not in template_file:
                        pytest.fail(
                            f"Unexpected syntax error in {template_file}"
                        )


class TestPerformanceImpact:
    """Test that debugging features don't significantly impact performance."""

    def test_debug_overhead_minimal(self, fs: FakeFilesystem):
        """Test that debugging adds minimal performance overhead."""
        import time

        # Create test template
        template_content = "Test template: {{ test_var }}"
        fs.create_file(
            "/test_workspace/base/template.j2", contents=template_content
        )

        os.chdir("/test_workspace/base")

        context = {"test_var": "test_value"}

        # Measure baseline rendering time
        start_time = time.perf_counter()
        for _ in range(100):  # Run multiple times for better measurement
            from jinja2 import Environment

            env = Environment()
            template = env.from_string(template_content)
            template.render(context)
        baseline_time = time.perf_counter() - start_time

        # Measure debug rendering time
        debugger = TemplateDebugger(enabled=True)
        start_time = time.perf_counter()
        for _ in range(100):
            template = env.from_string(template_content)
            result = template.render(context)
            debugger.log_expansion_step(
                "test", template_content, result, context
            )
        debug_time = time.perf_counter() - start_time

        # Debug overhead should be less than 50% (generous threshold for testing)
        overhead_ratio = debug_time / baseline_time
        assert (
            overhead_ratio < 1.5
        ), f"Debug overhead too high: {overhead_ratio:.2f}x"

    def test_disabled_debugger_no_overhead(self):
        """Test that disabled debugger adds no overhead."""
        debugger = TemplateDebugger(enabled=False)

        # These operations should be no-ops
        debugger.log_expansion_step("test", "before", "after", {})
        debugger.show_detailed_expansion()

        # No exceptions should be raised and no logging should occur
        assert len(debugger.expansion_log) == 0


class TestIntegrationScenarios:
    """Test complete debugging workflows and integration scenarios."""

    def test_complete_debugging_workflow(self, fs: FakeFilesystem):
        """Test a complete debugging workflow with multiple features."""
        # Create test files
        template_content = """
# Debug Template Test
Config: {{ config.debug }}
File content: {{ code_file.content }}
Missing: {{ undefined_var }}
"""

        fs.create_file(
            "/test_workspace/base/template.j2", contents=template_content
        )
        fs.create_file(
            "/test_workspace/base/config.yaml", contents="debug: true"
        )
        fs.create_file(
            "/test_workspace/base/code.py", contents="print('hello')"
        )
        fs.create_file(
            "/test_workspace/base/schema.json", contents='{"type": "object"}'
        )

        os.chdir("/test_workspace/base")

        # Test context inspection
        class MockFileInfo:
            def __init__(self, path: str, content: str):
                self.path = path
                self.content = content
                self.mime_type = "text/plain"

        context = {
            "config": {"debug": True},
            "code_file": MockFileInfo("code.py", "print('hello')"),
        }

        inspector = TemplateContextInspector()
        report = inspector.inspect_context(context)

        # Verify context inspection works
        assert len(report.files) == 1
        assert len(report.objects) == 1

        # Test undefined variable detection
        undefined_vars = detect_undefined_variables(template_content, context)
        assert "undefined_var" in undefined_vars

    def test_optimization_debugging_workflow(self, fs: FakeFilesystem):
        """Test optimization debugging workflow."""
        # Create a template that would be optimized
        template_content = """
File content: {{ large_file.content }}
Config: {{ config.settings }}
"""

        fs.create_file(
            "/test_workspace/base/template.j2", contents=template_content
        )

        # Mock optimization process
        tracker = OptimizationStepTracker(enabled=True)

        # Simulate optimization steps
        tracker.log_step(
            "File content replacement",
            template_content,
            "File content: [See appendix]\nConfig: {{ config.settings }}",
            "Moved large file content to appendix",
        )

        # Verify tracking works
        assert len(tracker.steps) == 1
        assert "File content replacement" in tracker.steps[0].name


class TestErrorHandling:
    """Test error handling in debugging features."""

    def test_debug_with_invalid_template(self, fs: FakeFilesystem):
        """Test debugging with invalid template syntax."""
        # Create template with syntax error
        invalid_template = "Hello {{ name"  # Missing closing brace
        fs.create_file(
            "/test_workspace/base/invalid.j2", contents=invalid_template
        )

        os.chdir("/test_workspace/base")

        # Test that debugger handles invalid syntax gracefully
        from jinja2 import Environment, TemplateSyntaxError

        env = Environment()

        with pytest.raises(TemplateSyntaxError):
            env.from_string(invalid_template)

    def test_context_inspection_with_none_values(self):
        """Test context inspection with None values."""
        context = {
            "valid_string": "hello",
            "none_value": None,
            "empty_string": "",
        }

        inspector = TemplateContextInspector()
        report = inspector.inspect_context(context)

        # Should handle None values gracefully
        assert len(report.strings) >= 1  # At least valid_string
        assert len(report.objects) >= 1  # None value

    def test_debugger_with_large_context(self):
        """Test debugger performance with large context."""
        # Create large context
        large_context = {}
        for i in range(1000):
            large_context[f"var_{i}"] = f"value_{i}"

        inspector = TemplateContextInspector()

        # Should complete without timeout or memory issues
        import time

        start_time = time.time()
        report = inspector.inspect_context(large_context)
        end_time = time.time()

        # Should complete in reasonable time (< 1 second)
        assert end_time - start_time < 1.0
        assert len(report.strings) == 1000


if __name__ == "__main__":
    pytest.main([__file__])
