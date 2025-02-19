"""Custom Jinja2 extensions for enhanced template functionality.

This module provides extensions that modify Jinja2's default behavior:
- CommentExtension: Ignores variables inside comment blocks during validation and rendering
"""

from jinja2 import nodes
from jinja2.ext import Extension
from jinja2.parser import Parser


class CommentExtension(Extension):
    """Extension that ignores variables inside comment blocks.

    This extension ensures that:
    1. Contents of comment blocks are completely ignored during parsing
    2. Variables inside comments are not validated or processed
    3. Comments are stripped from the output
    4. Nested comments are not allowed (will raise a syntax error)

    Example:
        Valid usage:
        ```jinja
        {% comment %}
            This is a comment
            {{ some_var }}  # This variable will be ignored
        {% endcomment %}
        ```

        Invalid usage (will raise error):
        ```jinja
        {% comment %}
            Outer comment
            {% comment %}  # Error: Nested comments are not allowed
                Inner comment
            {% endcomment %}
        {% endcomment %}
        ```
    """

    tags = {"comment"}

    def parse(self, parser: Parser) -> nodes.Node:
        """Parse a comment block, ignoring its contents.

        Nested comments are not allowed and will raise a syntax error.
        This keeps the template syntax simpler and more predictable.

        Args:
            parser: The Jinja2 parser instance

        Returns:
            An empty node since comments are ignored

        Raises:
            TemplateSyntaxError: If the comment block is not properly closed
                                or if a nested comment is found
        """
        # Get the line number for error reporting
        lineno = parser.stream.current.lineno

        # Skip the opening comment tag
        next(parser.stream)

        # Skip until we find {% endcomment %}, rejecting nested comments
        while not parser.stream.current.test("name:endcomment"):
            if parser.stream.current.type == "eof":
                raise parser.fail("Unclosed comment block", lineno)

            # Explicitly reject nested comments
            if parser.stream.current.test("name:comment"):
                raise parser.fail(
                    "Nested comments are not allowed. Use separate comment blocks instead.",
                    parser.stream.current.lineno,
                )
            next(parser.stream)

        # Skip the endcomment tag
        next(parser.stream)

        # Return an empty string node
        return nodes.Output([nodes.TemplateData("")]).set_lineno(lineno)
