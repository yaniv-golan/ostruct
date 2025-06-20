"""Template debugging help system for ostruct CLI.

This module provides comprehensive help and examples for template debugging features.
"""

import click

TEMPLATE_DEBUG_HELP = """
🐛 Template Debugging Quick Reference

BASIC DEBUGGING:
  --debug                     🐛 Enable all debug output (verbose logging + template expansion)
  --template-debug CAPACITIES 📝 Enable specific debugging capacities (see CAPACITIES below)

CAPACITIES:
  pre-expand                 📋 Show template variables before expansion
  vars                       📊 Show template variable types and names
  preview                    👁️  Show preview of variable content
  steps                      🔄 Show step-by-step template expansion
  post-expand                📝 Show expanded templates after processing
  optimization               🔧 Show optimization analysis
  optimization-steps         🔧 Show detailed optimization step tracking

OPTIMIZATION DEBUGGING:
  --show-pre-optimization    🔧 Show template before optimization
  --show-optimization-diff   🔄 Show optimization changes (before/after comparison)
  --show-optimization-steps  🔧 Show detailed optimization step tracking
  --optimization-step-detail [summary|detailed]  📊 Control step detail level
  --no-optimization          ⚡ Skip optimization entirely for debugging

PERFORMANCE ANALYSIS:
  --profile-template         ⏱️  Show template performance breakdown (future)
  --analyze-optimization     📊 Show optimization impact analysis (future)

INTERACTIVE DEBUGGING:
  ostruct debug template.j2 schema.json --debug-shell  🎯 Interactive debug shell (future)

EXAMPLES:

🔍 Basic Template Debugging:
  # Show everything (most verbose)
  ostruct run template.j2 schema.json --debug -ft config.yaml

  # Just template content (clean output)
  ostruct run template.j2 schema.json --template-debug post-expand -ft config.yaml

  # Show template variables and context
  ostruct run template.j2 schema.json --template-debug vars,preview -ft config.yaml

  # Show step-by-step expansion
  ostruct run template.j2 schema.json --template-debug steps -ft config.yaml

🔧 Optimization Debugging:
  # See template before optimization
  ostruct run template.j2 schema.json --show-pre-optimization -ft config.yaml

  # See what optimization changed
  ostruct run template.j2 schema.json --show-optimization-diff -ft config.yaml

  # See step-by-step optimization process
  ostruct run template.j2 schema.json --show-optimization-steps -ft config.yaml

  # Detailed optimization steps with full diffs
  ostruct run template.j2 schema.json --show-optimization-steps --optimization-step-detail detailed -ft config.yaml

  # Skip optimization entirely
  ostruct run template.j2 schema.json --no-optimization -ft config.yaml

🎯 Combined Debugging:
  # Show both optimization diff and steps
  ostruct run template.j2 schema.json --show-optimization-diff --show-optimization-steps -ft config.yaml

  # Full debugging with context and optimization
  ostruct run template.j2 schema.json --debug --show-context --show-optimization-diff -ft config.yaml

🚨 Troubleshooting Common Issues:

❌ Undefined Variable Errors:
  Problem: UndefinedError: 'variable_name' is undefined
  Solution: Use --template-debug vars,preview to see available variables
  Example: ostruct run template.j2 schema.json --template-debug vars,preview -ft config.yaml

❌ Template Not Expanding:
  Problem: Template appears unchanged in output
  Solution: Use --template-debug post-expand to see expansion
  Example: ostruct run template.j2 schema.json --template-debug post-expand -ft config.yaml

❌ Optimization Breaking Template:
  Problem: Template works without optimization but fails with it
  Solution: Use --show-optimization-diff to see changes
  Example: ostruct run template.j2 schema.json --show-optimization-diff -ft config.yaml

❌ Performance Issues:
  Problem: Template rendering is slow
  Solution: Use --show-optimization-steps to see bottlenecks
  Example: ostruct run template.j2 schema.json --show-optimization-steps -ft config.yaml

💡 Pro Tips:
  • Use --dry-run with debugging flags to avoid API calls
  • Combine multiple debug capacities: --template-debug vars,preview,post-expand
  • Start with --template-debug post-expand for basic template issues
  • Use --debug for full diagnostic information
  • Use --template-debug vars,preview when variables are undefined
  • Use optimization debugging when templates work but optimization fails

📚 For more information, see: docs/template_debugging.md
"""


def show_template_debug_help() -> None:
    """Display comprehensive template debugging help."""
    click.echo(TEMPLATE_DEBUG_HELP, err=True)


def show_quick_debug_tips() -> None:
    """Show quick debugging tips for common issues."""
    quick_tips = """
🚀 Quick Debug Tips:

Template not working? Try:
  1. ostruct run template.j2 schema.json --template-debug post-expand --dry-run
  2. ostruct run template.j2 schema.json --template-debug vars,preview --dry-run
  3. ostruct run template.j2 schema.json --debug --dry-run

Optimization issues? Try:
  1. ostruct run template.j2 schema.json --show-optimization-diff --dry-run
  2. ostruct run template.j2 schema.json --no-optimization --dry-run

For full help: ostruct run --help-debug
"""
    click.echo(quick_tips, err=True)


def show_debug_examples() -> None:
    """Show practical debugging examples."""
    examples = """
🎯 Template Debugging Examples:

📝 Basic Template Issues:
  # Check if template expands correctly
  ostruct run my_template.j2 schema.json --template-debug post-expand --dry-run --file config config.yaml

  # See what variables are available
  ostruct run my_template.j2 schema.json --template-debug vars,preview --dry-run --file config config.yaml

  # Full debug output
  ostruct run my_template.j2 schema.json --debug --dry-run --file config config.yaml

🔧 Optimization Issues:
  # See what optimization does to your template
  ostruct run my_template.j2 schema.json --show-optimization-diff --dry-run --file config config.yaml

  # Track each optimization step
  ostruct run my_template.j2 schema.json --show-optimization-steps --dry-run --file config config.yaml

  # Bypass optimization entirely
  ostruct run my_template.j2 schema.json --no-optimization --dry-run --file config config.yaml

🔍 Advanced Debugging:
  # Combine multiple debug features
  ostruct run my_template.j2 schema.json \\
    --debug \\
    --template-debug vars,preview,post-expand \\
    --show-optimization-diff \\
    --show-optimization-steps \\
    --dry-run \\
    --file config config.yaml

💡 Remember: Always use --dry-run when debugging to avoid API calls!
"""
    click.echo(examples, err=True)
