"""Quick reference help system for ostruct CLI.

This module provides quick usage examples and patterns with rich formatting.
Uses rich-click formatting for beautiful, organized output.
"""

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text


def show_quick_ref_help() -> None:
    """Display quick reference help with rich formatting."""
    console = Console(stderr=True)

    # Main title
    title = Text("🚀 OSTRUCT QUICK REFERENCE", style="bold bright_blue")
    console.print(title)
    console.print()

    # File Attachment System
    attachment_content = """[bold bright_blue]--file[/bold bright_blue] alias file.txt                     📄 Template access (default target)
[bold bright_blue]--file[/bold bright_blue] ci:data file.csv                   💻 Code Interpreter upload
[bold bright_blue]--file[/bold bright_blue] fs:docs file.pdf                   🔍 File Search vector store
[bold bright_blue]--file[/bold bright_blue] prompt:config config.yaml         📄 Template access (explicit)

[bold bright_blue]--dir[/bold bright_blue] alias ./src                         📁 Directory attachment (template)
[bold bright_blue]--dir[/bold bright_blue] ci:data ./datasets                  📂 Code execution directory
[bold bright_blue]--dir[/bold bright_blue] fs:docs ./documentation             📁 Search directory"""

    attachment_panel = Panel(
        attachment_content,
        title="[bold]📎 File Attachment System[/bold]",
        border_style="blue",
        padding=(1, 2),
    )
    console.print(attachment_panel)

    # Multi-tool Routing
    routing_content = """[bold cyan]--file ci,fs:shared data.csv[/bold cyan]              Share file between Code Interpreter and File Search
[bold cyan]--file prompt,ci:config settings.json[/bold cyan]    Make file available in template AND Code Interpreter"""

    routing_panel = Panel(
        routing_content,
        title="[bold]🔄 Multi-Tool Routing[/bold]",
        border_style="cyan",
        padding=(1, 2),
    )
    console.print(routing_panel)

    # File Collections
    collections_content = """[bold green]--collect all:files @filelist.txt[/bold green]         📄 Attach multiple files from list
[bold green]--collect ci:data @datasets.txt[/bold green]           💻 Upload file collection to Code Interpreter"""

    collections_panel = Panel(
        collections_content,
        title="[bold]📝 File Collections[/bold]",
        border_style="green",
        padding=(1, 2),
    )
    console.print(collections_panel)

    # Variables and Tools
    vars_tools_content = """[bold yellow]Variables:[/bold yellow]
[cyan]-V name=value[/cyan]                             Simple string variables
[cyan]-J config='{"key":"value"}'[/cyan]               JSON structured data

[bold yellow]Tools:[/bold yellow]
[cyan]--enable-tool web-search[/cyan]                  🌐 Real-time web search for current info
[cyan]--mcp-server label@https://server.com/sse[/cyan] MCP server integration
[cyan]--timeout 7200[/cyan]                           2-hour timeout for long operations"""

    vars_tools_panel = Panel(
        vars_tools_content,
        title="[bold]🏷️ Variables & 🔌 Tools[/bold]",
        border_style="yellow",
        padding=(1, 2),
    )
    console.print(vars_tools_panel)

    # Common Patterns
    console.print(Text("⚡ Common Patterns", style="bold bright_green"))
    console.print()

    patterns = [
        (
            "Basic template rendering",
            "ostruct run template.j2 schema.json -V env=prod",
        ),
        (
            "Data analysis with Code Interpreter",
            "ostruct run analysis.j2 schema.json --file ci:data data.csv -V task=analyze",
        ),
        (
            "Document search + processing",
            "ostruct run search.j2 schema.json --file fs:docs docs/ --file config config.yaml",
        ),
        (
            "Multi-tool workflow",
            "ostruct run workflow.j2 schema.json --file ci:data raw_data.csv --file fs:knowledge knowledge/ --file config config.json",
        ),
        (
            "Current information research",
            'ostruct run research.j2 schema.json --enable-tool web-search -V topic="latest AI developments"',
        ),
    ]

    for desc, cmd in patterns:
        console.print(f"[dim]# {desc}[/dim]")
        syntax = Syntax(
            cmd, "bash", theme="monokai", background_color="default"
        )
        console.print(syntax)
        console.print()

    # Footer with help links
    footer_content = """📖 [cyan]ostruct run --help[/cyan]           Detailed options reference
📖 [cyan]ostruct run --help-debug[/cyan]      Troubleshooting guide
📖 [dim]https://ostruct.readthedocs.io[/dim]   Full documentation"""

    footer_panel = Panel(
        footer_content,
        title="[bold]📖 More Help[/bold]",
        border_style="blue",
        padding=(1, 2),
    )
    console.print(footer_panel)
