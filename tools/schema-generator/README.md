# Schema Generator

> **Tool Type:** Meta-tool for ostruct development
> **Model:** GPT-4.1 with iterative refinement
> **Cost:** ~$0.05-0.25 per schema generation (depending on complexity and refinement iterations)

## Overview

The Schema Generator is a development tool that automatically creates JSON schemas for ostruct prompt templates. It analyzes your Jinja2 templates and generates OpenAI Structured Outputs-compliant schemas with validation and iterative refinement.

**Key Features:**

- **Automated Schema Generation**: AI-powered analysis of template structure and output expectations
- **OpenAI Compliance**: Ensures compatibility with OpenAI's Structured Outputs requirements
- **Iterative Refinement**: Automatically improves schemas based on validation feedback
- **Multiple Validators**: Supports ajv-cli, jsonschema, and custom validators
- **Quality Assessment**: Provides confidence scores and improvement suggestions

## Installation & Prerequisites

```bash
# Required dependencies
ostruct --version    # ostruct CLI must be installed and accessible on PATH
jq --version        # JSON processor (auto-installed via ensure_jq.sh)

# Recommended JSON Schema validator
npm install -g ajv-cli

# Alternative validator
pip install jsonschema
```

## Usage

```bash
./run.sh [OPTIONS] TARGET_TEMPLATE
```

### Arguments

| Argument | Description |
|----------|-------------|
| `TARGET_TEMPLATE` | **Required**: Path to your Jinja2 template file |

### Options

| Option | Description |
|--------|-------------|
| `-o, --output FILE` | Output file for the schema (default: `<template-name>.json`) |
| `--verbose` | Enable verbose logging (INFO level) |
| `--debug` | Enable debug logging (DEBUG level, passes --debug to ostruct) |
| `-v, --validator-cmd CMD` | JSON Schema validator command (default: ajv) |
| `-r, --max-retries NUM` | Maximum refinement retries (default: 3) |
| `-t, --temp-dir DIR` | Temporary directory for intermediate files |
| `-h, --help` | Show help message |

### Examples

```bash
# Generate schema for a template (saves to template-name.json)
./run.sh my_template.j2

# Save to specific output file
./run.sh -o custom_schema.json my_template.j2

# Enable verbose logging
./run.sh --verbose my_template.j2

# Enable debug mode (includes ostruct debug output)
./run.sh --debug my_template.j2

# Use alternative validator with more retries
./run.sh -v jsonschema -r 5 complex_template.j2

# Use custom temporary directory
./run.sh -t ./debug_temp my_template.j2
```

## How It Works

The generator follows a multi-step process with iterative refinement:

### 1. Template Analysis

- Analyzes your Jinja2 template for output structure hints
- Identifies placeholders, variables, and expected data types
- Determines the complexity and scope of the expected output

### 2. Initial Schema Generation

- Uses GPT-4.1 to generate an initial JSON schema
- Applies OpenAI Structured Outputs compliance rules
- Includes comprehensive property descriptions and type definitions

### 3. Validation & Quality Assessment

- Validates the schema using your chosen validator (ajv-cli, jsonschema, etc.)
- Checks for JSON Schema compliance and syntax errors
- Evaluates schema quality, completeness, and confidence scores

### 4. Iterative Refinement

- If validation fails or quality is low, analyzes the specific issues
- Refines the schema to address validation errors and quality concerns
- Repeats up to the maximum retry limit until a valid schema is produced

### 5. Final Output

- Provides the validated schema with metadata
- Includes generation details, quality assessment, and compliance verification
- Saves to the specified output file (or `<template-name>.json` by default)

## OpenAI Structured Outputs Compliance

Generated schemas automatically adhere to current OpenAI requirements:

✅ **Required Compliance Features:**

- All fields must be required (no optional fields allowed)
- `additionalProperties: false` on all objects
- Root type must be object (no arrays, primitives, or unions at root)
- Maximum 5,000 object properties with up to 5 levels of nesting
- Supported types only: string, number, boolean, integer, object, array, enum, anyOf
- `$defs` and recursive schemas are supported

❌ **Unsupported Features (Automatically Avoided):**

- `minLength`, `maxLength`, `pattern`, `format` constraints
- `minimum`, `maximum` numeric constraints
- `anyOf`, `oneOf`, `allOf` at root level
- `not`, `if/then/else` conditional schemas

## Output Format

The generator produces comprehensive metadata along with the schema:

```json
{
  "generated_schema": "{\"type\":\"object\",...}",  // JSON-escaped schema string
  "input_template_digest": "sha256_hash",           // Template fingerprint
  "schema_generation_model_id": "gpt-4.1",         // AI model used
  "generation_timestamp_utc": "2024-01-01T12:00:00Z",
  "identified_placeholders": ["var1", "var2"],     // Found template variables
  "inferred_property_details": [...],              // Type inference details
  "schema_quality_assessment": {
    "confidence_score": 0.85,                      // 0-1 confidence rating
    "completeness_notes": "Schema covers all expected outputs",
    "ambiguity_warnings": [],                      // Potential issues
    "improvement_suggestions": [...]               // Recommendations
  },
  "best_practices_adherence_check": {
    "has_root_object": true,
    "uses_additional_properties_false": true,
    "all_properties_required": true,
    "uses_supported_types_only": true,
    "avoids_unsupported_keywords": true,
    "has_appropriate_constraints": true,
    "compliance_notes": []
  }
}
```

## Example Workflow

```bash
# 1. Create your ostruct template
cat > extract_data.j2 << 'EOF'
Extract the following information from the text:
- Name of the person
- Their age (if mentioned)
- List of hobbies or interests
- Email address (if provided)

Return the data in a structured JSON format.

Text: {{ input_text }}
EOF

# 2. Generate the schema
./run.sh extract_data.j2
# Creates: extract_data.json

# 3. Use with ostruct
ostruct run extract_data.j2 extract_data.json \
  -V input_text="John Doe, 30, loves hiking and photography. Contact: john@example.com"
```

## Directory Structure

```
tools/schema-generator/
├── README.md                           # This documentation
├── run.sh                              # Main generator script
├── src/
│   ├── generate_schema_from_template.j2 # Initial generation prompt
│   ├── refine_schema_from_feedback.j2   # Refinement prompt
│   └── schema_generator_output.json     # Output schema definition
├── scripts/                            # (empty - no additional scripts)
└── test/                              # Example templates for testing
    └── (test templates)
```

## Advanced Usage

### Custom Validators

The generator supports different JSON Schema validators:

```bash
# Using ajv-cli (default, most comprehensive)
./run.sh my_template.j2

# Using Python jsonschema module
./run.sh -v jsonschema my_template.j2

# Using a custom validator command
./run.sh -v "/path/to/custom/validator" my_template.j2
```

### CI/CD Integration

```bash
# Add schema generation to your CI pipeline
cd tools/schema-generator

# Generate schema and check for success
./run.sh --verbose src/templates/main.j2
if [ $? -eq 0 ]; then
  echo "✅ Schema generation successful"
  # Copy generated schema to appropriate location
  cp main.json ../schemas/
else
  echo "❌ Schema generation failed"
  exit 1
fi
```

### Debugging and Troubleshooting

```bash
# Enable debug mode for detailed logging
./run.sh --debug my_template.j2

# Use custom temp directory to inspect intermediate files
mkdir debug_temp
./run.sh -t debug_temp my_template.j2
ls debug_temp/  # Examine intermediate files

# Increase retry limit for complex templates
./run.sh -r 10 complex_template.j2
```

## Troubleshooting

### Common Issues

1. **"ostruct not found"**

   ```bash
   # Ensure ostruct is installed and in PATH
   ostruct --version
   pip install ostruct-cli  # if needed
   ```

2. **"jq not found"**

   ```bash
   # The tool automatically tries to install jq
   # If that fails, install manually:
   brew install jq          # macOS
   sudo apt install jq      # Ubuntu/Debian
   sudo yum install jq      # RHEL/CentOS
   ```

3. **"JSON Schema validator not found"**

   ```bash
   # Install recommended validator
   npm install -g ajv-cli

   # Or use alternative
   pip install jsonschema
   ./run.sh -v jsonschema my_template.j2
   ```

4. **"Schema generation failed after X retries"**

   ```bash
   # Enable debug mode to see detailed errors
   ./run.sh --debug my_template.j2

   # Increase retry limit
   ./run.sh -r 10 my_template.j2

   # Simplify your template if it's too complex
   ```

5. **"Template file not found"**

   ```bash
   # Check file path and permissions
   ls -la my_template.j2

   # Use absolute path if needed
   ./run.sh /full/path/to/template.j2
   ```

### Quality Issues

If generated schemas have low confidence scores:

1. **Make templates more explicit** about expected output structure
2. **Add examples** in template comments or descriptions
3. **Use clear variable names** that indicate data types
4. **Include output format instructions** in your template

### Getting Help

- Use `./run.sh --help` for usage information
- Enable `--debug` for detailed error messages and ostruct debug output
- Check temporary files with `-t custom_temp_dir` for debugging
- Review the generated schema metadata for quality insights

## Contributing

This tool is part of the ostruct project's development infrastructure. To contribute:

1. Test with various template types and complexity levels
2. Report issues with specific templates that cause generation failures
3. Suggest improvements to generation prompts in `src/`
4. Add support for additional JSON Schema validators

## Related Tools

- **Template Analyzer** (`tools/template-analyzer/`): Analyzes templates and schemas for issues and optimization opportunities
- **ostruct CLI**: The main ostruct command-line interface
- **ostruct Documentation**: <https://ostruct.readthedocs.io/>
