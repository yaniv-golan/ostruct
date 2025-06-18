"""Tests for system prompt handling and template processing."""

from typing import Any

import pytest
from ostruct.cli.errors import SystemPromptError
from ostruct.cli.template_processor import (
    DEFAULT_SYSTEM_PROMPT,
    process_system_prompt,
)
from ostruct.cli.template_rendering import create_jinja_env


class TestSystemPrompts:
    """Test system prompt handling functionality."""

    def test_default_system_prompt(self, fs: Any) -> None:
        """Test default system prompt when none is provided."""
        env = create_jinja_env()
        prompt, has_conflict = process_system_prompt(
            task_template="Test task",
            system_prompt=None,
            system_prompt_file=None,
            template_context={},
            env=env,
        )
        assert prompt == DEFAULT_SYSTEM_PROMPT
        assert has_conflict is False

    def test_direct_system_prompt(self, fs: Any) -> None:
        """Test system prompt provided directly."""
        test_prompt = "Custom system prompt"
        env = create_jinja_env()
        prompt, has_conflict = process_system_prompt(
            task_template="Test task",
            system_prompt=test_prompt,
            system_prompt_file=None,
            template_context={},
            env=env,
        )
        assert prompt == test_prompt
        assert has_conflict is False

    def test_system_prompt_from_file(self, fs: Any) -> None:
        """Test system prompt loaded from file."""
        test_prompt = "Custom system prompt from file"
        fs.create_file("prompt.txt", contents=test_prompt)
        env = create_jinja_env()

        prompt, has_conflict = process_system_prompt(
            task_template="Test task",
            system_prompt=None,
            system_prompt_file="prompt.txt",
            template_context={},
            env=env,
        )
        assert prompt == test_prompt
        assert has_conflict is False

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

        prompt, has_conflict = process_system_prompt(
            task_template=template_content,
            system_prompt=None,
            system_prompt_file=None,
            template_context={},
            env=env,
        )
        assert prompt == "Custom system prompt from template"
        assert has_conflict is False

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
        prompt1, has_conflict1 = process_system_prompt(
            task_template=template_content,
            system_prompt=direct_prompt,
            system_prompt_file=None,
            template_context={},
            env=env,
        )
        assert prompt1 == direct_prompt
        assert has_conflict1 is False

        # File prompt should take precedence over template
        prompt2, has_conflict2 = process_system_prompt(
            task_template=template_content,
            system_prompt=None,
            system_prompt_file="prompt.txt",
            template_context={},
            env=env,
        )
        assert prompt2 == file_prompt
        assert has_conflict2 is True  # This should detect the conflict

        # Template prompt should take precedence over default
        prompt3, has_conflict3 = process_system_prompt(
            task_template=template_content,
            system_prompt=None,
            system_prompt_file=None,
            template_context={},
            env=env,
        )
        assert prompt3 == "Template prompt"
        assert has_conflict3 is False

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
        prompt, has_conflict = process_system_prompt(
            task_template=template_content,
            system_prompt=None,
            system_prompt_file=None,
            template_context=template_context,
            env=env,
        )
        assert prompt == "You are a helpful assistant specialized in testing"
        assert has_conflict is False

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

    def test_include_system_order(self, fs: Any) -> None:
        """Test include_system ordering and template-relative path resolution."""
        # Create template file and include file in same directory
        fs.create_dir("/project/templates")

        # Create include_system file
        include_content = "You are an expert in data analysis."
        fs.create_file(
            "/project/templates/shared_prompt.txt", contents=include_content
        )

        # Create template with include_system
        template_content = """---
model: gpt-4o
include_system: shared_prompt.txt
system_prompt: Additional instructions for this specific task.
---
## File: output.txt
Test task"""

        template_path = "/project/templates/task.j2"
        fs.create_file(template_path, contents=template_content)

        env = create_jinja_env()

        # Test include_system resolution
        prompt, has_conflict = process_system_prompt(
            task_template=template_content,
            system_prompt=None,
            system_prompt_file=None,
            template_context={},
            env=env,
            template_path=template_path,
        )

        # Should contain include_system content and template system_prompt
        assert include_content in prompt
        assert "Additional instructions for this specific task." in prompt
        assert has_conflict is False

        # Check ordering: include_system should come before system_prompt
        include_pos = prompt.find(include_content)
        system_pos = prompt.find(
            "Additional instructions for this specific task."
        )
        assert include_pos < system_pos

    def test_include_system_file_not_found(self, fs: Any) -> None:
        """Test error handling when include_system file is not found."""
        template_content = """---
model: gpt-4o
include_system: nonexistent.txt
---
## File: output.txt
Test task"""

        template_path = "/project/task.j2"
        fs.create_file(template_path, contents=template_content)

        env = create_jinja_env()

        with pytest.raises(Exception) as exc_info:
            process_system_prompt(
                task_template=template_content,
                system_prompt=None,
                system_prompt_file=None,
                template_context={},
                env=env,
                template_path=template_path,
            )
        assert "include_system file not found" in str(exc_info.value)

    def test_include_system_without_template_path(self, fs: Any) -> None:
        """Test include_system is ignored when template_path is None."""
        template_content = """---
model: gpt-4o
include_system: shared_prompt.txt
system_prompt: Only this should appear.
---
## File: output.txt
Test task"""

        env = create_jinja_env()

        # Call without template_path - include_system should be ignored
        prompt, has_conflict = process_system_prompt(
            task_template=template_content,
            system_prompt=None,
            system_prompt_file=None,
            template_context={},
            env=env,
            template_path=None,  # No template path
        )

        # Should only contain system_prompt, not include_system
        assert "Only this should appear." in prompt
        assert "shared_prompt" not in prompt
        assert has_conflict is False
