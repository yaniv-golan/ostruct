#!/usr/bin/env python3
"""Migrate ostruct configuration files from v0.8.x to v0.9.0 format.

This script specifically handles configuration file migration with detailed
analysis and validation of configuration changes.

Usage:
    python migrate_config.py ostruct.yaml --dry-run    # Preview changes
    python migrate_config.py ostruct.yaml              # Apply migration
    python migrate_config.py *.yaml --validate         # Migrate multiple files
"""

import argparse
from pathlib import Path
from typing import Any, Dict, List

import yaml


class ConfigMigrator:
    """Migrates ostruct configuration files to v0.9.0 format."""

    def __init__(self):
        self.version_changes = {
            "from": "0.8.x",
            "to": "0.9.0",
            "breaking_changes": [
                "file_routing section removed - replaced with attachments",
                "security.allowed_dirs moved to attachments.allowed_directories",
                "New path_security configuration section",
                "New tools configuration for code_interpreter and file_search",
            ],
        }

    def analyze_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze configuration and determine what needs migration.

        Args:
            config: Configuration dictionary

        Returns:
            Analysis results
        """
        analysis = {
            "version_detected": "unknown",
            "needs_migration": False,
            "legacy_sections": [],
            "missing_sections": [],
            "recommendations": [],
        }

        # Detect version based on structure
        if "file_routing" in config:
            analysis["version_detected"] = "0.8.x"
            analysis["needs_migration"] = True
            analysis["legacy_sections"].append("file_routing")

        if "security" in config and "allowed_dirs" in config["security"]:
            analysis["legacy_sections"].append("security.allowed_dirs")
            analysis["needs_migration"] = True

        # Check for v0.9.0 sections
        if "attachments" not in config:
            analysis["missing_sections"].append("attachments")

        if "path_security" not in config:
            analysis["missing_sections"].append("path_security")

        if "tools" not in config:
            analysis["missing_sections"].append("tools")

        # Generate recommendations
        if analysis["needs_migration"]:
            analysis["recommendations"] = [
                "Backup your current configuration before migration",
                "Review migrated attachment settings",
                "Test new security modes with your workflows",
                "Update any automation scripts to use new CLI syntax",
            ]

        return analysis

    def migrate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate configuration to v0.9.0 format.

        Args:
            config: Original configuration

        Returns:
            Migration results
        """
        migrated_config = config.copy()
        migrations = []
        warnings = []

        # 1. Migrate file_routing to attachments
        if "file_routing" in migrated_config:
            old_routing = migrated_config.pop("file_routing")

            if "attachments" not in migrated_config:
                migrated_config["attachments"] = {}

            # Map old file routing settings
            attachments = migrated_config["attachments"]

            if "default_target" in old_routing:
                target_mapping = {
                    "template": "prompt",
                    "code_interpreter": "code-interpreter",
                    "file_search": "file-search",
                }
                attachments["default_target"] = target_mapping.get(
                    old_routing["default_target"], "prompt"
                )
            else:
                attachments["default_target"] = "prompt"

            if "auto_alias" in old_routing:
                attachments["auto_alias"] = old_routing["auto_alias"]

            migrations.append(
                "Migrated file_routing to attachments configuration"
            )

        # 2. Migrate security settings
        if "security" in migrated_config:
            security = migrated_config["security"]

            # Move allowed_dirs to attachments
            if "allowed_dirs" in security:
                if "attachments" not in migrated_config:
                    migrated_config["attachments"] = {}

                migrated_config["attachments"]["allowed_directories"] = (
                    security.pop("allowed_dirs")
                )
                migrations.append(
                    "Moved security.allowed_dirs to attachments.allowed_directories"
                )

            # Create path_security section
            if "base_dir" in security or "mode" in security:
                if "path_security" not in migrated_config:
                    migrated_config["path_security"] = {}

                if "mode" in security:
                    migrated_config["path_security"]["mode"] = security.pop(
                        "mode"
                    )
                else:
                    migrated_config["path_security"]["mode"] = "warn"

                if "base_dir" in security:
                    base_dir = security.pop("base_dir")
                    migrated_config["path_security"]["allowed_directories"] = [
                        base_dir
                    ]

                migrations.append(
                    "Created path_security configuration from legacy security settings"
                )

            # Remove security section if empty
            if not security:
                migrated_config.pop("security")
                migrations.append("Removed empty security section")

        # 3. Add default tools configuration if missing
        if "tools" not in migrated_config:
            migrated_config["tools"] = {
                "code_interpreter": {
                    "auto_download": True,
                    "output_directory": "./downloads",
                    "cleanup": True,
                },
                "file_search": {
                    "vector_store_name": "ostruct_search",
                    "cleanup": True,
                    "retry_count": 3,
                    "timeout": 60.0,
                },
            }
            migrations.append("Added default tools configuration")

        # 4. Update models section for v0.9.0
        if "models" in migrated_config:
            models = migrated_config["models"]
            if "default" in models and models["default"] == "gpt-4":
                models["default"] = "gpt-4o"
                migrations.append("Updated default model from gpt-4 to gpt-4o")
                warnings.append(
                    "Default model changed to gpt-4o - verify this works for your use case"
                )
        else:
            migrated_config["models"] = {"default": "gpt-4o"}
            migrations.append("Added default models configuration")

        # 5. Add version metadata
        migrated_config["_migration"] = {
            "from_version": "0.8.x",
            "to_version": "0.9.0",
            "migrated_sections": migrations,
        }

        return {
            "config": migrated_config,
            "migrations": migrations,
            "warnings": warnings,
        }

    def validate_config(self, config: Dict[str, Any]) -> Dict[str, List[str]]:
        """Validate migrated configuration.

        Args:
            config: Migrated configuration

        Returns:
            Validation results
        """
        validation = {"errors": [], "warnings": [], "recommendations": []}

        # Check required sections
        required_sections = ["attachments", "models"]
        for section in required_sections:
            if section not in config:
                validation["errors"].append(
                    f"Missing required section: {section}"
                )

        # Validate attachments section
        if "attachments" in config:
            attachments = config["attachments"]

            if "default_target" not in attachments:
                validation["warnings"].append(
                    "No default_target specified in attachments"
                )
            elif attachments["default_target"] not in [
                "prompt",
                "code-interpreter",
                "file-search",
            ]:
                validation["errors"].append(
                    f"Invalid default_target: {attachments['default_target']}"
                )

        # Validate path_security section
        if "path_security" in config:
            path_security = config["path_security"]

            if "mode" in path_security:
                valid_modes = ["permissive", "warn", "strict"]
                if path_security["mode"] not in valid_modes:
                    validation["errors"].append(
                        f"Invalid path_security mode: {path_security['mode']}"
                    )

        # Validate tools section
        if "tools" in config:
            tools = config["tools"]

            if "code_interpreter" in tools:
                ci_config = tools["code_interpreter"]
                if "output_directory" in ci_config:
                    output_dir = Path(ci_config["output_directory"])
                    if (
                        not output_dir.exists()
                        and str(output_dir) != "./downloads"
                    ):
                        validation["warnings"].append(
                            f"Code interpreter output directory doesn't exist: {output_dir}"
                        )

        # Security recommendations
        if "path_security" not in config:
            validation["recommendations"].append(
                "Consider adding path_security configuration for enhanced security"
            )

        if config.get("path_security", {}).get("mode") == "permissive":
            validation["recommendations"].append(
                "Consider using 'warn' or 'strict' security mode for better security"
            )

        return validation


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Migrate ostruct configuration files from v0.8.x to v0.9.0",
        epilog="""
Examples:
  %(prog)s ostruct.yaml --dry-run      # Preview configuration changes
  %(prog)s ostruct.yaml               # Migrate configuration file
  %(prog)s *.yaml --validate          # Migrate and validate multiple files
  %(prog)s ostruct.yaml --analyze     # Only analyze without migrating
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "files", nargs="+", help="Configuration files to migrate"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show changes without modifying files",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate migrated configuration",
    )
    parser.add_argument(
        "--analyze",
        action="store_true",
        help="Only analyze configuration (no migration)",
    )

    args = parser.parse_args()

    migrator = ConfigMigrator()

    for file_pattern in args.files:
        for config_path in Path.cwd().glob(file_pattern):
            if config_path.is_file() and config_path.suffix in [
                ".yaml",
                ".yml",
            ]:
                print(f"\n🔧 Processing: {config_path}")

                try:
                    with open(config_path, "r", encoding="utf-8") as f:
                        config = yaml.safe_load(f) or {}
                except Exception as e:
                    print(f"❌ Error reading file: {e}")
                    continue

                # Analyze configuration
                analysis = migrator.analyze_config(config)
                print(f"📋 Detected version: {analysis['version_detected']}")

                if analysis["legacy_sections"]:
                    print(
                        f"🔄 Legacy sections found: {', '.join(analysis['legacy_sections'])}"
                    )

                if analysis["missing_sections"]:
                    print(
                        f"➕ Missing v0.9.0 sections: {', '.join(analysis['missing_sections'])}"
                    )

                if args.analyze:
                    # Only show analysis
                    if analysis["recommendations"]:
                        print("💡 Recommendations:")
                        for rec in analysis["recommendations"]:
                            print(f"   • {rec}")
                    continue

                if not analysis["needs_migration"]:
                    print("✅ Configuration is already v0.9.0 compatible")
                    continue

                # Perform migration
                migration_result = migrator.migrate_config(config)
                migrated_config = migration_result["config"]

                if migration_result["migrations"]:
                    print("🔄 Migrations applied:")
                    for migration in migration_result["migrations"]:
                        print(f"   • {migration}")

                if migration_result["warnings"]:
                    print("⚠️  Warnings:")
                    for warning in migration_result["warnings"]:
                        print(f"   • {warning}")

                # Validate if requested
                if args.validate:
                    validation = migrator.validate_config(migrated_config)

                    if validation["errors"]:
                        print("❌ Validation errors:")
                        for error in validation["errors"]:
                            print(f"   • {error}")

                    if validation["warnings"]:
                        print("⚠️  Validation warnings:")
                        for warning in validation["warnings"]:
                            print(f"   • {warning}")

                    if validation["recommendations"]:
                        print("💡 Recommendations:")
                        for rec in validation["recommendations"]:
                            print(f"   • {rec}")

                # Write migrated configuration
                if not args.dry_run:
                    try:
                        # Create backup
                        backup_path = config_path.with_suffix(
                            config_path.suffix + ".bak"
                        )
                        config_path.rename(backup_path)
                        print(f"💾 Backup saved: {backup_path}")

                        # Write migrated version
                        with open(config_path, "w", encoding="utf-8") as f:
                            yaml.dump(
                                migrated_config,
                                f,
                                default_flow_style=False,
                                sort_keys=False,
                            )

                        print(f"✅ Migration complete: {config_path}")

                    except Exception as e:
                        print(f"❌ Error writing migrated file: {e}")
                else:
                    print("🔍 Dry run - no files modified")

    if args.dry_run:
        print(
            "\n🔍 This was a dry run. Use without --dry-run to apply changes."
        )


if __name__ == "__main__":
    main()
