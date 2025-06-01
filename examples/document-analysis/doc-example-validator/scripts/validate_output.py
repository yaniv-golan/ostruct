#!/usr/bin/env python3
"""
validate_output.py - Validates documentation example validator output

This script validates that the generated JSON file conforms to the expected
schema and contains reasonable task structures.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any


def validate_project_info(project_info: Dict[str, Any]) -> List[str]:
    """Validate project_info section"""
    errors = []
    required_fields = [
        "name",
        "type",
        "documentation_files_analyzed",
        "total_examples_found",
        "analysis_timestamp",
    ]

    for field in required_fields:
        if field not in project_info:
            errors.append(f"Missing required field in project_info: {field}")

    if "total_examples_found" in project_info:
        if (
            not isinstance(project_info["total_examples_found"], int)
            or project_info["total_examples_found"] < 0
        ):
            errors.append(
                "total_examples_found must be a non-negative integer"
            )

    return errors


def validate_task_management(task_management: Dict[str, Any]) -> List[str]:
    """Validate task_management section"""
    errors = []
    required_fields = [
        "instructions",
        "status_legend",
        "ai_agent_instructions",
    ]

    for field in required_fields:
        if field not in task_management:
            errors.append(
                f"Missing required field in task_management: {field}"
            )

    # Validate status legend has required statuses
    if "status_legend" in task_management:
        required_statuses = [
            "PENDING",
            "IN_PROGRESS",
            "COMPLETED",
            "FAILED",
            "BLOCKED",
        ]
        for status in required_statuses:
            if status not in task_management["status_legend"]:
                errors.append(f"Missing status in status_legend: {status}")

    return errors


def validate_task(task: Dict[str, Any], task_index: int) -> List[str]:
    """Validate individual task structure"""
    errors = []
    required_fields = [
        "id",
        "title",
        "status",
        "priority",
        "dependencies",
        "example_location",
        "validation_criteria",
        "test_instructions",
        "category",
    ]

    for field in required_fields:
        if field not in task:
            errors.append(
                f"Task {task_index}: Missing required field: {field}"
            )

    # Validate task ID format
    if "id" in task:
        task_id = task["id"]
        if not isinstance(task_id, str) or not task_id:
            errors.append(f"Task {task_index}: id must be a non-empty string")
        elif not task_id.startswith("T") or "." not in task_id:
            errors.append(
                f"Task {task_index}: id should follow format 'T{{group}}.{{number}}'"
            )

    # Validate status
    valid_statuses = [
        "PENDING",
        "IN_PROGRESS",
        "COMPLETED",
        "FAILED",
        "BLOCKED",
        "SKIPPED",
    ]
    if "status" in task and task["status"] not in valid_statuses:
        errors.append(f"Task {task_index}: Invalid status '{task['status']}'")

    # Validate priority
    valid_priorities = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    if "priority" in task and task["priority"] not in valid_priorities:
        errors.append(
            f"Task {task_index}: Invalid priority '{task['priority']}'"
        )

    # Validate dependencies is a list
    if "dependencies" in task and not isinstance(task["dependencies"], list):
        errors.append(f"Task {task_index}: dependencies must be a list")

    # Validate example_location structure
    if "example_location" in task:
        loc = task["example_location"]
        if not isinstance(loc, dict):
            errors.append(
                f"Task {task_index}: example_location must be an object"
            )
        else:
            required_loc_fields = ["file", "section"]
            for field in required_loc_fields:
                if field not in loc:
                    errors.append(
                        f"Task {task_index}: Missing field in example_location: {field}"
                    )

    # Validate arrays
    array_fields = ["validation_criteria", "test_instructions"]
    for field in array_fields:
        if field in task and not isinstance(task[field], list):
            errors.append(f"Task {task_index}: {field} must be an array")
        elif field in task and len(task[field]) == 0:
            errors.append(f"Task {task_index}: {field} cannot be empty")

    return errors


def validate_dependencies(tasks: List[Dict[str, Any]]) -> List[str]:
    """Validate task dependencies reference existing tasks"""
    errors = []
    task_ids = {task.get("id") for task in tasks if "id" in task}

    for i, task in enumerate(tasks):
        if "dependencies" in task:
            for dep_id in task["dependencies"]:
                if dep_id not in task_ids:
                    errors.append(
                        f"Task {i}: Dependency '{dep_id}' references non-existent task"
                    )

    return errors


def main():
    if len(sys.argv) != 2:
        print("Usage: python validate_output.py <output_file.json>")
        sys.exit(1)

    output_file = Path(sys.argv[1])

    if not output_file.exists():
        print(f"❌ Error: File not found: {output_file}")
        sys.exit(1)

    try:
        with open(output_file, "r") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: Could not read file: {e}")
        sys.exit(1)

    print(f"🔍 Validating output file: {output_file}")
    print("")

    errors = []

    # Validate top-level structure
    required_sections = ["project_info", "task_management", "tasks"]
    for section in required_sections:
        if section not in data:
            errors.append(f"Missing required section: {section}")

    # Validate each section
    if "project_info" in data:
        errors.extend(validate_project_info(data["project_info"]))

    if "task_management" in data:
        errors.extend(validate_task_management(data["task_management"]))

    if "tasks" in data:
        if not isinstance(data["tasks"], list):
            errors.append("tasks must be an array")
        else:
            # Validate each task
            for i, task in enumerate(data["tasks"]):
                errors.extend(validate_task(task, i))

            # Validate dependencies
            errors.extend(validate_dependencies(data["tasks"]))

    # Report results
    if errors:
        print("❌ Validation failed with the following errors:")
        for error in errors:
            print(f"  • {error}")
        print("")
        print(f"Total errors: {len(errors)}")
        sys.exit(1)
    else:
        print("✅ Validation passed!")

        # Show summary statistics
        if "tasks" in data:
            tasks = data["tasks"]
            total_tasks = len(tasks)

            # Count by priority
            priority_counts: Dict[str, int] = {}
            status_counts: Dict[str, int] = {}
            category_counts: Dict[str, int] = {}

            for task in tasks:
                priority = task.get("priority", "UNKNOWN")
                status = task.get("status", "UNKNOWN")
                category = task.get("category", "uncategorized")

                priority_counts[priority] = (
                    priority_counts.get(priority, 0) + 1
                )
                status_counts[status] = status_counts.get(status, 0) + 1
                category_counts[category] = (
                    category_counts.get(category, 0) + 1
                )

            print("")
            print("📊 Summary Statistics:")
            print(f"  • Total tasks: {total_tasks}")
            print("  • By priority:")
            for priority in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
                count = priority_counts.get(priority, 0)
                print(f"    - {priority}: {count}")

            print("  • By status:")
            for status in sorted(status_counts.keys()):
                print(f"    - {status}: {status_counts[status]}")

            print("  • By category:")
            for category in sorted(category_counts.keys()):
                print(f"    - {category}: {category_counts[category]}")

        print("")
        print("🎉 Output file is valid and ready for AI agent execution!")


if __name__ == "__main__":
    main()
