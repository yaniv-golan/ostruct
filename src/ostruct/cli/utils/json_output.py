"""Shared JSON output formatting utilities for CLI commands."""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Union


class JSONOutputHandler:
    """Centralized JSON output formatting for CLI commands.

    This class provides standardized JSON output patterns across CLI commands,
    ensuring consistent structure, metadata inclusion, and formatting.

    Usage:
        handler = JSONOutputHandler()

        # Format results with metadata
        result = handler.format_results(
            success_items=uploaded_files,
            cached_items=cached_files,
            errors=error_list,
            metadata={"operation": "upload", "total_files": 10}
        )

        # Output JSON
        if handler.should_output_json(output_json_flag):
            click.echo(handler.to_json(result))
    """

    def __init__(
        self, include_metadata: bool = True, indent: Optional[int] = None
    ) -> None:
        """Initialize the JSON output handler.

        Args:
            include_metadata: Whether to include metadata in output
            indent: JSON indentation (None for compact output)
        """
        self.include_metadata = include_metadata
        self.indent = indent

    def format_results(
        self,
        success_items: Optional[List[Any]] = None,
        cached_items: Optional[List[Any]] = None,
        errors: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        operation: str = "operation",
        summary: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Format results into a standardized JSON structure.

        Args:
            success_items: List of successfully processed items
            cached_items: List of cached/skipped items (optional)
            errors: List of error messages
            metadata: Additional metadata to include
            operation: Name of the operation for metadata
            summary: Optional pre-built summary (if provided, used instead of auto-generated)

        Returns:
            Dictionary with standardized JSON structure
        """
        result: Dict[str, Any] = {}

        # Main data sections
        if success_items is not None:
            if cached_items is not None:
                # Separate success and cached items
                result["uploaded"] = success_items
                result["cached"] = cached_items
            else:
                # Single success category
                result["results"] = success_items

        # Errors section
        result["errors"] = errors or []

        # Summary section
        if summary is not None:
            # Use provided summary
            result["summary"] = summary
        else:
            # Auto-generate summary
            success_count = len(success_items) if success_items else 0
            cached_count = len(cached_items) if cached_items else 0
            error_count = len(errors) if errors else 0
            total_count = success_count + cached_count + error_count

            auto_summary = {"total": total_count}

            if cached_items is not None:
                # Upload-style summary
                auto_summary["uploaded"] = success_count
                auto_summary["cached"] = cached_count
                auto_summary["errors"] = error_count
            else:
                # Generic processing summary
                auto_summary["processed"] = success_count
                auto_summary["errors"] = error_count

            result["summary"] = auto_summary

        # Metadata section
        if self.include_metadata and metadata:
            metadata_dict = {
                "operation": operation,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
            metadata_dict.update(metadata)
            result["metadata"] = metadata_dict

        return result

    def format_summary(
        self,
        *,
        total: int,
        processed: Optional[int] = None,
        uploaded: Optional[int] = None,
        cached: Optional[int] = None,
        errors: int = 0,
        **extra: Any,
    ) -> Dict[str, Any]:
        """Format a standardized summary dictionary.

        Args:
            total: Total items processed
            processed: Successfully processed items (for generic operations)
            uploaded: Successfully uploaded items (for upload operations)
            cached: Cached items (for upload operations)
            errors: Number of errors
            **extra: Additional fields to include

        Returns:
            Formatted summary dict
        """
        summary: Dict[str, Any] = {"total": total, "errors": errors}

        if processed is not None:
            summary["processed"] = processed
        if uploaded is not None:
            summary["uploaded"] = uploaded
        if cached is not None:
            summary["cached"] = cached

        summary.update(extra)
        return summary

    def format_error_response(
        self, error_message: str, error_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """Format an error response.

        Args:
            error_message: The error message
            error_code: Optional error code

        Returns:
            Dictionary with error structure
        """
        result: Dict[str, Any] = {"error": error_message}

        if error_code:
            result["error_code"] = error_code

        if self.include_metadata:
            result["metadata"] = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "success": False,
            }

        return result

    def format_dry_run_response(
        self, preview_data: Dict[str, Any], operation: str = "dry_run"
    ) -> Dict[str, Any]:
        """Format a dry-run response.

        Args:
            preview_data: Dictionary with preview information
            operation: Name of the operation

        Returns:
            Dictionary with dry-run structure
        """
        result: Dict[str, Any] = {"dry_run": True}
        result.update(preview_data)

        if self.include_metadata:
            result["metadata"] = {
                "operation": operation,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "mode": "dry_run",
            }

        return result

    def to_json(self, data: Union[Dict[str, Any], List[Any]]) -> str:
        """Convert data to JSON string.

        Args:
            data: Dictionary or list to convert to JSON

        Returns:
            JSON string
        """
        return json.dumps(data, indent=self.indent, ensure_ascii=False)

    @staticmethod
    def should_output_json(output_json: bool) -> bool:
        """Check if JSON output should be used.

        This is a utility method that can be used to determine if JSON output
        mode is enabled and other features (like progress bars, interactive prompts)
        should be disabled.

        Args:
            output_json: The JSON output flag

        Returns:
            True if JSON output should be used
        """
        return output_json

    @staticmethod
    def is_json_mode_compatible(
        output_json: bool, interactive: bool = False, progress: str = "basic"
    ) -> bool:
        """Check if current settings are compatible with JSON mode.

        Args:
            output_json: JSON output flag
            interactive: Whether interactive mode is enabled
            progress: Progress level setting

        Returns:
            True if settings are compatible with JSON output
        """
        if not output_json:
            return True

        # JSON mode is incompatible with interactive features
        if interactive:
            return False

        # JSON mode should use 'none' progress to avoid corrupting output
        if progress != "none":
            return False

        return True

    def format_list_response(
        self,
        items: List[Dict[str, Any]],
        operation: str = "list",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Format a list response (e.g., for list commands).

        Args:
            items: List of items to include
            operation: Name of the operation
            metadata: Additional metadata

        Returns:
            Dictionary with list structure
        """
        result: Dict[str, Any] = {"items": items, "count": len(items)}

        if self.include_metadata:
            metadata_dict = {
                "operation": operation,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
            if metadata:
                metadata_dict.update(metadata)
            result["metadata"] = metadata_dict

        return result

    def format_status_response(
        self,
        status: str,
        message: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Format a status response.

        Args:
            status: Status string (e.g., "success", "warning", "error")
            message: Optional status message
            data: Optional additional data

        Returns:
            Dictionary with status structure
        """
        result: Dict[str, Any] = {"status": status}

        if message:
            result["message"] = message

        if data:
            result["data"] = data

        if self.include_metadata:
            result["metadata"] = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "success": status in ["success", "completed"],
            }

        return result
