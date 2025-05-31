"""Token limit validation with actionable error guidance."""

import logging
import os
from pathlib import Path
from typing import List, Optional, Tuple

import tiktoken

from .errors import PromptTooLargeError


class TokenLimitValidator:
    """Validate prompt size and provide corrective guidance for explicit file routing."""

    MAX_TOKENS = 128000  # Model context window limit

    def __init__(self, model: str = "gpt-4o"):
        """Initialize validator with model-specific encoding.

        Args:
            model: Model name for token encoding selection
        """
        self.model = model
        self.encoder = self._get_encoder(model)

    def _get_encoder(self, model: str) -> tiktoken.Encoding:
        """Get appropriate tiktoken encoder for model."""
        if model.startswith(("gpt-4o", "o1", "o3")):
            return tiktoken.get_encoding("o200k_base")
        else:
            return tiktoken.get_encoding("cl100k_base")

    def validate_prompt_size(
        self,
        template_content: str,
        template_files: List[str],
        context_limit: Optional[int] = None,
    ) -> None:
        """Check if prompt will exceed context window and provide actionable guidance.

        Args:
            template_content: Rendered template content
            template_files: List of file paths included in template
            context_limit: Optional custom context limit (defaults to MAX_TOKENS)

        Raises:
            PromptTooLargeError: If prompt exceeds context window with actionable guidance
        """
        logger = logging.getLogger(__name__)

        limit = context_limit or self.MAX_TOKENS
        total_tokens = self._count_template_tokens(template_content)

        oversized_files = []
        for file_path in template_files:
            try:
                file_tokens = self._count_file_tokens(file_path)
                total_tokens += file_tokens

                # Flag files over 5K tokens for routing guidance
                if file_tokens > 5000:
                    oversized_files.append((file_path, file_tokens))
            except (OSError, IOError):
                # Skip files that can't be read for token counting
                continue

        # Add 90% warning threshold
        if total_tokens > limit * 0.9:
            logger.warning(
                "Prompt is %.1f%% of the %d-token window (%d tokens)",
                total_tokens / limit * 100,
                limit,
                total_tokens,
            )

        if total_tokens > limit:
            self._raise_actionable_error(total_tokens, limit, oversized_files)

    def _count_template_tokens(self, content: str) -> int:
        """Count tokens in template content."""
        return len(self.encoder.encode(content))

    def _count_file_tokens(self, file_path: str) -> int:
        """Count tokens in a file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                return len(self.encoder.encode(content))
        except UnicodeDecodeError:
            # For binary files, estimate based on file size
            # Rough estimate: 1 token per 4 bytes
            file_size = os.path.getsize(file_path)
            return file_size // 4

    def _is_data_file(self, file_path: str) -> bool:
        """Detect if file is likely a data file suitable for Code Interpreter."""
        data_extensions = {
            ".csv",
            ".json",
            ".xlsx",
            ".xls",
            ".tsv",
            ".parquet",
            ".sql",
            ".db",
            ".sqlite",
            ".sqlite3",
            ".pkl",
            ".pickle",
            ".npy",
            ".npz",
            ".h5",
            ".hdf5",
            ".xml",
            ".yaml",
            ".yml",
        }
        return Path(file_path).suffix.lower() in data_extensions

    def _is_document_file(self, file_path: str) -> bool:
        """Detect if file is likely a document suitable for File Search."""
        doc_extensions = {
            ".pdf",
            ".doc",
            ".docx",
            ".txt",
            ".md",
            ".rst",
            ".tex",
            ".html",
            ".htm",
            ".rtf",
            ".odt",
            ".epub",
            ".mobi",
        }
        return Path(file_path).suffix.lower() in doc_extensions

    def _is_code_file(self, file_path: str) -> bool:
        """Detect if file is likely source code."""
        code_extensions = {
            ".py",
            ".js",
            ".ts",
            ".java",
            ".cpp",
            ".c",
            ".h",
            ".hpp",
            ".cs",
            ".go",
            ".rs",
            ".rb",
            ".php",
            ".swift",
            ".kt",
            ".scala",
            ".r",
            ".m",
            ".sh",
            ".bash",
            ".ps1",
            ".pl",
            ".lua",
            ".dart",
        }
        return Path(file_path).suffix.lower() in code_extensions

    def _raise_actionable_error(
        self,
        total_tokens: int,
        limit: int,
        oversized_files: List[Tuple[str, int]],
    ) -> None:
        """Raise PromptTooLargeError with specific guidance for explicit file routing."""
        error_msg = (
            f"❌ Error: Prompt exceeds model context window "
            f"({total_tokens:,} tokens > {limit:,} limit)\n\n"
        )

        if oversized_files:
            error_msg += "💡 Suggestion: Re-run with explicit file routing to move large files out of template context:\n\n"

            for file_path, tokens in oversized_files:
                file_name = Path(file_path).name

                if self._is_data_file(file_path):
                    error_msg += f"   📊 Data file: ostruct -fc {file_name} <template> <schema>\n"
                    error_msg += f"       (Moves {file_name} to Code Interpreter for data processing)\n\n"
                elif self._is_document_file(file_path):
                    error_msg += f"   📄 Document: ostruct -fs {file_name} <template> <schema>\n"
                    error_msg += f"       (Moves {file_name} to File Search for semantic retrieval)\n\n"
                elif self._is_code_file(file_path):
                    error_msg += f"   💻 Code file: ostruct -fc {file_name} <template> <schema>\n"
                    error_msg += f"       (Moves {file_name} to Code Interpreter for analysis)\n\n"
                else:
                    error_msg += f"   📁 Large file: ostruct -fc {file_name} OR -fs {file_name} <template> <schema>\n"
                    error_msg += "       (Choose based on usage: -fc for processing, -fs for retrieval)\n\n"

                error_msg += (
                    f"       Size: {tokens:,} tokens ({file_path})\n\n"
                )

            error_msg += (
                "🔧 Alternative: Use --file-for for specific tool routing:\n"
            )
            error_msg += f"    ostruct --file-for code-interpreter {oversized_files[0][0]} <template> <schema>\n\n"

        else:
            error_msg += "💡 Suggestion: Consider breaking down your template or using fewer input files\n\n"

        error_msg += "🔍 Check file sizes: tiktoken_cli count <filename>\n"
        error_msg += "📖 Learn more: ostruct --help (see File Routing section)"

        raise PromptTooLargeError(
            error_msg,
            context={
                "total_tokens": total_tokens,
                "context_limit": limit,
                "oversized_files": [
                    (path, tokens) for path, tokens in oversized_files
                ],
                "suggested_routing": self._generate_routing_suggestions(
                    oversized_files
                ),
            },
        )

    def _generate_routing_suggestions(
        self, oversized_files: List[Tuple[str, int]]
    ) -> List[dict]:
        """Generate structured routing suggestions for programmatic use."""
        suggestions = []
        for file_path, tokens in oversized_files:
            suggestion = {
                "file_path": file_path,
                "tokens": tokens,
                "file_type": self._classify_file(file_path),
                "recommended_flags": self._get_recommended_flags(file_path),
            }
            suggestions.append(suggestion)
        return suggestions

    def _classify_file(self, file_path: str) -> str:
        """Classify file type for routing suggestions."""
        if self._is_data_file(file_path):
            return "data"
        elif self._is_document_file(file_path):
            return "document"
        elif self._is_code_file(file_path):
            return "code"
        else:
            return "unknown"

    def _get_recommended_flags(self, file_path: str) -> List[str]:
        """Get recommended CLI flags for file routing."""
        if self._is_data_file(file_path) or self._is_code_file(file_path):
            return ["-fc", "--file-for code-interpreter"]
        elif self._is_document_file(file_path):
            return ["-fs", "--file-for file-search"]
        else:
            return ["-fc", "-fs"]  # Both options for unknown files


def validate_token_limits(
    template_content: str,
    template_files: List[str],
    model: str,
    context_limit: Optional[int] = None,
) -> None:
    """Convenience function for token limit validation.

    Args:
        template_content: Rendered template content
        template_files: List of file paths included in template
        model: Model name for encoding selection
        context_limit: Optional custom context limit

    Raises:
        PromptTooLargeError: If prompt exceeds context window
    """
    validator = TokenLimitValidator(model)
    validator.validate_prompt_size(
        template_content, template_files, context_limit
    )
