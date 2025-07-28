"""Integration test for attachment processing pipeline."""

import tempfile
from pathlib import Path

import pytest
from ostruct.cli.validators import validate_inputs


@pytest.mark.asyncio
async def test_attachment_integration_end_to_end():
    """Test complete attachment processing integration."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Create test files
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        test_dir = tmp_path / "testdir"
        test_dir.mkdir()
        (test_dir / "inner.txt").write_text("inner content")

        # Create schema file
        schema_file = tmp_path / "schema.json"
        schema_file.write_text(
            '{"type": "object", "properties": {"result": {"type": "string"}}}'
        )

        # Create CLI args with new attachment syntax
        args = {
            "base_dir": str(tmp_path),
            "allowed_dirs": [],
            "allowed_dir_file": None,
            "attaches": [
                {
                    "alias": "data",
                    "path": str(test_file),
                    "targets": ["prompt"],
                    "recursive": False,
                    "pattern": None,
                }
            ],
            "dirs": [
                {
                    "alias": "docs",
                    "path": str(test_dir),
                    "targets": ["file-search"],
                    "recursive": True,
                    "pattern": "*.txt",
                }
            ],
            "task": "Process the data",
            "task_file": None,
            "schema_file": str(schema_file),
            "verbose": False,
            "model": "gpt-4",
            "var": [],
            "json_var": [],
            "files": [],
            "dir": [],
            "patterns": [],
            "recursive": False,
            "system_prompt": None,
            "system_prompt_file": None,
            "ignore_task_sysprompt": False,
        }

        # Run the validation pipeline (this should use the new attachment system)
        result = await validate_inputs(args)

        # Unpack results
        (
            security_manager,
            task_template,
            schema,
            template_context,
            env,
            template_path,
            upload_cache,
        ) = result

        # Verify that the new attachment system was used
        routing_result = args.get("_routing_result")
        assert routing_result is not None

        # Verify routing results
        assert "template" in routing_result.enabled_tools
        assert "file-search" in routing_result.enabled_tools
        assert (
            "code-interpreter" not in routing_result.enabled_tools
        )  # Not used

        # Verify file routing
        assert len(routing_result.validated_files["template"]) == 1
        assert test_file.name in routing_result.validated_files["template"][0]

        assert len(routing_result.validated_files["file-search"]) == 1
        assert (
            test_dir.name in routing_result.validated_files["file-search"][0]
        )

        # Verify that templates and other components are correct
        assert task_template == "Process the data"
        assert schema["type"] == "object"
        assert isinstance(template_context, dict)


@pytest.mark.asyncio
async def test_async_attachment_integration():
    """Test async integration with attachment processing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Create test file
        test_file = tmp_path / "async_test.txt"
        test_file.write_text("async test content")

        # Create schema file
        schema_file = tmp_path / "schema.json"
        schema_file.write_text(
            '{"type": "object", "properties": {"result": {"type": "string"}}}'
        )

        # Create CLI args with new attachment syntax
        args = {
            "base_dir": str(tmp_path),
            "allowed_dirs": [],
            "allowed_dir_file": None,
            "attaches": [
                {
                    "alias": "async_data",
                    "path": str(test_file),
                    "targets": ["prompt", "code-interpreter"],
                    "recursive": False,
                    "pattern": None,
                }
            ],
            "task": "Process async data",
            "task_file": None,
            "schema_file": str(schema_file),
            "verbose": False,
            "model": "gpt-4",
            "var": [],
            "json_var": [],
            "files": [],
            "dir": [],
            "patterns": [],
            "recursive": False,
            "system_prompt": None,
            "system_prompt_file": None,
            "ignore_task_sysprompt": False,
        }

        # Run async validation
        (
            security_manager,
            task_template,
            schema,
            template_context,
            env,
            template_path,
            upload_cache,
        ) = await validate_inputs(args)

        routing_result = args.get("_routing_result")
        assert routing_result is not None

        # Verify multi-target routing works
        assert "template" in routing_result.enabled_tools
        assert "code-interpreter" in routing_result.enabled_tools

        # Same file should appear in both targets
        assert len(routing_result.validated_files["template"]) == 1
        assert len(routing_result.validated_files["code-interpreter"]) == 1


@pytest.mark.asyncio
async def test_fallback_to_legacy_system():
    """Test fallback to legacy system when no new attachments."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Create schema file
        schema_file = tmp_path / "schema.json"
        schema_file.write_text(
            '{"type": "object", "properties": {"result": {"type": "string"}}}'
        )

        # Create CLI args with NO new attachment syntax (should use legacy)
        args = {
            "base_dir": str(tmp_path),
            "allowed_dirs": [],
            "allowed_dir_file": None,
            # No attaches/dirs/collects - should trigger legacy system
            "task": "Legacy test",
            "task_file": None,
            "schema_file": str(schema_file),
            "verbose": False,
            "model": "gpt-4",  # Required field
            "var": [],
            "json_var": [],
            "files": [],
            "dir": [],
            "patterns": [],
            "recursive": False,
            "system_prompt": None,
            "system_prompt_file": None,
            "ignore_task_sysprompt": False,
        }

        # Run validation (should use legacy system)
        await validate_inputs(args)

        # Verify that routing result exists (from legacy system)
        routing_result = args.get("_routing_result")
        assert routing_result is not None

        # Legacy system should have been used (typically has auto_enabled_feedback)
        # This confirms the fallback mechanism works
