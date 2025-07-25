"""Integration tests for JSON output from ostruct run command.

These tests verify that the JSON output schema remains consistent
and contains the expected structure for different scenarios.
"""

import json

from ostruct.cli.utils.json_output import JSONOutputHandler


class TestJSONOutputIntegration:
    """Integration tests for JSON output schema consistency."""

    def test_single_response_json_schema_structure(self) -> None:
        """Test JSON output structure for single response using JSONOutputHandler."""
        handler = JSONOutputHandler(indent=2)

        # Simulate a single model response (what would come from OpenAI)
        single_response_data = {
            "result": "Processed content from model",
            "confidence": 0.95,
            "reasoning": "Based on the input analysis...",
        }

        # This is how runner.py handles single responses
        json_output = handler.to_json(single_response_data)

        # Verify it's valid JSON and has expected structure
        parsed = json.loads(json_output)
        assert isinstance(
            parsed, dict
        ), "Single response should be a dictionary"
        assert "result" in parsed
        assert "confidence" in parsed
        assert parsed["result"] == "Processed content from model"
        assert parsed["confidence"] == 0.95

        # Verify it's properly formatted
        assert "\n" in json_output  # Should be indented
        assert "  " in json_output  # Should have 2-space indentation

    def test_multiple_response_json_schema_structure(self) -> None:
        """Test JSON output structure for multiple responses using JSONOutputHandler."""
        handler = JSONOutputHandler(indent=2)

        # Simulate multiple model responses (what would come from --iterations)
        multiple_responses_data = [
            {
                "result": "First analysis result",
                "confidence": 0.9,
                "iteration": 1,
            },
            {
                "result": "Second analysis result",
                "confidence": 0.85,
                "iteration": 2,
            },
        ]

        # This is how runner.py handles multiple responses
        json_output = handler.to_json(multiple_responses_data)

        # Verify it's valid JSON and has expected structure
        parsed = json.loads(json_output)
        assert isinstance(
            parsed, list
        ), "Multiple responses should be an array"
        assert len(parsed) == 2

        # Verify each response has expected structure
        for i, response in enumerate(parsed):
            assert isinstance(
                response, dict
            ), f"Response {i} should be a dictionary"
            assert "result" in response, f"Response {i} missing 'result' field"
            assert (
                "confidence" in response
            ), f"Response {i} missing 'confidence' field"
            assert (
                "iteration" in response
            ), f"Response {i} missing 'iteration' field"

        # Verify specific content
        assert parsed[0]["result"] == "First analysis result"
        assert parsed[0]["confidence"] == 0.9
        assert parsed[1]["result"] == "Second analysis result"
        assert parsed[1]["confidence"] == 0.85

        # Verify it's properly formatted
        assert "\n" in json_output  # Should be indented
        assert "  " in json_output  # Should have 2-space indentation

    def test_json_output_handler_type_flexibility(self) -> None:
        """Test that JSONOutputHandler can handle both dict and list inputs."""
        handler = JSONOutputHandler()

        # Test with dictionary (single response)
        dict_data = {"key": "value", "number": 42}
        dict_output = handler.to_json(dict_data)
        assert json.loads(dict_output) == dict_data

        # Test with list (multiple responses)
        list_data = [{"id": 1, "value": "first"}, {"id": 2, "value": "second"}]
        list_output = handler.to_json(list_data)
        assert json.loads(list_output) == list_data

        # Test with nested structures
        complex_data = {
            "responses": [
                {"result": "test", "metadata": {"tokens": 100}},
                {"result": "test2", "metadata": {"tokens": 150}},
            ],
            "summary": {"total": 2, "avg_tokens": 125},
        }
        complex_output = handler.to_json(complex_data)
        assert json.loads(complex_output) == complex_data

    def test_json_output_schema_documentation(self) -> None:
        """Document the expected JSON output schema for reference."""
        # This test serves as documentation for the expected JSON schema

        single_response_schema = {
            "description": "Single response from ostruct run --output-file output.json",
            "type": "object",
            "note": "Raw model response JSON - structure depends on the user-provided schema.json file",
            "example": {
                "result": "Analysis complete",
                "confidence": 0.95,
                "additional_fields": "depend on schema.json",
            },
        }

        multiple_response_schema = {
            "description": "Multiple responses from ostruct run --iterations N --output-file output.json",
            "type": "array",
            "items": {
                "type": "object",
                "note": "Each item is a raw model response - structure depends on schema.json",
            },
            "example": [
                {"result": "First analysis", "confidence": 0.9},
                {"result": "Second analysis", "confidence": 0.85},
            ],
        }

        # Key points about the JSON output:
        # 1. Single response: Direct model output as JSON object
        # 2. Multiple responses: Array of model outputs
        # 3. Structure depends entirely on user's schema.json file
        # 4. No wrapper object - just the raw model response(s)
        # 5. Indented with 2 spaces when using --output-file

        # These schemas are for documentation purposes
        assert single_response_schema["type"] == "object"
        assert multiple_response_schema["type"] == "array"
        assert "example" in single_response_schema
        assert "example" in multiple_response_schema

    def test_json_output_consistency_with_runner(self) -> None:
        """Test that our JSONOutputHandler matches what runner.py produces."""
        handler = JSONOutputHandler(indent=2)

        # Simulate what runner.py does for single response
        mock_response = type(
            "MockResponse",
            (),
            {
                "model_dump_json": lambda self, indent: json.dumps(
                    {"analysis": "Complete", "score": 8.5}, indent=indent
                )
            },
        )()

        # Single response: runner.py calls response.model_dump_json(indent=2)
        single_output_runner_style = mock_response.model_dump_json(indent=2)

        # Single response: our JSONOutputHandler approach
        single_data = {"analysis": "Complete", "score": 8.5}
        single_output_handler = handler.to_json(single_data)

        # Both should produce equivalent JSON
        assert json.loads(single_output_runner_style) == json.loads(
            single_output_handler
        )

        # Multiple responses: runner.py uses JSONOutputHandler.to_json()
        multiple_data = [
            {"analysis": "First", "score": 7.5},
            {"analysis": "Second", "score": 8.0},
        ]
        multiple_output = handler.to_json(multiple_data)

        # Should be valid JSON array
        parsed_multiple = json.loads(multiple_output)
        assert isinstance(parsed_multiple, list)
        assert len(parsed_multiple) == 2
        assert parsed_multiple[0]["analysis"] == "First"
        assert parsed_multiple[1]["analysis"] == "Second"
