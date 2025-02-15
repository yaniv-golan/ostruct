"""Tests for system prompt handling and template processing."""

from typing import Any

import pytest

from ostruct.cli.cli import DEFAULT_SYSTEM_PROMPT, process_system_prompt
from ostruct.cli.errors import SystemPromptError
from ostruct.cli.template_rendering import create_jinja_env


class TestSystemPrompts:
    """Test system prompt handling functionality."""

    def test_default_system_prompt(self, fs: Any) -> None:
        """Test default system prompt when none is provided."""
        env = create_jinja_env()
        prompt = process_system_prompt(
            task_template="Test task",
            system_prompt=None,
            system_prompt_file=None,
            template_context={},
            env=env,
        )
        assert prompt == DEFAULT_SYSTEM_PROMPT

    def test_direct_system_prompt(self, fs: Any) -> None:
        """Test system prompt provided directly."""
        test_prompt = "Custom system prompt"
        env = create_jinja_env()
        prompt = process_system_prompt(
            task_template="Test task",
            system_prompt=test_prompt,
            system_prompt_file=None,
            template_context={},
            env=env,
        )
        assert prompt == test_prompt

    def test_system_prompt_from_file(self, fs: Any) -> None:
        """Test system prompt loaded from file."""
        test_prompt = "Custom system prompt from file"
        fs.create_file("prompt.txt", contents=test_prompt)
        env = create_jinja_env()

        prompt = process_system_prompt(
            task_template="Test task",
            system_prompt=None,
            system_prompt_file="prompt.txt",
            template_context={},
            env=env,
        )
        assert prompt == test_prompt

    def test_system_prompt_from_template(self, fs: Any) -> None:
        """Test system prompt from template frontmatter."""
        template_content = """---
model: gpt-4o
temperature: 0.7
system_prompt: Custom system prompt from template
---
## File: output.txt
Test task"""
        env = create_jinja_env()

        prompt = process_system_prompt(
            task_template=template_content,
            system_prompt=None,
            system_prompt_file=None,
            template_context={},
            env=env,
        )
        assert prompt == "Custom system prompt from template"

    def test_system_prompt_precedence(self, fs: Any) -> None:
        """Test system prompt precedence (direct > file > template > default)."""
        # Create template with frontmatter
        template_content = """---
model: gpt-4o
temperature: 0.7
system_prompt: Template prompt
---
## File: output.txt
Test task"""

        # Create prompt file
        file_prompt = "File prompt"
        fs.create_file("prompt.txt", contents=file_prompt)

        env = create_jinja_env()

        # Direct prompt should take precedence over all
        direct_prompt = "Direct prompt"
        prompt1 = process_system_prompt(
            task_template=template_content,
            system_prompt=direct_prompt,
            system_prompt_file=None,
            template_context={},
            env=env,
        )
        assert prompt1 == direct_prompt

        # File prompt should take precedence over template
        prompt2 = process_system_prompt(
            task_template=template_content,
            system_prompt=None,
            system_prompt_file="prompt.txt",
            template_context={},
            env=env,
        )
        assert prompt2 == file_prompt

        # Template prompt should take precedence over default
        prompt3 = process_system_prompt(
            task_template=template_content,
            system_prompt=None,
            system_prompt_file=None,
            template_context={},
            env=env,
        )
        assert prompt3 == "Template prompt"

    def test_system_prompt_with_variables(self, fs: Any) -> None:
        """Test variable interpolation in system prompts."""
        template_content = """---
model: gpt-4o
temperature: 0.7
system_prompt: You are a {{ role }} assistant specialized in {{ domain }}
---
## File: output.txt
Test task"""

        template_context = {"role": "helpful", "domain": "testing"}

        env = create_jinja_env()
        prompt = process_system_prompt(
            task_template=template_content,
            system_prompt=None,
            system_prompt_file=None,
            template_context=template_context,
            env=env,
        )
        assert prompt == "You are a helpful assistant specialized in testing"

    def test_invalid_system_prompt_file(self, fs: Any) -> None:
        """Test error handling for invalid system prompt file."""
        env = create_jinja_env()
        with pytest.raises(SystemPromptError) as exc_info:
            process_system_prompt(
                task_template="Test task",
                system_prompt=None,
                system_prompt_file="nonexistent.txt",
                template_context={},
                env=env,
            )
        assert "Failed to load system prompt file" in str(exc_info.value)

    def test_invalid_template_frontmatter(self, fs: Any) -> None:
        """Test error handling for invalid template frontmatter."""
        template_content = """---
model: gpt-4o
temperature: 0.7
invalid: yaml: content:
---
## File: output.txt
Test task"""

        env = create_jinja_env()
        with pytest.raises(SystemPromptError):
            process_system_prompt(
                task_template=template_content,
                system_prompt=None,
                system_prompt_file=None,
                template_context={},
                env=env,
            )

    def test_conflicting_system_prompts(self, fs: Any) -> None:
        """Test error handling when both system prompt string and file are provided."""
        fs.create_file("prompt.txt", contents="File prompt")
        env = create_jinja_env()
        with pytest.raises(SystemPromptError) as exc:
            process_system_prompt(
                task_template="Test task",
                system_prompt="Direct prompt",
                system_prompt_file="prompt.txt",
                template_context={},
                env=env,
            )
        assert "Cannot specify both" in str(exc.value)
