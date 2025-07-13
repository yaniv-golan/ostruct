"""Tests for CLI parameter handling and validation."""

import click
import pytest
from ostruct.cli.params import (
    TARGET_NORMALISE,
    AttachmentSpec,
    AttachParam,
    normalise_targets,
    validate_attachment_alias,
)


class TestTargetNormalization:
    """Test target normalization functionality."""

    def test_single_target_normalization(self):
        """Test normalization of single targets."""
        assert normalise_targets("prompt") == {"prompt"}
        assert normalise_targets("code-interpreter") == {"code-interpreter"}
        assert normalise_targets("file-search") == {"file-search"}

    def test_alias_normalization(self):
        """Test alias expansion."""
        assert normalise_targets("ci") == {"code-interpreter"}
        assert normalise_targets("fs") == {"file-search"}

    def test_multiple_targets(self):
        """Test comma-separated target lists."""
        assert normalise_targets("prompt,ci") == {"prompt", "code-interpreter"}
        assert normalise_targets("ci,fs") == {
            "code-interpreter",
            "file-search",
        }
        assert normalise_targets("prompt,code-interpreter,file-search") == {
            "prompt",
            "code-interpreter",
            "file-search",
        }

    def test_case_insensitive(self):
        """Test case-insensitive handling."""
        assert normalise_targets("PROMPT") == {"prompt"}
        assert normalise_targets("Code-Interpreter") == {"code-interpreter"}
        assert normalise_targets("CI") == {"code-interpreter"}

    def test_whitespace_handling(self):
        """Test whitespace stripping."""
        assert normalise_targets(" prompt ") == {"prompt"}
        assert normalise_targets("prompt, ci") == {
            "prompt",
            "code-interpreter",
        }
        assert normalise_targets(" prompt , ci , fs ") == {
            "prompt",
            "code-interpreter",
            "file-search",
        }

    def test_empty_string_default(self):
        """Test empty string handling."""
        assert normalise_targets("") == {"prompt"}
        assert normalise_targets("   ") == {"prompt"}

    def test_empty_tokens_filtered(self):
        """Test that empty tokens are filtered out."""
        assert normalise_targets("prompt,,ci") == {
            "prompt",
            "code-interpreter",
        }
        assert normalise_targets(",prompt,") == {"prompt"}

    def test_duplicate_targets_deduplicated(self):
        """Test that duplicate targets are deduplicated."""
        assert normalise_targets("prompt,prompt") == {"prompt"}
        assert normalise_targets("ci,code-interpreter") == {"code-interpreter"}

    def test_unknown_target_error(self):
        """Test error handling for unknown targets."""
        with pytest.raises(click.BadParameter) as exc_info:
            normalise_targets("invalid-target")

        error_msg = str(exc_info.value)
        assert "Unknown target(s): invalid-target" in error_msg
        assert "Valid targets:" in error_msg
        assert "prompt" in error_msg

    def test_multiple_unknown_targets_error(self):
        """Test error handling for multiple unknown targets."""
        with pytest.raises(click.BadParameter) as exc_info:
            normalise_targets("invalid1,invalid2")

        error_msg = str(exc_info.value)
        assert "Unknown target(s):" in error_msg
        assert "invalid1" in error_msg
        assert "invalid2" in error_msg

    def test_mixed_valid_invalid_targets(self):
        """Test error when mixing valid and invalid targets."""
        with pytest.raises(click.BadParameter) as exc_info:
            normalise_targets("prompt,invalid")

        error_msg = str(exc_info.value)
        assert "Unknown target(s): invalid" in error_msg


class TestAttachmentAliasValidation:
    """Test attachment alias validation."""

    def test_valid_aliases(self):
        """Test valid alias acceptance."""
        assert validate_attachment_alias("file1") == "file1"
        assert validate_attachment_alias("my-file") == "my-file"
        assert validate_attachment_alias("data_file") == "data_file"
        assert validate_attachment_alias("File123") == "File123"

    def test_empty_alias_error(self):
        """Test error for empty aliases."""
        with pytest.raises(click.BadParameter) as exc_info:
            validate_attachment_alias("")
        assert "cannot be empty" in str(exc_info.value)

        with pytest.raises(click.BadParameter) as exc_info:
            validate_attachment_alias("   ")
        assert "cannot be empty" in str(exc_info.value)

    def test_whitespace_in_alias_error(self):
        """Test error for aliases containing whitespace."""
        with pytest.raises(click.BadParameter) as exc_info:
            validate_attachment_alias("my file")
        assert "cannot contain whitespace" in str(exc_info.value)

        with pytest.raises(click.BadParameter) as exc_info:
            validate_attachment_alias("file\twith\ttab")
        assert "cannot contain whitespace" in str(exc_info.value)

    def test_alias_too_long_error(self):
        """Test error for aliases that are too long."""
        long_alias = "a" * 65  # 65 characters, exceeds 64 limit
        with pytest.raises(click.BadParameter) as exc_info:
            validate_attachment_alias(long_alias)
        assert "too long" in str(exc_info.value)

    def test_alias_whitespace_trimming(self):
        """Test that leading/trailing whitespace is trimmed."""
        assert validate_attachment_alias("  file1  ") == "file1"


class TestAttachmentSpecType:
    """Test AttachmentSpec TypedDict structure."""

    def test_attachment_spec_structure(self):
        """Test that AttachmentSpec has correct structure."""
        # This is more of a static type check, but we can verify the structure
        spec: AttachmentSpec = {
            "alias": "test",
            "path": "/path/to/file",
            "targets": {"prompt"},
            "recursive": False,
            "pattern": None,
        }

        assert spec["alias"] == "test"
        assert spec["path"] == "/path/to/file"
        assert spec["targets"] == {"prompt"}
        assert spec["recursive"] is False
        assert spec["pattern"] is None

    def test_attachment_spec_with_collect_path(self):
        """Test AttachmentSpec with collect-style path."""
        spec: AttachmentSpec = {
            "alias": "collection",
            "path": ("@", "filelist.txt"),
            "targets": {"code-interpreter"},
            "recursive": True,
            "pattern": "*.py",
        }

        assert isinstance(spec["path"], tuple)
        assert spec["path"] == ("@", "filelist.txt")


class TestTargetConstants:
    """Test target normalization constants."""

    def test_target_normalise_completeness(self):
        """Test that all expected targets are in TARGET_NORMALISE."""
        expected_targets = {"prompt", "code-interpreter", "file-search"}

        # Check that all canonical targets map to themselves
        for target in expected_targets:
            assert target in TARGET_NORMALISE
            assert TARGET_NORMALISE[target] == target

        # Check that aliases map to canonical targets
        assert TARGET_NORMALISE["ci"] == "code-interpreter"
        assert TARGET_NORMALISE["fs"] == "file-search"

    def test_no_extra_targets(self):
        """Test that there are no unexpected targets."""
        expected_keys = {
            "prompt",
            "code-interpreter",
            "file-search",
            "ci",
            "fs",
            "user-data",
            "ud",
            "auto",
        }
        assert set(TARGET_NORMALISE.keys()) == expected_keys


class TestAttachParam:
    """Test AttachParam custom Click parameter type."""

    def setup_method(self):
        """Set up test fixtures."""
        self.param_type = AttachParam()
        self.multi_param_type = AttachParam(multi=True)
        # Mock Click objects
        self.mock_param = None
        self.mock_ctx = None

    def test_basic_attachment_space_form(self):
        """Test basic attachment with space form syntax."""
        value = ("data", "./file.txt")
        result = self.param_type.convert(value, self.mock_param, self.mock_ctx)

        expected = {
            "alias": "data",
            "path": "./file.txt",
            "targets": {"prompt"},
            "recursive": False,
            "pattern": None,
        }
        assert result == expected

    def test_attachment_with_targets(self):
        """Test attachment with explicit targets."""
        value = ("ci:analysis", "./data.csv")
        result = self.param_type.convert(value, self.mock_param, self.mock_ctx)

        expected = {
            "alias": "analysis",
            "path": "./data.csv",
            "targets": {"code-interpreter"},
            "recursive": False,
            "pattern": None,
        }
        assert result == expected

    def test_attachment_with_multiple_targets(self):
        """Test attachment with multiple comma-separated targets."""
        value = ("ci,fs:mixed", "./file.txt")
        result = self.param_type.convert(value, self.mock_param, self.mock_ctx)

        expected = {
            "alias": "mixed",
            "path": "./file.txt",
            "targets": {"code-interpreter", "file-search"},
            "recursive": False,
            "pattern": None,
        }
        assert result == expected

    def test_collect_with_filelist(self):
        """Test collect syntax with @filelist."""
        value = ("ci,fs:mixed", "@file-list.txt")
        result = self.multi_param_type.convert(
            value, self.mock_param, self.mock_ctx
        )

        expected = {
            "alias": "mixed",
            "path": ("@", "file-list.txt"),
            "targets": {"code-interpreter", "file-search"},
            "recursive": False,
            "pattern": None,
        }
        assert result == expected

    def test_windows_drive_letter_handling(self):
        """Test Windows drive letter edge case."""
        # Single letter followed by colon should be treated as alias, not target
        value = ("C:", "./path/file.txt")
        result = self.param_type.convert(value, self.mock_param, self.mock_ctx)

        expected = {
            "alias": "C:",
            "path": "./path/file.txt",
            "targets": {"prompt"},  # Default when no target specified
            "recursive": False,
            "pattern": None,
        }
        assert result == expected

    def test_invalid_format_not_tuple(self):
        """Test error when value is not a tuple."""
        with pytest.raises(click.BadParameter) as exc_info:
            self.param_type.convert("invalid", self.mock_param, self.mock_ctx)

        assert "space form syntax" in str(exc_info.value)
        assert "--file data ./file.txt" in str(exc_info.value)

    def test_invalid_format_wrong_tuple_length(self):
        """Test error when tuple has wrong length."""
        with pytest.raises(click.BadParameter) as exc_info:
            self.param_type.convert(
                ("only-one",), self.mock_param, self.mock_ctx
            )

        assert "space form syntax" in str(exc_info.value)

    def test_invalid_target_error(self):
        """Test error handling for invalid targets."""
        with pytest.raises(click.BadParameter) as exc_info:
            self.param_type.convert(
                ("invalid:alias", "./file.txt"), self.mock_param, self.mock_ctx
            )

        assert "Invalid target(s)" in str(exc_info.value)
        assert "Examples:" in str(exc_info.value)

    def test_invalid_alias_error(self):
        """Test error handling for invalid aliases."""
        with pytest.raises(click.BadParameter) as exc_info:
            self.param_type.convert(
                ("prompt:", "./file.txt"), self.mock_param, self.mock_ctx
            )

        assert "cannot be empty" in str(exc_info.value)
        assert "Examples:" in str(exc_info.value)

    def test_empty_filelist_error(self):
        """Test error for empty filelist path."""
        with pytest.raises(click.BadParameter) as exc_info:
            self.multi_param_type.convert(
                ("data", "@"), self.mock_param, self.mock_ctx
            )

        assert "Filelist path cannot be empty" in str(exc_info.value)

    def test_non_multi_param_ignores_filelist(self):
        """Test that non-multi param treats @ as regular path character."""
        value = ("data", "@file.txt")
        result = self.param_type.convert(value, self.mock_param, self.mock_ctx)

        # Should treat @file.txt as regular path, not special syntax
        assert result["path"] == "@file.txt"
        assert not isinstance(result["path"], tuple)

    def test_help_examples_include_collect_for_multi(self):
        """Test that multi=True includes collect examples in error messages."""
        with pytest.raises(click.BadParameter) as exc_info:
            self.multi_param_type.convert(
                "invalid", self.mock_param, self.mock_ctx
            )

        error_msg = str(exc_info.value)
        assert "--collect ci,fs:mixed @file-list.txt" in error_msg

    def test_help_examples_exclude_collect_for_single(self):
        """Test that multi=False excludes collect examples."""
        with pytest.raises(click.BadParameter) as exc_info:
            self.param_type.convert("invalid", self.mock_param, self.mock_ctx)

        error_msg = str(exc_info.value)
        assert "--collect" not in error_msg
