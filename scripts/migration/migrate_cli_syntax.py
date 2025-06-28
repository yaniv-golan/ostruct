#!/usr/bin/env python3
"""Migrate ostruct CLI syntax from legacy to new format.

This script helps users migrate from ostruct v0.8.x legacy file routing syntax
to the new v0.9.0 target/alias attachment system.

Usage:
    # Dry run (preview changes)
    python migrate_cli_syntax.py *.sh --dry-run

    # Apply migrations
    python migrate_cli_syntax.py *.sh

    # With validation
    python migrate_cli_syntax.py *.sh --validate

    # Migrate configuration files
    python migrate_cli_syntax.py --config ostruct.yaml
"""

import argparse
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml


class SyntaxMigrator:
    """Migrates ostruct command syntax from legacy to new format."""

    def __init__(self):
        self.migrations = [
            # Basic file attachments (space-form syntax)
            (r"-f\s+(\w+)\s+([^\s]+)", r"--file \1 \2"),
            # Directory attachments
            (r"-d\s+(\w+)\s+([^\s]+)", r"--dir \1 \2"),
            # Tool-specific routing (short forms)
            (r"-fc\s+([^\s]+)", r"--file ci:data \1"),
            (r"-fs\s+([^\s]+)", r"--file fs:docs \1"),
            (r"-ft\s+([^\s]+)", r"--file config \1"),
            # Directory routing (short forms)
            (r"-dc\s+([^\s]+)", r"--dir ci:data \1"),
            (r"-ds\s+([^\s]+)", r"--dir fs:docs \1"),
            (r"-dt\s+([^\s]+)", r"--dir config \1"),
            # Explicit tool routing (long forms)
            (r"--file-for-code-interpreter\s+([^\s]+)", r"--file ci:data \1"),
            (r"--file-for-file-search\s+([^\s]+)", r"--file fs:docs \1"),
            (r"--file-for-template\s+([^\s]+)", r"--file config \1"),
            # Directory routing (long forms)
            (r"--dir-for-code-interpreter\s+([^\s]+)", r"--dir ci:data \1"),
            (r"--dir-for-search\s+([^\s]+)", r"--dir fs:docs \1"),
            (r"--dir-for-template\s+([^\s]+)", r"--dir config \1"),
            # Alias forms (maintain aliases)
            (r"--fca\s+(\w+)\s+([^\s]+)", r"--file ci:\1 \2"),
            (r"--fsa\s+(\w+)\s+([^\s]+)", r"--file fs:\1 \2"),
            (r"--fta\s+(\w+)\s+([^\s]+)", r"--file \1 \2"),
            (r"--dca\s+(\w+)\s+([^\s]+)", r"--dir ci:\1 \2"),
            (r"--dsa\s+(\w+)\s+([^\s]+)", r"--dir fs:\1 \2"),
            (r"--dta\s+(\w+)\s+([^\s]+)", r"--dir \1 \2"),
            # Security options
            (r"-A\s+([^\s]+)", r"--allow \1"),
            (r"--allowed-dir\s+([^\s]+)", r"--allow \1"),
            (r"--base-dir\s+([^\s]+)", r"--path-security strict --allow \1"),
            # Pattern options
            (r"-p\s+([^\s]+)\s+([^\s]+)", r"--dir \2 \1 --pattern \1"),
            (r"--pattern\s+([^\s]+)", r"--pattern \1"),
            # Legacy flags
            (r"-R\b", r"--recursive"),
            (r"--recursive-dir\b", r"--recursive"),
        ]

    def migrate_line(self, line: str) -> Tuple[str, bool]:
        """Migrate a single line of shell script.

        Args:
            line: Original line of text

        Returns:
            Tuple of (migrated_line, changed_flag)
        """
        changed = False

        for pattern, replacement in self.migrations:
            new_line = re.sub(pattern, replacement, line)
            if new_line != line:
                line = new_line
                changed = True

        return line, changed

    def migrate_file(
        self, file_path: Path, dry_run: bool = True
    ) -> Dict[str, Any]:
        """Migrate entire file.

        Args:
            file_path: Path to file to migrate
            dry_run: If True, don't modify file (just analyze)

        Returns:
            Dictionary with migration results
        """
        results = {
            "file": str(file_path),
            "lines_changed": 0,
            "changes": [],
            "warnings": [],
            "backup": None,
        }

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception as e:
            results["warnings"].append(f"Cannot read file: {e}")
            return results

        new_lines = []
        for line_num, line in enumerate(lines, 1):
            new_line, changed = self.migrate_line(line)
            new_lines.append(new_line)

            if changed:
                results["lines_changed"] += 1
                results["changes"].append(
                    {
                        "line": line_num,
                        "before": line.strip(),
                        "after": new_line.strip(),
                    }
                )

        if not dry_run and results["lines_changed"] > 0:
            # Create backup
            backup_path = file_path.with_suffix(file_path.suffix + ".bak")
            try:
                # Copy original to backup
                with open(file_path, "r", encoding="utf-8") as original:
                    with open(backup_path, "w", encoding="utf-8") as backup:
                        backup.write(original.read())

                # Write migrated version
                with open(file_path, "w", encoding="utf-8") as f:
                    f.writelines(new_lines)

                results["backup"] = str(backup_path)
            except Exception as e:
                results["warnings"].append(
                    f"Failed to write migrated file: {e}"
                )

        return results


def migrate_configuration(
    config_path: Path, dry_run: bool = True
) -> Dict[str, Any]:
    """Migrate configuration files to new format.

    Args:
        config_path: Path to configuration file
        dry_run: If True, don't modify file

    Returns:
        Dictionary with migration results
    """
    results = {
        "file": str(config_path),
        "migrations": [],
        "warnings": [],
        "backup": None,
    }

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
    except Exception as e:
        results["warnings"].append(f"Cannot read configuration file: {e}")
        return results

    # Migrate file routing configuration
    if "file_routing" in config:
        config.pop("file_routing")
        if "attachments" not in config:
            config["attachments"] = {}

        config["attachments"].update(
            {"default_target": "prompt", "security_mode": "permissive"}
        )
        results["migrations"].append(
            "Converted file_routing to attachments configuration"
        )

    # Migrate security settings
    if "security" in config:
        security = config["security"]
        if "allowed_dirs" in security:
            if "attachments" not in config:
                config["attachments"] = {}
            config["attachments"]["allowed_directories"] = security[
                "allowed_dirs"
            ]
            results["migrations"].append(
                "Migrated allowed_dirs to allowed_directories"
            )

        # Migrate base_dir to security settings
        if "base_dir" in security:
            if "path_security" not in config:
                config["path_security"] = {}
            config["path_security"]["mode"] = "strict"
            config["path_security"]["allowed_directories"] = [
                security["base_dir"]
            ]
            results["migrations"].append(
                "Migrated base_dir to path_security configuration"
            )

    # Add new v0.9.0 configuration sections if needed
    if results["migrations"] and "tools" not in config:
        config["tools"] = {
            "code_interpreter": {"auto_download": True, "cleanup": True},
            "file_search": {"cleanup": True},
        }
        results["migrations"].append("Added default tools configuration")

    if not dry_run and results["migrations"]:
        # Create backup
        backup_path = config_path.with_suffix(config_path.suffix + ".bak")
        try:
            # Copy original to backup
            config_path.rename(backup_path)

            # Write migrated version
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)

            results["backup"] = str(backup_path)
        except Exception as e:
            results["warnings"].append(
                f"Failed to write migrated configuration: {e}"
            )

    return results


def validate_migration(
    original_file: Path, migrated_file: Path
) -> Dict[str, List[str]]:
    """Validate migration results.

    Args:
        original_file: Path to original file
        migrated_file: Path to migrated file

    Returns:
        Dictionary with validation results
    """
    validation = {
        "syntax_errors": [],
        "semantic_warnings": [],
        "compatibility_issues": [],
    }

    try:
        with open(migrated_file, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        validation["syntax_errors"].append(f"Cannot read migrated file: {e}")
        return validation

    # Check for missing aliases in attachments
    if re.search(r"--file\s+[^:\s]*\s*$", content):
        validation["syntax_errors"].append(
            "Found attachment without path - new syntax requires both alias and path"
        )

    # Check for malformed target:alias syntax
    if re.search(r"--file\s+[^:\s]*:[^:\s]*:[^:\s]*", content):
        validation["syntax_errors"].append(
            "Found malformed target:alias syntax - should be 'target:alias path' or 'alias path'"
        )

    # Check for security implications
    if "--path-security" not in content and "ostruct run" in content:
        validation["semantic_warnings"].append(
            "Consider adding --path-security for enhanced security"
        )

    # Check for complex routing that might need manual review
    if content.count("--file") > 5:
        validation["compatibility_issues"].append(
            "Complex file routing with many attachments detected - manual review recommended"
        )

    # Check for mixed old/new syntax
    legacy_patterns = ["-f ", "-d ", "-fc ", "-fs ", "-ft ", "--file-for-"]
    for pattern in legacy_patterns:
        if pattern in content:
            validation["syntax_errors"].append(
                f"Found unmigrated legacy syntax: {pattern}"
            )

    return validation


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Migrate ostruct CLI syntax from v0.8.x to v0.9.0",
        epilog="""
Examples:
  %(prog)s *.sh --dry-run              # Preview changes to shell scripts
  %(prog)s scripts/*.sh                # Migrate shell scripts
  %(prog)s --config ostruct.yaml       # Migrate configuration file
  %(prog)s *.sh --validate             # Migrate and validate results
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "files", nargs="*", help="Files to migrate (shell scripts, etc.)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show changes without modifying files",
    )
    parser.add_argument(
        "--validate", action="store_true", help="Validate migration results"
    )
    parser.add_argument(
        "--config", metavar="FILE", help="Migrate configuration file"
    )

    args = parser.parse_args()

    if not args.files and not args.config:
        parser.error("Must specify files to migrate or --config option")

    migrator = SyntaxMigrator()
    total_files = 0
    total_changes = 0

    # Handle configuration file migration
    if args.config:
        config_path = Path(args.config)
        if config_path.exists():
            print(f"🔧 Migrating configuration: {config_path}")
            result = migrate_configuration(config_path, args.dry_run)

            if result["migrations"]:
                print(f"   ✅ {len(result['migrations'])} migrations applied:")
                for migration in result["migrations"]:
                    print(f"      • {migration}")

                if result["backup"]:
                    print(f"   💾 Backup saved: {result['backup']}")
            else:
                print("   ℹ️  No migrations needed")

            if result["warnings"]:
                for warning in result["warnings"]:
                    print(f"   ⚠️  {warning}")
        else:
            print(f"❌ Configuration file not found: {config_path}")

    # Handle file migrations
    for file_pattern in args.files:
        for file_path in Path.cwd().glob(file_pattern):
            if file_path.is_file() and not file_path.name.endswith(".bak"):
                result = migrator.migrate_file(file_path, args.dry_run)
                total_files += 1
                total_changes += result["lines_changed"]

                if result["lines_changed"] > 0:
                    status = "📝 Preview" if args.dry_run else "✅ Migrated"
                    print(
                        f"{status}: {file_path} ({result['lines_changed']} changes)"
                    )

                    for change in result["changes"]:
                        print(f"  Line {change['line']}:")
                        print(f"    - {change['before']}")
                        print(f"    + {change['after']}")

                    if result["backup"]:
                        print(f"  💾 Backup: {result['backup']}")

                    # Run validation if requested
                    if args.validate and not args.dry_run:
                        validation = validate_migration(file_path, file_path)
                        if validation["syntax_errors"]:
                            print("  ❌ Validation errors:")
                            for error in validation["syntax_errors"]:
                                print(f"     • {error}")
                        if validation["semantic_warnings"]:
                            print("  ⚠️  Recommendations:")
                            for warning in validation["semantic_warnings"]:
                                print(f"     • {warning}")
                        if validation["compatibility_issues"]:
                            print("  🔍 Manual review needed:")
                            for issue in validation["compatibility_issues"]:
                                print(f"     • {issue}")

                if result["warnings"]:
                    for warning in result["warnings"]:
                        print(f"  ⚠️  {warning}")

    # Summary
    print(f"\n📊 Summary: {total_changes} changes across {total_files} files")

    if args.dry_run and total_changes > 0:
        print("🔍 This was a dry run. Use without --dry-run to apply changes.")

    if total_changes > 0 and not args.dry_run:
        print("✅ Migration complete! Backup files (.bak) have been created.")
        print("🧪 Test your migrated scripts before removing backup files.")


if __name__ == "__main__":
    main()
