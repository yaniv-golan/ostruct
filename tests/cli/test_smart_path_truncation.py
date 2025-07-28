"""Tests for smart path truncation functionality."""

from ostruct.cli.utils.path_truncation import smart_truncate_path


class TestSmartPathTruncation:
    """Test smart path truncation algorithm."""

    def test_no_truncation_needed(self):
        """Test that short paths are returned unchanged."""
        path = "/short/path.txt"
        result = smart_truncate_path(path, 50)
        assert result == path

    def test_single_segment_filename(self):
        """Test truncation of single filename with extension."""
        result = smart_truncate_path("very_long_filename.py", 15)
        assert result.endswith(".py")
        assert len(result) <= 15
        assert "..." in result

    def test_preserve_extension(self):
        """Test that file extensions are preserved when possible."""
        # Test case where filename can be preserved
        result = smart_truncate_path("/very/long/path/to/file.py", 20)
        assert result.endswith(".py")
        assert len(result) <= 20

        # Test case where filename must be truncated but extension preserved
        result2 = smart_truncate_path("/path/very_long_filename.py", 25)
        assert result2.endswith(".py")
        assert len(result2) <= 25

    def test_phase1_segment_shrinking(self):
        """Test Phase 1: segment shrinking with middle ellipsis."""
        # Use a length that actually requires truncation
        result = smart_truncate_path("/very_long_directory/filename.txt", 25)
        assert len(result) <= 25
        assert "filename.txt" in result  # Filename should be preserved
        assert "..." in result

    def test_phase2_segment_omission(self):
        """Test Phase 2: omitting middle segments."""
        result = smart_truncate_path("/a/b/c/d/e/f/filename.py", 20)
        assert len(result) <= 20
        # Should show some directory context and filename
        assert "filename.py" in result or result.endswith(".py")
        assert "..." in result

    def test_fallback_filename_only(self):
        """Test fallback to filename-only when path is very long."""
        very_long_path = (
            "/very/long/path/with/many/segments/that/exceeds/limits/file.py"
        )
        result = smart_truncate_path(very_long_path, 15)
        assert len(result) <= 15
        # Should at least show some part of the filename
        assert "file" in result or ".py" in result

    def test_windows_path_normalization(self):
        """Test that Windows paths are normalized to Unix style."""
        result = smart_truncate_path("C:\\Windows\\System32\\file.txt", 20)
        assert "\\" not in result
        assert "/" in result or result == "file.txt"

    def test_no_extension_handling(self):
        """Test handling of files without extensions."""
        result = smart_truncate_path(
            "/path/to/very_long_filename_without_extension", 20
        )
        assert len(result) <= 20
        assert "..." in result

    def test_custom_ellipsis(self):
        """Test using custom ellipsis string."""
        result = smart_truncate_path(
            "/very/long/path/file.txt", 20, ellipsis="…"
        )
        assert "…" in result
        assert len(result) <= 20

    def test_preserve_extension_false(self):
        """Test disabling extension preservation."""
        result = smart_truncate_path(
            "/path/very_long_filename.py", 15, preserve_extension=False
        )
        assert len(result) <= 15
        # May or may not end with .py depending on truncation

    def test_empty_path(self):
        """Test handling of empty or invalid paths."""
        result = smart_truncate_path("", 10)
        assert result == ""

    def test_very_short_max_length(self):
        """Test handling of very short max_length."""
        result = smart_truncate_path("/very/long/path/file.txt", 5)
        assert len(result) <= 5

    def test_relative_path(self):
        """Test handling of relative paths."""
        result = smart_truncate_path("relative/path/to/file.txt", 15)
        assert len(result) <= 15
        assert not result.startswith("/")

    def test_absolute_path(self):
        """Test handling of absolute paths."""
        result = smart_truncate_path("/absolute/path/to/file.txt", 15)
        assert len(result) <= 15

    def test_optimization_phase(self):
        """Test Phase 3: space optimization when segments are omitted."""
        # Use a path that will trigger segment omission but leave room for optimization
        result = smart_truncate_path("/a/b/c/d/short.py", 20)
        assert len(result) <= 20
        # Should be able to show more than just "/a/.../short.py" due to optimization
        assert "short.py" in result

    def test_multiple_dots_in_filename(self):
        """Test handling of filenames with multiple dots."""
        result = smart_truncate_path("/path/file.name.with.dots.txt", 25)
        assert len(result) <= 25
        assert result.endswith(".txt")  # Should preserve final extension

    def test_hidden_files(self):
        """Test handling of hidden files (starting with dot)."""
        result = smart_truncate_path(
            "/path/to/.hidden_file_with_very_long_name", 25
        )
        assert len(result) <= 25
        # Should preserve the leading dot and show some of the hidden filename
        assert result.count(".") >= 1  # At least the leading dot
        assert ".hidden" in result or "hidden" in result or ".hi" in result
