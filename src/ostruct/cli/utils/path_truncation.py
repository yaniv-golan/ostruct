"""Path truncation utilities for intelligent file path display.

This module provides smart path truncation that preserves meaningful information
like filenames, extensions, and directory structure while fitting within
specified length constraints.
"""

from typing import List, Optional


def truncate_with_ellipsis(text: str, max_width: int) -> str:
    """Truncate text with ellipsis if too long."""
    if len(text) <= max_width:
        return text
    if max_width <= 3:
        return "..." if max_width == 3 else text[:max_width]
    return text[: max_width - 3] + "..."


def smart_truncate_path(
    path: str,
    max_length: int,
    min_segment_length: Optional[int] = None,
    ellipsis: str = "...",
    preserve_extension: bool = True,
) -> str:
    """Intelligently truncate file paths while preserving meaningful information.

    Uses a 3-phase algorithm:
    1. Shrink individual path segments with middle ellipsis
    2. Omit middle directory segments if still too long
    3. Optimize space usage by expanding segments when possible

    Args:
        path: The file path to truncate
        max_length: Maximum allowed length
        min_segment_length: Minimum length for segments before omission (default: max_length // 3)
        ellipsis: String to use for ellipsis (default: "...")
        preserve_extension: Whether to preserve file extensions (default: True)

    Returns:
        Truncated path that fits within max_length

    Examples:
        >>> smart_truncate_path("/very/long/path/to/filename.py", 20)
        ".../filename.py"
        >>> smart_truncate_path("/a/b/c/very_long_filename.py", 25)
        "/a/.../very...me.py"
    """
    if len(path) <= max_length:
        return path

    if max_length < len(ellipsis):
        return path[:max_length]

    if min_segment_length is None:
        min_segment_length = max(
            3, max_length // 4
        )  # More aggressive: max_length // 4 instead of // 3

    # Normalize path separators and split into segments
    normalized_path = path.replace("\\", "/")
    is_absolute = normalized_path.startswith("/")
    segments = [seg for seg in normalized_path.split("/") if seg]

    if not segments:
        return truncate_with_ellipsis(path, max_length)

    # Handle single segment (just a filename)
    if len(segments) == 1:
        return _shrink_filename(
            segments[0], max_length, ellipsis, preserve_extension
        )

    # Priority Phase: Try to preserve filename fully while shrinking directories
    filename = segments[-1]
    directory_segments = segments[:-1]

    # Calculate space needed for filename and separators
    separators_needed = len(
        segments
    )  # One separator per segment (including leading / if absolute)
    if is_absolute:
        separators_needed += 1  # Extra for leading /

    space_for_dirs = max_length - len(filename) - separators_needed

    # If we can fit the full filename, try shrinking only directories
    if space_for_dirs > 0:
        # Try to fit directories in remaining space
        shrunk_dirs = []
        remaining_space = space_for_dirs

        for dir_segment in directory_segments:
            if len(dir_segment) <= remaining_space:
                shrunk_dirs.append(dir_segment)
                remaining_space -= len(dir_segment)
            else:
                # Need to shrink this directory
                if (
                    remaining_space >= len(ellipsis) + 2
                ):  # Minimum for meaningful shrink
                    shrunk_dirs.append(
                        _shrink_segment(
                            dir_segment, remaining_space, ellipsis, False
                        )
                    )
                    remaining_space = 0
                    break
                else:
                    # Not enough space, go to phase 2
                    break

        # If we processed all directories, we have a solution
        if len(shrunk_dirs) == len(directory_segments):
            result_segments = shrunk_dirs + [filename]
            priority_result = ("/" if is_absolute else "") + "/".join(
                result_segments
            )
            if len(priority_result) <= max_length:
                return priority_result

    # Priority phase failed, fall back to original Phase 1: shrink all segments equally
    shrunk_segments = []

    # Calculate minimum length for filename to preserve extension
    filename = segments[-1]
    if preserve_extension and "." in filename:
        ext_len = len(filename.split(".")[-1]) + 1  # +1 for the dot
        filename_min = max(min_segment_length, ext_len + len(ellipsis))
    else:
        filename_min = min_segment_length

    for i, segment in enumerate(segments):
        is_filename = i == len(segments) - 1
        if is_filename:
            # Use special minimum for filename to guarantee extension space
            shrunk = _shrink_segment(
                segment,
                filename_min,
                ellipsis,
                preserve_extension,
            )
        else:
            shrunk = _shrink_segment(
                segment,
                min_segment_length,
                ellipsis,
                False,
            )
        shrunk_segments.append(shrunk)

    # Reconstruct path
    phase1_result = ("/" if is_absolute else "") + "/".join(shrunk_segments)

    # Light optimization: if we have extra space, expand the filename
    if len(phase1_result) < max_length:
        extra = max_length - len(phase1_result)
        if extra > 0 and preserve_extension and "." in filename:
            new_len = len(shrunk_segments[-1]) + extra
            shrunk_segments[-1] = _shrink_filename(
                filename, new_len, ellipsis, True
            )
            phase1_result = ("/" if is_absolute else "") + "/".join(
                shrunk_segments
            )

    if len(phase1_result) <= max_length:
        return phase1_result

    # Phase 2: Omit middle segments if still too long
    if len(segments) > 2:
        # Keep first segment, last segment, and use ellipsis for middle
        first_seg = _shrink_segment(
            segments[0], min_segment_length, ellipsis, False
        )
        last_seg = _shrink_segment(
            segments[-1], min_segment_length, ellipsis, preserve_extension
        )

        # Calculate space needed for basic structure
        prefix = "/" if is_absolute else ""
        basic_structure = f"{prefix}{first_seg}/{ellipsis}/{last_seg}"

        if len(basic_structure) <= max_length:
            # Phase 3: Optimize space usage
            return _optimize_truncated_path(
                segments,
                basic_structure,
                max_length,
                ellipsis,
                preserve_extension,
                is_absolute,
            )
        else:
            # Basic structure is still too long, try just filename
            filename = segments[-1]
            shrunk_filename = _shrink_filename(
                filename,
                max_length - len(ellipsis) - 1,
                ellipsis,
                preserve_extension,
            )
            return ellipsis + "/" + shrunk_filename

    # Fallback: Just show filename if possible
    filename = segments[-1]
    shrunk_filename = _shrink_filename(
        filename, max_length - len(ellipsis) - 1, ellipsis, preserve_extension
    )
    return ellipsis + "/" + shrunk_filename


def _shrink_segment(
    segment: str,
    min_length: int,
    ellipsis: str,
    preserve_extension: bool = False,
) -> str:
    """Shrink a single path segment using middle ellipsis."""
    if len(segment) <= min_length:
        return segment

    if preserve_extension:
        return _shrink_filename(
            segment, min_length, ellipsis, preserve_extension
        )

    if min_length <= len(ellipsis):
        return segment[:min_length]

    # Use middle ellipsis
    chars_available = min_length - len(ellipsis)
    start_chars = chars_available // 2
    end_chars = chars_available - start_chars

    return (
        segment[:start_chars] + ellipsis + segment[-end_chars:]
        if end_chars > 0
        else segment[:start_chars] + ellipsis
    )


def _shrink_filename(
    filename: str,
    max_length: int,
    ellipsis: str,
    preserve_extension: bool = True,
) -> str:
    """Shrink a filename, optionally preserving the extension."""
    if len(filename) <= max_length:
        return filename

    # Handle hidden files (starting with .)
    if filename.startswith(".") and len(filename) > 1:
        dot = filename[0]
        rest = filename[1:]
        if max_length <= 1:
            return dot
        shrunk_rest = _shrink_filename(
            rest, max_length - 1, ellipsis, preserve_extension
        )
        return dot + shrunk_rest

    if not preserve_extension or "." not in filename:
        return _truncate_with_custom_ellipsis(filename, max_length, ellipsis)

    # Split filename and extension
    name_part, ext_part = filename.rsplit(".", 1)
    ext_with_dot = "." + ext_part

    # NEW: If extension alone is too long, show ellipsis + tail of extension
    if len(ext_with_dot) >= max_length:
        if max_length <= len(ellipsis):
            # Show as much of the extension as possible instead of dropping it
            return ext_with_dot[-max_length:]  # '.js', '.py', etc.
        # Show ellipsis + tail of extension: "...py"
        ext_tail_length = max_length - len(ellipsis)
        if ext_tail_length > 0:
            return ellipsis + ext_with_dot[-ext_tail_length:]
        else:
            return ellipsis

    # Shrink name part while preserving extension
    available_for_name = max_length - len(ext_with_dot)
    if available_for_name <= len(ellipsis):
        # Not enough space for meaningful name, but we can still show extension
        if len(ellipsis) + len(ext_with_dot) <= max_length:
            return ellipsis + ext_with_dot
        else:
            # Fall back to showing ellipsis + extension tail
            ext_tail_length = max_length - len(ellipsis)
            return (
                ellipsis + ext_with_dot[-ext_tail_length:]
                if ext_tail_length > 0
                else ellipsis
            )

    shrunk_name = _truncate_with_custom_ellipsis(
        name_part, available_for_name, ellipsis
    )
    return shrunk_name + ext_with_dot


def _truncate_with_custom_ellipsis(
    text: str, max_width: int, ellipsis: str
) -> str:
    """Truncate text with custom ellipsis if too long."""
    if len(text) <= max_width:
        return text
    if max_width <= len(ellipsis):
        return ellipsis if max_width == len(ellipsis) else text[:max_width]
    return text[: max_width - len(ellipsis)] + ellipsis


def _optimize_truncated_path(
    original_segments: List[str],
    current_result: str,
    max_length: int,
    ellipsis: str,
    preserve_extension: bool,
    is_absolute: bool,
) -> str:
    """Phase 3: Optimize space usage by expanding segments when there's room."""
    available_space = max_length - len(current_result)
    if available_space <= 0:
        return current_result

    # Try to expand the filename first (most important)
    segments = current_result.split("/")
    if len(segments) >= 2:
        filename_idx = -1
        current_filename = segments[filename_idx]
        original_filename = original_segments[-1]

        if len(original_filename) > len(current_filename):
            extra_chars = min(
                available_space, len(original_filename) - len(current_filename)
            )
            if extra_chars > 0:
                expanded_filename = _shrink_filename(
                    original_filename,
                    len(current_filename) + extra_chars,
                    ellipsis,
                    preserve_extension,
                )
                segments[filename_idx] = expanded_filename
                current_result = "/".join(segments)
                available_space = max_length - len(current_result)

    # Try to expand first directory if there's still space
    if available_space > 0 and len(segments) >= 3:
        first_dir_idx = 1 if is_absolute else 0
        current_first = segments[first_dir_idx]
        original_first = original_segments[0]

        if len(original_first) > len(current_first):
            extra_chars = min(
                available_space, len(original_first) - len(current_first)
            )
            if extra_chars > 0:
                expanded_first = _shrink_segment(
                    original_first,
                    len(current_first) + extra_chars,
                    ellipsis,
                    False,
                )
                segments[first_dir_idx] = expanded_first
                current_result = "/".join(segments)

    return current_result
