"""Test plan assembly and printing consistency.

Ensures JSON and human output use same data source per UNIFIED GUIDELINES.
"""

import io
import json

import pytest
from ostruct.cli.attachment_processor import ProcessedAttachments
from ostruct.cli.plan_assembly import PlanAssembler
from ostruct.cli.plan_printing import PlanPrinter


def create_test_processed_attachments() -> ProcessedAttachments:
    """Create test processed attachments for consistency testing."""
    from ostruct.cli.attachment_processor import AttachmentSpec

    # Create some test attachment specs
    spec1 = AttachmentSpec(
        alias="data",
        path="test_data.csv",
        targets={"code-interpreter"},
        recursive=False,
        pattern=None,
    )

    spec2 = AttachmentSpec(
        alias="docs",
        path="./documentation",
        targets={"file-search"},
        recursive=True,
        pattern="*.md",
    )

    # Create ProcessedAttachments manually
    processed = ProcessedAttachments()
    processed.alias_map = {"data": spec1, "docs": spec2}
    processed.ci_files = [spec1]
    processed.fs_dirs = [spec2]

    return processed


def test_plan_consistency():
    """Ensure JSON and human output use same data source."""
    # Create test data
    processed_attachments = create_test_processed_attachments()
    variables = {"name": "test", "count": 42}

    # Build execution plan
    plan = PlanAssembler.build_execution_plan(
        processed_attachments=processed_attachments,
        template_path="template.j2",
        schema_path="schema.json",
        variables=variables,
        security_mode="permissive",
        model="gpt-4o",
        cost_estimate={"approx_usd": 0.05, "tokens": 1000},
    )

    # Validate plan structure
    PlanAssembler.validate_plan(plan)

    # Test JSON output
    json_output = json.dumps(plan, indent=2)
    parsed_json = json.loads(json_output)

    # Both should reference same underlying data
    assert parsed_json == plan
    assert parsed_json["type"] == "execution_plan"
    assert parsed_json["schema_version"] == "1.0"
    assert len(parsed_json["attachments"]) == 2
    assert parsed_json["variables"] == variables

    # Test human output captures same data
    output_buffer = io.StringIO()
    PlanPrinter.human(plan, file=output_buffer)
    human_output = output_buffer.getvalue()

    # Human output should contain key information from plan
    assert "execution plan" in human_output.lower()
    assert "template.j2" in human_output
    assert "schema.json" in human_output
    assert "data → code-interpreter" in human_output
    assert "docs → file-search" in human_output
    assert "gpt-4o" in human_output

    # Test summary line
    summary = PlanPrinter.summary_line(plan)
    assert "2 attachments" in summary
    assert "2 variables" in summary
    assert "gpt-4o" in summary


def test_run_summary_consistency():
    """Test run summary consistency between JSON and human output."""
    # Create execution plan first
    processed_attachments = create_test_processed_attachments()
    execution_plan = PlanAssembler.build_execution_plan(
        processed_attachments=processed_attachments,
        template_path="template.j2",
        schema_path="schema.json",
        variables={"test": "value"},
        model="gpt-4o",
    )

    # Build run summary
    run_summary = PlanAssembler.build_run_summary(
        execution_plan=execution_plan,
        result={"status": "completed", "output": "success"},
        execution_time=2.5,
        success=True,
        cost_breakdown={
            "total": 0.08,
            "input_cost": 0.05,
            "output_cost": 0.03,
        },
    )

    # Validate summary structure
    PlanAssembler.validate_plan(run_summary)

    # Test JSON consistency
    json_output = json.dumps(run_summary, indent=2)
    parsed_json = json.loads(json_output)
    assert parsed_json == run_summary
    assert parsed_json["type"] == "run_summary"
    assert parsed_json["success"] is True
    assert parsed_json["execution_time"] == 2.5

    # Test human output
    output_buffer = io.StringIO()
    PlanPrinter.human(run_summary, file=output_buffer)
    human_output = output_buffer.getvalue()

    assert "run summary" in human_output.lower()
    assert "Success" in human_output
    assert "2.50s" in human_output
    assert "$0.0800" in human_output

    # Test summary line
    summary = PlanPrinter.summary_line(run_summary)
    assert "Success in 2.50s" in summary


def test_plan_validation():
    """Test plan structure validation."""
    # Valid plan should pass
    valid_plan = {
        "schema_version": "1.0",
        "type": "execution_plan",
        "timestamp": 1234567890.0,
    }
    assert PlanAssembler.validate_plan(valid_plan) is True

    # Missing required field should fail
    invalid_plan = {
        "schema_version": "1.0",
        "type": "execution_plan",
        # Missing timestamp
    }

    with pytest.raises(ValueError, match="Missing required field: timestamp"):
        PlanAssembler.validate_plan(invalid_plan)

    # Invalid type should fail
    invalid_type_plan = {
        "schema_version": "1.0",
        "type": "invalid_type",
        "timestamp": 1234567890.0,
    }

    with pytest.raises(ValueError, match="Invalid plan type: invalid_type"):
        PlanAssembler.validate_plan(invalid_type_plan)

    # Invalid schema version should fail
    invalid_version_plan = {
        "schema_version": "2.0",
        "type": "execution_plan",
        "timestamp": 1234567890.0,
    }

    with pytest.raises(ValueError, match="Unsupported schema version: 2.0"):
        PlanAssembler.validate_plan(invalid_version_plan)


def test_output_format_validation():
    """Test output format validation in PlanPrinter."""
    plan = {
        "schema_version": "1.0",
        "type": "execution_plan",
        "timestamp": 1234567890.0,
    }

    # Valid formats should work
    output_buffer = io.StringIO()
    PlanPrinter.validate_and_print(plan, "human", output_buffer)
    assert len(output_buffer.getvalue()) > 0

    output_buffer = io.StringIO()
    PlanPrinter.validate_and_print(plan, "json", output_buffer)
    json_content = output_buffer.getvalue()
    assert len(json_content) > 0
    assert json.loads(json_content) == plan

    # Invalid format should fail
    with pytest.raises(ValueError, match="Unsupported output format: invalid"):
        PlanPrinter.validate_and_print(plan, "invalid")
