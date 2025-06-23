"""Template debugging help system for ostruct CLI.

This module provides comprehensive help and examples for template debugging features.
"""

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text


def show_template_debug_help() -> None:
    """Display comprehensive template debugging help with rich formatting."""
    console = Console(stderr=True)

    # Main title
    title = Text(
        "🐛 Template Debugging Quick Reference", style="bold bright_blue"
    )
    console.print(title)
    console.print()

    # Basic debugging section
    basic_content = """[bold bright_blue]--debug[/bold bright_blue]                     🐛 Enable all debug output (verbose logging + template expansion)
[bold bright_blue]--template-debug[/bold bright_blue] CAPACITIES 📝 Enable specific debugging capacities (see CAPACITIES below)"""

    basic_panel = Panel(
        basic_content,
        title="[bold]Basic Debugging[/bold]",
        border_style="blue",
        padding=(1, 2),
    )
    console.print(basic_panel)

    # Capacities section
    capacities_content = """[bold cyan]pre-expand[/bold cyan]                 📋 Show template variables before expansion
[bold cyan]vars[/bold cyan]                       📊 Show template variable types and names
[bold cyan]preview[/bold cyan]                    👁️  Show preview of variable content
[bold cyan]steps[/bold cyan]                      🔄 Show step-by-step template expansion
[bold cyan]post-expand[/bold cyan]                📝 Show expanded templates after processing"""

    capacities_panel = Panel(
        capacities_content,
        title="[bold]Available Capacities[/bold]",
        border_style="cyan",
        padding=(1, 2),
    )
    console.print(capacities_panel)

    # Examples section
    console.print(Text("🔍 Examples", style="bold bright_green"))
    console.print()

    # Basic debugging examples
    basic_examples = [
        (
            "Show everything (most verbose)",
            "ostruct run template.j2 schema.json --debug --file config config.yaml",
        ),
        (
            "Just template content (clean)",
            "ostruct run template.j2 schema.json --template-debug post-expand --file config config.yaml",
        ),
        (
            "Show variables and context",
            "ostruct run template.j2 schema.json --template-debug vars,preview --file config config.yaml",
        ),
        (
            "Step-by-step expansion",
            "ostruct run template.j2 schema.json --template-debug steps --file config config.yaml",
        ),
    ]

    for desc, cmd in basic_examples:
        console.print(f"[dim]# {desc}[/dim]")
        syntax = Syntax(
            cmd, "bash", theme="monokai", background_color="default"
        )
        console.print(syntax)
        console.print()

    # Combined debugging example
    console.print("[dim]# Full debugging with context[/dim]")
    combined_cmd = "ostruct run template.j2 schema.json --debug --template-debug vars,preview,post-expand --file config config.yaml"
    syntax = Syntax(
        combined_cmd, "bash", theme="monokai", background_color="default"
    )
    console.print(syntax)
    console.print()

    # Troubleshooting section
    troubleshooting_title = Text(
        "🚨 Troubleshooting Common Issues", style="bold red"
    )
    console.print(troubleshooting_title)
    console.print()

    # Create troubleshooting panels
    issues = [
        {
            "title": "❌ Undefined Variable Errors",
            "problem": "UndefinedError: 'variable_name' is undefined",
            "solution": "Use --template-debug vars,preview to see available variables",
            "example": "ostruct run template.j2 schema.json --template-debug vars,preview --file config config.yaml",
        },
        {
            "title": "❌ Template Not Expanding",
            "problem": "Template appears unchanged in output",
            "solution": "Use --template-debug post-expand to see expansion",
            "example": "ostruct run template.j2 schema.json --template-debug post-expand --file config config.yaml",
        },
        {
            "title": "❌ Performance Issues",
            "problem": "Template rendering is slow",
            "solution": "Use --template-debug steps to see processing bottlenecks",
            "example": "ostruct run template.j2 schema.json --template-debug steps --file config config.yaml",
        },
    ]

    for issue in issues:
        content = f"""[bold red]Problem:[/bold red] {issue["problem"]}
[bold green]Solution:[/bold green] {issue["solution"]}
[bold blue]Example:[/bold blue]
[dim cyan]{issue["example"]}[/dim cyan]"""

        panel = Panel(
            content,
            title=f"[bold]{issue['title']}[/bold]",
            border_style="red",
            padding=(1, 2),
        )
        console.print(panel)
        console.print()

    # Pro tips section
    tips_content = """• Use [bold cyan]--dry-run[/bold cyan] with debugging flags to avoid API calls
• Combine multiple debug capacities: [bold cyan]--template-debug vars,preview,post-expand[/bold cyan]
• Start with [bold cyan]--template-debug post-expand[/bold cyan] for basic template issues
• Use [bold cyan]--debug[/bold cyan] for full diagnostic information
• Use [bold cyan]--template-debug vars,preview[/bold cyan] when variables are undefined"""

    tips_panel = Panel(
        tips_content,
        title="[bold]💡 Pro Tips[/bold]",
        border_style="yellow",
        padding=(1, 2),
    )
    console.print(tips_panel)

    # Footer
    console.print()
    footer = Text(
        "📚 For more information, see: docs/template_debugging.md",
        style="dim italic",
    )
    console.print(footer)


def show_quick_debug_tips() -> None:
    """Show quick debugging tips for common issues with rich formatting."""
    console = Console(stderr=True)

    title = Text("🚀 Quick Debug Tips", style="bold bright_green")
    console.print(title)
    console.print()

    content = """[bold]Template not working? Try:[/bold]
  1. [cyan]ostruct run template.j2 schema.json --template-debug post-expand --dry-run[/cyan]
  2. [cyan]ostruct run template.j2 schema.json --template-debug vars,preview --dry-run[/cyan]
  3. [cyan]ostruct run template.j2 schema.json --debug --dry-run[/cyan]

[bold]Performance issues? Try:[/bold]
  1. [cyan]ostruct run template.j2 schema.json --template-debug steps --dry-run[/cyan]

[dim]For full help: ostruct run --help-debug[/dim]"""

    panel = Panel(content, border_style="green", padding=(1, 2))
    console.print(panel)


def show_debug_examples() -> None:
    """Show practical debugging examples with rich formatting."""
    console = Console(stderr=True)

    title = Text("🎯 Template Debugging Examples", style="bold bright_blue")
    console.print(title)
    console.print()

    examples = [
        {
            "title": "📝 Basic Template Issues",
            "commands": [
                (
                    "Check if template expands correctly",
                    "ostruct run my_template.j2 schema.json --template-debug post-expand --dry-run --file config config.yaml",
                ),
                (
                    "See what variables are available",
                    "ostruct run my_template.j2 schema.json --template-debug vars,preview --dry-run --file config config.yaml",
                ),
                (
                    "Full debug output",
                    "ostruct run my_template.j2 schema.json --debug --dry-run --file config config.yaml",
                ),
            ],
        },
        {
            "title": "🔧 Performance Issues",
            "commands": [
                (
                    "Track template processing steps",
                    "ostruct run my_template.j2 schema.json --template-debug steps --dry-run --file config config.yaml",
                )
            ],
        },
    ]

    for example in examples:
        console.print(Text(str(example["title"]), style="bold bright_blue"))
        console.print()

        for desc, cmd in example["commands"]:
            console.print(f"[dim]# {desc}[/dim]")
            syntax = Syntax(
                cmd, "bash", theme="monokai", background_color="default"
            )
            console.print(syntax)
            console.print()

    # Advanced example
    console.print(Text("🔍 Advanced Debugging", style="bold bright_blue"))
    console.print()
    console.print("[dim]# Combine multiple debug features[/dim]")

    advanced_cmd = """ostruct run my_template.j2 schema.json \\
    --debug \\
    --template-debug vars,preview,post-expand,steps \\
    --dry-run \\
    --file config config.yaml"""

    syntax = Syntax(
        advanced_cmd, "bash", theme="monokai", background_color="default"
    )
    console.print(syntax)
    console.print()

    # Reminder
    reminder = Panel(
        "[bold yellow]💡 Remember: Always use --dry-run when debugging to avoid API calls![/bold yellow]",
        border_style="yellow",
        padding=(0, 2),
    )
    console.print(reminder)
