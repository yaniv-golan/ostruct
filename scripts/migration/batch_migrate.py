#!/usr/bin/env python3
"""Batch migration tool for multiple projects using ostruct.

This script helps migrate entire projects or directories containing
multiple scripts and configuration files from v0.8.x to v0.9.0.

Usage:
    python batch_migrate.py /path/to/project --dry-run     # Preview all changes
    python batch_migrate.py /path/to/project               # Migrate project
    python batch_migrate.py . --recursive                  # Migrate current dir recursively
"""

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List

# Import our migration tools
from migrate_cli_syntax import (
    SyntaxMigrator,
    migrate_configuration,
    validate_migration,
)
from migrate_config import ConfigMigrator


class BatchMigrator:
    """Batch migration tool for entire projects."""

    def __init__(self):
        self.syntax_migrator = SyntaxMigrator()
        self.config_migrator = ConfigMigrator()

        # File patterns to process
        self.script_patterns = [
            "*.sh",
            "*.bash",
            "*.zsh",  # Shell scripts
            "*.bat",
            "*.cmd",
            "*.ps1",  # Windows scripts
            "*.py",  # Python scripts
            "Makefile",
            "*.mk",  # Makefiles
            "*.yml",
            "*.yaml",  # YAML files (configs and CI/CD)
        ]

        self.config_patterns = [
            "ostruct.yaml",
            "ostruct.yml",
            ".ostruct.yaml",
            ".ostruct.yml",
        ]

    def find_files(
        self, root_path: Path, recursive: bool = False
    ) -> Dict[str, List[Path]]:
        """Find all files that might need migration.

        Args:
            root_path: Root directory to search
            recursive: Whether to search recursively

        Returns:
            Dictionary categorizing found files
        """
        found_files = {"scripts": [], "configs": [], "other": []}

        search_pattern = "**/*" if recursive else "*"

        for file_path in root_path.glob(search_pattern):
            if not file_path.is_file():
                continue

            # Skip backup files and hidden files
            if file_path.name.endswith(".bak") or file_path.name.startswith(
                "."
            ):
                continue

            # Categorize files
            if any(
                file_path.match(pattern) for pattern in self.config_patterns
            ):
                found_files["configs"].append(file_path)
            elif any(
                file_path.match(pattern) for pattern in self.script_patterns
            ):
                # Quick check if file contains ostruct commands
                try:
                    with open(
                        file_path, "r", encoding="utf-8", errors="ignore"
                    ) as f:
                        content = f.read()
                        if "ostruct run" in content or "ostruct " in content:
                            found_files["scripts"].append(file_path)
                except (OSError, UnicodeDecodeError):
                    pass  # Skip files we can't read

        return found_files

    def analyze_project(
        self, root_path: Path, recursive: bool = False
    ) -> Dict[str, Any]:
        """Analyze project for migration needs.

        Args:
            root_path: Root directory to analyze
            recursive: Whether to search recursively

        Returns:
            Analysis results
        """
        analysis = {
            "project_path": str(root_path),
            "files_found": {},
            "migration_needed": False,
            "estimated_changes": 0,
            "risk_assessment": "low",
            "recommendations": [],
        }

        # Find files
        found_files = self.find_files(root_path, recursive)
        analysis["files_found"] = {
            "scripts": len(found_files["scripts"]),
            "configs": len(found_files["configs"]),
            "total": sum(len(files) for files in found_files.values()),
        }

        # Analyze each file type
        script_changes = 0
        config_changes = 0

        for script_path in found_files["scripts"]:
            result = self.syntax_migrator.migrate_file(
                script_path, dry_run=True
            )
            script_changes += result["lines_changed"]

        for config_path in found_files["configs"]:
            try:
                import yaml

                with open(config_path, "r", encoding="utf-8") as f:
                    config = yaml.safe_load(f) or {}
                config_analysis = self.config_migrator.analyze_config(config)
                if config_analysis["needs_migration"]:
                    config_changes += 1
            except (OSError, UnicodeDecodeError, yaml.YAMLError):
                pass  # Skip files we can't read

        analysis["estimated_changes"] = script_changes + config_changes
        analysis["migration_needed"] = analysis["estimated_changes"] > 0

        # Risk assessment
        total_files = analysis["files_found"]["total"]
        if total_files > 20 or script_changes > 50:
            analysis["risk_assessment"] = "high"
        elif total_files > 10 or script_changes > 20:
            analysis["risk_assessment"] = "medium"

        # Generate recommendations
        if analysis["migration_needed"]:
            analysis["recommendations"] = [
                "Create a full backup of your project before migration",
                "Test migrated scripts in a development environment first",
                "Update CI/CD pipelines to use new syntax",
                "Review security settings for path_security configuration",
            ]

            if analysis["risk_assessment"] == "high":
                analysis["recommendations"].insert(
                    0, "Consider migrating in stages due to project complexity"
                )

        return analysis

    def migrate_project(
        self,
        root_path: Path,
        recursive: bool = False,
        dry_run: bool = True,
        validate: bool = False,
    ) -> Dict[str, Any]:
        """Migrate entire project.

        Args:
            root_path: Root directory to migrate
            recursive: Whether to search recursively
            dry_run: Whether to preview changes only
            validate: Whether to validate results

        Returns:
            Migration results
        """
        results = {
            "project_path": str(root_path),
            "files_migrated": 0,
            "total_changes": 0,
            "scripts_results": [],
            "config_results": [],
            "errors": [],
            "warnings": [],
        }

        found_files = self.find_files(root_path, recursive)

        # Migrate scripts
        for script_path in found_files["scripts"]:
            try:
                result = self.syntax_migrator.migrate_file(
                    script_path, dry_run
                )
                if result["lines_changed"] > 0:
                    results["files_migrated"] += 1
                    results["total_changes"] += result["lines_changed"]
                    results["scripts_results"].append(result)

                    # Validate if requested and not dry run
                    if validate and not dry_run:
                        validation = validate_migration(
                            script_path, script_path
                        )
                        result["validation"] = validation

            except Exception as e:
                results["errors"].append(f"Error migrating {script_path}: {e}")

        # Migrate configs
        for config_path in found_files["configs"]:
            try:
                result = migrate_configuration(config_path, dry_run)
                if result["migrations"]:
                    results["files_migrated"] += 1
                    results["config_results"].append(result)

            except Exception as e:
                results["errors"].append(f"Error migrating {config_path}: {e}")

        return results

    def generate_report(
        self,
        analysis: Dict[str, Any],
        migration_results: Dict[str, Any] = None,
    ) -> str:
        """Generate a migration report.

        Args:
            analysis: Project analysis results
            migration_results: Migration results (optional)

        Returns:
            Formatted report string
        """
        report = []
        report.append("# ostruct Migration Report")
        report.append(f"**Project**: {analysis['project_path']}")
        report.append(
            f"**Date**: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        report.append("")

        # Analysis section
        report.append("## Analysis")
        report.append(f"- **Files found**: {analysis['files_found']['total']}")
        report.append(f"  - Scripts: {analysis['files_found']['scripts']}")
        report.append(f"  - Configs: {analysis['files_found']['configs']}")
        report.append(
            f"- **Migration needed**: {'Yes' if analysis['migration_needed'] else 'No'}"
        )
        report.append(
            f"- **Estimated changes**: {analysis['estimated_changes']}"
        )
        report.append(f"- **Risk assessment**: {analysis['risk_assessment']}")
        report.append("")

        if analysis["recommendations"]:
            report.append("## Recommendations")
            for rec in analysis["recommendations"]:
                report.append(f"- {rec}")
            report.append("")

        # Migration results section
        if migration_results:
            report.append("## Migration Results")
            report.append(
                f"- **Files migrated**: {migration_results['files_migrated']}"
            )
            report.append(
                f"- **Total changes**: {migration_results['total_changes']}"
            )

            if migration_results["errors"]:
                report.append("- **Errors encountered**: Yes")
                report.append("")
                report.append("### Errors")
                for error in migration_results["errors"]:
                    report.append(f"- {error}")
                report.append("")

            if migration_results["scripts_results"]:
                report.append("### Script Migrations")
                for result in migration_results["scripts_results"]:
                    if result["lines_changed"] > 0:
                        report.append(
                            f"- **{result['file']}**: {result['lines_changed']} changes"
                        )
                        if result.get("backup"):
                            report.append(f"  - Backup: {result['backup']}")
                report.append("")

            if migration_results["config_results"]:
                report.append("### Configuration Migrations")
                for result in migration_results["config_results"]:
                    report.append(
                        f"- **{result['file']}**: {len(result['migrations'])} migrations"
                    )
                    for migration in result["migrations"]:
                        report.append(f"  - {migration}")
                report.append("")

        return "\n".join(report)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Batch migrate ostruct projects from v0.8.x to v0.9.0",
        epilog="""
Examples:
  %(prog)s /path/to/project --analyze           # Analyze project only
  %(prog)s /path/to/project --dry-run           # Preview all migrations
  %(prog)s /path/to/project --recursive         # Migrate project recursively
  %(prog)s . --validate --report report.md     # Migrate and create report
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("path", help="Project directory to migrate")
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Search subdirectories recursively",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without modifying files",
    )
    parser.add_argument(
        "--analyze",
        action="store_true",
        help="Only analyze project (no migration)",
    )
    parser.add_argument(
        "--validate", action="store_true", help="Validate migration results"
    )
    parser.add_argument(
        "--report", metavar="FILE", help="Generate migration report file"
    )

    args = parser.parse_args()

    project_path = Path(args.path).resolve()
    if not project_path.exists():
        print(f"❌ Project path does not exist: {project_path}")
        sys.exit(1)

    if not project_path.is_dir():
        print(f"❌ Path is not a directory: {project_path}")
        sys.exit(1)

    migrator = BatchMigrator()

    print(f"🔍 Analyzing project: {project_path}")
    analysis = migrator.analyze_project(project_path, args.recursive)

    print("\n📊 Analysis Results:")
    print(f"   📁 Files found: {analysis['files_found']['total']}")
    print(f"      • Scripts: {analysis['files_found']['scripts']}")
    print(f"      • Configs: {analysis['files_found']['configs']}")
    print(
        f"   🔄 Migration needed: {'Yes' if analysis['migration_needed'] else 'No'}"
    )
    print(f"   📈 Estimated changes: {analysis['estimated_changes']}")
    print(f"   ⚠️  Risk level: {analysis['risk_assessment']}")

    if analysis["recommendations"]:
        print("\n💡 Recommendations:")
        for rec in analysis["recommendations"]:
            print(f"   • {rec}")

    if args.analyze:
        print("\n✅ Analysis complete.")
        return

    if not analysis["migration_needed"]:
        print(
            "\n✅ No migration needed - project is already v0.9.0 compatible."
        )
        return

    # Perform migration
    print("\n🔄 Starting migration...")
    migration_results = migrator.migrate_project(
        project_path, args.recursive, args.dry_run, args.validate
    )

    print("\n📊 Migration Results:")
    print(f"   ✅ Files migrated: {migration_results['files_migrated']}")
    print(f"   🔢 Total changes: {migration_results['total_changes']}")

    if migration_results["errors"]:
        print(f"   ❌ Errors: {len(migration_results['errors'])}")
        for error in migration_results["errors"]:
            print(f"      • {error}")

    # Generate report if requested
    if args.report:
        report_content = migrator.generate_report(analysis, migration_results)
        try:
            with open(args.report, "w", encoding="utf-8") as f:
                f.write(report_content)
            print(f"\n📝 Report saved: {args.report}")
        except Exception as e:
            print(f"\n❌ Error saving report: {e}")

    if args.dry_run:
        print(
            "\n🔍 This was a dry run. Use without --dry-run to apply changes."
        )
    else:
        print("\n✅ Migration complete!")
        print(
            "🧪 Test your migrated scripts before removing .bak backup files."
        )


if __name__ == "__main__":
    main()
