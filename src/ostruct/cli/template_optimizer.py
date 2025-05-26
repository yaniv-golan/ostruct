"""Automatic template optimization system for improved LLM performance."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class OptimizationResult:
    """Result of template optimization process."""

    optimized_template: str
    transformations: List[str]
    files_moved: List[str]
    inline_files_kept: List[str]
    optimization_time_ms: float

    @property
    def has_optimizations(self) -> bool:
        """Check if any optimizations were applied."""
        return bool(self.transformations)


class TemplateOptimizer:
    """Automatic prompt optimization using pure text manipulation.

    This optimizer applies prompt engineering best practices to improve LLM performance:
    - Moves large file content to structured appendices
    - Keeps small values inline for context
    - Generates natural language references
    - Maintains deterministic and fast processing
    """

    def __init__(self):
        """Initialize the template optimizer."""
        self.file_references: Dict[str, str] = {}
        self.dir_references: Dict[str, str] = {}
        self.optimization_log: List[str] = []
        self.inline_threshold = (
            200  # Characters threshold for inline vs appendix
        )
        self.small_value_threshold = (
            50  # Very small values stay inline regardless
        )

    def optimize_for_llm(self, template_content: str) -> OptimizationResult:
        """Apply prompt engineering best practices for files and directories.

        Args:
            template_content: Original template content

        Returns:
            OptimizationResult with optimized template and metadata
        """
        import time

        start_time = time.time()

        # Reset state for new optimization
        self.file_references.clear()
        self.dir_references.clear()
        self.optimization_log.clear()

        optimized = template_content
        inline_files_kept = []

        # Step 1: Find and optimize file_content() calls
        file_pattern = r'{{\s*([^}]*\.content|file_content\([^)]+\)|[^}]*\[["\'][^"\']*["\']\]\.content)\s*}}'

        def replace_file_reference(match):
            full_match = match.group(0)
            content_expr = match.group(1)

            # Extract file path from various patterns
            file_path = self._extract_file_path(content_expr)
            if not file_path:
                return full_match  # Keep original if can't parse

            # Check if content should stay inline
            try:
                if self._should_stay_inline(file_path):
                    inline_files_kept.append(file_path)
                    return full_match  # Keep inline

                # Generate reference for large files
                reference = self._generate_file_reference_text(file_path)
                self.file_references[file_path] = reference
                self.optimization_log.append(f"Moved {file_path} to appendix")
                return reference

            except Exception:
                # If any error, keep original
                return full_match

        optimized = re.sub(file_pattern, replace_file_reference, optimized)

        # Step 2: Optimize directory content references
        dir_pattern = (
            r"{{\s*([^}]*\.(files|content)|[^}]*\.files\[[^]]*\])\s*}}"
        )
        optimized = re.sub(dir_pattern, self._replace_dir_reference, optimized)

        # Step 3: Build comprehensive appendix if we moved files
        if self.file_references or self.dir_references:
            optimized += "\n\n" + self._build_complete_appendix()
            self.optimization_log.append(
                "Built structured appendix with moved content"
            )

        optimization_time = (time.time() - start_time) * 1000

        return OptimizationResult(
            optimized_template=optimized,
            transformations=self.optimization_log.copy(),
            files_moved=list(self.file_references.keys()),
            inline_files_kept=inline_files_kept,
            optimization_time_ms=optimization_time,
        )

    def _extract_file_path(self, content_expr: str) -> Optional[str]:
        """Extract file path from various Jinja2 content expressions.

        Args:
            content_expr: Jinja2 expression containing file reference

        Returns:
            Extracted file path or None if not found
        """
        # Pattern 1: file_content('path') or file_content("path")
        match = re.search(r'file_content\(["\']([^"\']+)["\']\)', content_expr)
        if match:
            return match.group(1)

        # Pattern 2: variable.content where variable is likely a file
        match = re.search(r"(\w+)\.content", content_expr)
        if match:
            var_name = match.group(1)
            # Common file variable patterns
            if any(
                keyword in var_name.lower()
                for keyword in ["file", "config", "data", "script", "code"]
            ):
                return f"${var_name}"  # Use variable name as placeholder

        # Pattern 3: files['filename'].content
        match = re.search(
            r'files\[["\']([^"\']+)["\']\]\.content', content_expr
        )
        if match:
            return match.group(1)

        return None

    def _should_stay_inline(self, file_path: str) -> bool:
        """Determine if file content should stay inline.

        Args:
            file_path: Path to the file

        Returns:
            True if content should stay inline, False if moved to appendix
        """
        # Variable references (${var}) should stay inline for now
        if file_path.startswith("$"):
            return True

        try:
            # Check actual file size if path exists
            path = Path(file_path)
            if path.exists() and path.is_file():
                content = path.read_text(encoding="utf-8", errors="ignore")
                content_size = len(content.strip())

                # Very small files stay inline
                if content_size <= self.small_value_threshold:
                    return True

                # Check if it's a simple value (no newlines, short)
                if (
                    content_size <= self.inline_threshold
                    and "\n" not in content.strip()
                ):
                    return True

                return False

        except Exception:
            pass

        # Default: move to appendix for unknown files
        return False

    def _generate_file_reference_text(self, file_path: str) -> str:
        """Generate natural language references using pattern matching.

        Args:
            file_path: Path to the file

        Returns:
            Natural language reference text
        """
        filename = Path(file_path).name.lower()

        # Pattern-based natural language generation
        if "config" in filename:
            return f"the configuration details in <file:{file_path}>"
        elif "rule" in filename or "policy" in filename:
            return f"the business rules defined in <file:{file_path}>"
        elif "schema" in filename:
            return f"the schema definition in <file:{file_path}>"
        elif "example" in filename or "sample" in filename:
            return f"the example shown in <file:{file_path}>"
        elif filename.endswith((".json", ".yaml", ".yml")):
            return f"the structured data from <file:{file_path}>"
        elif filename.endswith((".py", ".js", ".ts", ".java", ".cpp", ".c")):
            return f"the code implementation in <file:{file_path}>"
        elif filename.endswith((".md", ".txt", ".rst")):
            return f"the documentation in <file:{file_path}>"
        elif filename.endswith((".csv", ".xlsx", ".tsv")):
            return f"the data from <file:{file_path}>"
        elif "readme" in filename:
            return f"the project overview in <file:{file_path}>"
        elif "changelog" in filename or "history" in filename:
            return f"the change history in <file:{file_path}>"
        else:
            return f"the content of <file:{file_path}>"

    def _replace_dir_reference(self, match) -> str:
        """Replace directory content references with natural language.

        Args:
            match: Regex match object for directory reference

        Returns:
            Natural language reference or original text
        """
        full_match = match.group(0)
        content_expr = match.group(1)

        # Extract directory variable name
        dir_match = re.search(r"(\w+)\.(?:files|content)", content_expr)
        if not dir_match:
            return full_match

        dir_var = dir_match.group(1)
        reference = f"the files and subdirectories in <dir:{dir_var}>"
        self.dir_references[dir_var] = reference
        self.optimization_log.append(
            f"Moved directory {dir_var} content to appendix"
        )

        return reference

    def _build_complete_appendix(self) -> str:
        """Build comprehensive appendix with moved content.

        Returns:
            Formatted appendix section
        """
        appendix_lines = [
            "=" * 50,
            "APPENDIX: Referenced Files and Directories",
            "=" * 50,
        ]

        if self.file_references:
            appendix_lines.extend(["", "FILES:"])
            for file_path, reference in self.file_references.items():
                appendix_lines.append(f"  <file:{file_path}>")
                appendix_lines.append(f"    Referenced as: {reference}")
                # Note: Actual file content would be injected here during template rendering
                appendix_lines.append(
                    f"    {{{{ file_content('{file_path}') }}}}"
                )
                appendix_lines.append("")

        if self.dir_references:
            appendix_lines.extend(["DIRECTORIES:"])
            for dir_var, reference in self.dir_references.items():
                appendix_lines.append(f"  <dir:{dir_var}>")
                appendix_lines.append(f"    Referenced as: {reference}")
                appendix_lines.append(f"    {{{{ {dir_var}.files }}}}")
                appendix_lines.append("")

        return "\n".join(appendix_lines)

    def get_optimization_stats(self) -> Dict[str, int]:
        """Get statistics about the last optimization.

        Returns:
            Dictionary with optimization statistics
        """
        return {
            "files_moved": len(self.file_references),
            "directories_moved": len(self.dir_references),
            "total_transformations": len(self.optimization_log),
        }


def optimize_template_for_llm(template_content: str) -> OptimizationResult:
    """Convenience function for template optimization.

    Args:
        template_content: Original template content

    Returns:
        OptimizationResult with optimized template
    """
    optimizer = TemplateOptimizer()
    return optimizer.optimize_for_llm(template_content)


def is_optimization_beneficial(
    template_content: str, threshold_chars: int = 1000
) -> bool:
    """Check if template optimization would be beneficial.

    Args:
        template_content: Template content to analyze
        threshold_chars: Minimum size to consider optimization

    Returns:
        True if optimization would likely help
    """
    # Check template size
    if len(template_content) < threshold_chars:
        return False

    # Check for file content patterns
    file_patterns = [
        r"{{\s*[^}]*\.content\s*}}",
        r"{{\s*file_content\([^)]+\)\s*}}",
        r"{{\s*[^}]*\.files\s*}}",
    ]

    for pattern in file_patterns:
        if re.search(pattern, template_content):
            return True

    return False
