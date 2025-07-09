"""Enhanced template error analysis for better user experience.

This module provides sophisticated analysis of Jinja2 template errors to give
users more helpful and context-aware error messages and fix suggestions.
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Set

import jinja2


class VariableReferenceType(Enum):
    """Types of variable references in templates."""

    SIMPLE = "simple"  # {{ var }}
    ATTRIBUTE = "attribute"  # {{ var.attr }}
    NESTED = "nested"  # {{ var.attr.subattr }}
    ITEM_ACCESS = "item"  # {{ var['key'] }}
    FILTER = "filter"  # {{ var | filter }}
    CONDITIONAL = "conditional"  # {% if var %}


@dataclass
class VariableReference:
    """Represents a variable reference found in a template."""

    variable_name: str
    full_path: str
    reference_type: VariableReferenceType
    line_number: Optional[int] = None
    context: Optional[str] = None
    parent_variable: Optional[str] = None
    attribute_path: Optional[List[str]] = None


@dataclass
class ErrorContext:
    """Context information for template errors."""

    missing_variable: str
    available_variables: Set[str]
    references: List[VariableReference]
    template_content: str


class TemplateErrorAnalyzer:
    """Analyzes template errors to provide enhanced error messages."""

    def __init__(self) -> None:
        self.env = jinja2.Environment(undefined=jinja2.StrictUndefined)

    def analyze_missing_variable_error(
        self,
        template: str,
        missing_variable: str,
        available_variables: Set[str],
    ) -> ErrorContext:
        """Analyze a missing variable error to provide enhanced context.

        Args:
            template: The template string
            missing_variable: The variable that's missing
            available_variables: Variables that are available

        Returns:
            ErrorContext with detailed analysis
        """
        # Use regex-based analysis for now - more reliable than AST parsing
        references = self._find_references_by_regex(template, missing_variable)

        return ErrorContext(
            missing_variable=missing_variable,
            available_variables=available_variables,
            references=references,
            template_content=template,
        )

    def _find_references_by_regex(
        self, template: str, variable_name: str
    ) -> List[VariableReference]:
        """Find variable references using regex patterns."""
        references = []

        # Pattern to match variable references
        escaped_var = re.escape(variable_name)
        patterns = [
            # {{ var.attr.subattr }}
            (
                r"\{\{\s*"
                + escaped_var
                + r"\.([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)\s*\}\}",
                True,
            ),
            # {{ var }}
            (r"\{\{\s*" + escaped_var + r"\s*\}\}", False),
            # {% if var.attr %}
            (
                r"\{%\s*if\s+"
                + escaped_var
                + r"\.([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)\s*%\}",
                True,
            ),
            # {% for item in var %}
            (r"\{%\s*for\s+\w+\s+in\s+" + escaped_var + r"\s*%\}", False),
        ]

        lines = template.split("\n")

        for i, line in enumerate(lines, 1):
            for pattern, has_attributes in patterns:
                matches = re.finditer(pattern, line)
                for match in matches:
                    if has_attributes and match.groups():
                        # Has attribute access
                        attr_path = match.group(1).split(".")
                        full_path = f"{variable_name}.{match.group(1)}"
                        ref_type = (
                            VariableReferenceType.NESTED
                            if len(attr_path) > 1
                            else VariableReferenceType.ATTRIBUTE
                        )
                    else:
                        # Simple variable reference
                        attr_path = None
                        full_path = variable_name
                        ref_type = VariableReferenceType.SIMPLE

                    references.append(
                        VariableReference(
                            variable_name=variable_name,
                            full_path=full_path,
                            reference_type=ref_type,
                            line_number=i,
                            context=line.strip(),
                            parent_variable=variable_name,
                            attribute_path=attr_path,
                        )
                    )

        return references

    def generate_enhanced_error_message(
        self, error_context: ErrorContext
    ) -> str:
        """Generate an enhanced error message with context and suggestions."""
        msg_parts = []

        # Header
        if error_context.references:
            primary_ref = error_context.references[0]
            msg_parts.append(
                f"Template validation error: '{primary_ref.full_path}'"
            )
        else:
            msg_parts.append(
                f"Template validation error: '{error_context.missing_variable}'"
            )

        msg_parts.append("")

        # Root cause analysis
        msg_parts.append("Root cause analysis:")
        msg_parts.append(
            f"✗ Variable '{error_context.missing_variable}' is not available"
        )

        if error_context.available_variables:
            available_list = ", ".join(
                sorted(error_context.available_variables)
            )
            msg_parts.append(f"✓ Available variables: {available_list}")

        msg_parts.append("")

        # Context from template
        if error_context.references:
            msg_parts.append("Template references:")
            for ref in error_context.references[:3]:  # Show up to 3 references
                line_info = (
                    f" (line {ref.line_number})" if ref.line_number else ""
                )
                msg_parts.append(f"  • {ref.full_path}{line_info}")
                if ref.context:
                    msg_parts.append(f"    Context: {ref.context}")

        msg_parts.append("")

        # Smart suggestions
        suggestions = self._generate_smart_suggestions(error_context)
        if suggestions:
            msg_parts.append("Possible fixes:")
            for i, suggestion in enumerate(suggestions, 1):
                msg_parts.append(f"{i}. {suggestion}")

        return "\n".join(msg_parts)

    def _generate_smart_suggestions(
        self, error_context: ErrorContext
    ) -> List[str]:
        """Generate smart fix suggestions based on the error context."""
        suggestions = []
        missing_var = error_context.missing_variable
        available_vars = error_context.available_variables

        # Check if there are similar variable names available
        similar_vars = self._find_similar_variables(
            missing_var, available_vars
        )

        # Analyze the type of references to provide targeted suggestions
        has_nested_refs = any(
            ref.reference_type
            in [VariableReferenceType.ATTRIBUTE, VariableReferenceType.NESTED]
            for ref in error_context.references
        )

        if has_nested_refs:
            # This looks like it should be a structured data variable
            suggestions.append(
                f"If '{missing_var}' should come from a file, use: --file {missing_var} path/to/file.json"
            )

            # Check if there's a similar variable that might contain the data
            for similar_var in similar_vars:
                if similar_var in available_vars:
                    suggestions.append(
                        f"If '{missing_var}' should be derived from '{similar_var}', update template to use:\n"
                        f"   {{% set {missing_var} = {similar_var}.content | from_json %}}"
                    )
                    break

            # Suggest JSON variable for complex structures
            example_structure = self._generate_example_json_structure(
                error_context.references
            )
            if example_structure:
                suggestions.append(
                    f"If '{missing_var}' is a template variable, use: -J {missing_var}='{example_structure}'"
                )
        else:
            # Simple variable reference
            if similar_vars:
                suggestions.append(
                    f"Did you mean one of: {', '.join(similar_vars)}?"
                )

            suggestions.append(
                f"If '{missing_var}' is a simple value, use: -V {missing_var}='value'"
            )
            suggestions.append(
                f"If '{missing_var}' should come from a file, use: --file {missing_var} path/to/file"
            )

        # Add template-level suggestions
        suggestions.append(
            f"Add a default value in template: {{{{ {missing_var} | default('fallback') }}}}"
        )

        return suggestions

    def _find_similar_variables(
        self, target: str, available: Set[str]
    ) -> List[str]:
        """Find variables with similar names to the target."""
        similar = []
        target_lower = target.lower()

        for var in available:
            var_lower = var.lower()
            # Simple similarity checks
            if target_lower in var_lower or var_lower in target_lower:
                similar.append(var)
            elif self._levenshtein_distance(target_lower, var_lower) <= 2:
                similar.append(var)

        return sorted(similar)

    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """Calculate Levenshtein distance between two strings."""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]

    def _generate_example_json_structure(
        self, references: List[VariableReference]
    ) -> Optional[str]:
        """Generate an example JSON structure based on the variable references."""
        if not references:
            return None

        # Build a nested structure based on the attribute paths
        structure: Dict[str, Any] = {}

        for ref in references:
            if ref.attribute_path:
                current = structure
                for attr in ref.attribute_path[:-1]:
                    if attr not in current:
                        current[attr] = {}
                    current = current[attr]

                # Set a placeholder value for the final attribute
                final_attr = ref.attribute_path[-1]
                current[final_attr] = "value"

        if structure:
            import json

            return json.dumps(structure, separators=(",", ":"))

        return None
