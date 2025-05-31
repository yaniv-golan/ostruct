# Meta-Schema Generator for ostruct

This utility automatically generates and validates JSON schemas for your ostruct prompt templates, ensuring compatibility with OpenAI's Structured Outputs feature and JSON Schema best practices.

## Overview

The Meta-Schema Generator analyzes your Jinja2 prompt templates and creates corresponding JSON schemas that define the expected output structure. It includes:

- **Automated schema generation** from template analysis
- **Validation** using standard JSON Schema validators
- **Iterative refinement** based on validation feedback
- **OpenAI Structured Outputs compliance** checking
- **Best practices enforcement** for schema quality

## Quick Start

```bash
# Generate schema for a template
./scripts/generate_and_validate_schema.sh my_template.j2

# Save output to file
./scripts/generate_and_validate_schema.sh -o schema.json my_template.j2

# Use custom validator and increase retries
./scripts/generate_and_validate_schema.sh -v jsonschema -r 5 complex_template.j2
```

## Prerequisites

Before using this utility, ensure you have:

### **Required Dependencies**

1. **ostruct** - Installed and accessible in your PATH
   ```bash
   # Via poetry (development)
   poetry install

   # Or direct installation
   pip install ostruct-cli
   ```

2. **jq** - JSON processor for parsing outputs
   ```bash
   # macOS
   brew install jq

   # Ubuntu/Debian
   sudo apt install jq

   # RHEL/CentOS/Fedora
   sudo yum install jq  # or dnf install jq

   # Windows (via Chocolatey)
   choco install jq
   ```

3. **JSON Schema Validator** - One of:
   - **ajv-cli** (recommended): `npm install -g ajv-cli`
   - **jsonschema** (Python): `pip install jsonschema`

### **Usually Pre-installed (but required)**

4. **SHA256 utility** - For template hashing (one of):
   - `sha256sum` (Linux/WSL) - usually pre-installed
   - `shasum` (macOS/BSD) - usually pre-installed

5. **bc** - Calculator for confidence score comparisons
   - Usually pre-installed on Unix systems
   - Windows: Available via WSL or Git Bash

### **Optional**

6. **poetry** - For development environments
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

## Usage

```bash
./scripts/generate_and_validate_schema.sh [OPTIONS] TARGET_TEMPLATE

ARGUMENTS:
    TARGET_TEMPLATE     Path to your Jinja2 template file

OPTIONS:
    -o, --output FILE          Output file for the final schema (default: stdout)
    -s, --ostruct-cmd CMD      Path to ostruct executable (default: ostruct)
    -v, --validator-cmd CMD    JSON Schema validator command (default: ajv)
    -r, --max-retries NUM      Maximum refinement attempts (default: 3)
    -t, --temp-dir DIR         Temporary directory for intermediate files
    -h, --help                 Show help message
```

## How It Works

The utility follows a multi-step process:

### 1. Initial Analysis
- Analyzes your template for output structure hints
- Identifies placeholders and expected data types
- Generates an initial JSON schema using AI

### 2. Validation
- Validates the generated schema using external tools
- Checks for JSON Schema compliance
- Verifies OpenAI Structured Outputs compatibility

### 3. Iterative Refinement
- If validation fails, analyzes the errors
- Refines the schema to address specific issues
- Repeats until valid or max retries reached

### 4. Output
- Provides the final validated schema
- Includes quality assessment and suggestions
- Documents compliance with best practices

## Example Workflow

```bash
# 1. Create your ostruct template
cat > extract_data.j2 << 'EOF'
Extract the following information from the text:
- Name of the person
- Their age (if mentioned)
- List of hobbies or interests
- Email address (if provided)

Return the data in a structured format.

Text: {{ input_text }}
EOF

# 2. Generate the schema
./scripts/generate_and_validate_schema.sh -o data_schema.json extract_data.j2

# 3. Use with ostruct
ostruct run extract_data.j2 data_schema.json -st "input_text=John Doe, 30, loves hiking and photography. Contact: john@example.com"
```

## Directory Structure

```
examples/meta-schema-generator/
├── README.md                           # This documentation
├── scripts/
│   └── generate_and_validate_schema.sh # Main utility script
├── prompts/
│   ├── generate_schema_from_template.j2 # Initial generation prompt
│   └── refine_schema_from_feedback.j2   # Refinement prompt
├── schemas/
│   └── schema_generator_output.json     # Meta-schema definition
└── test_target_templates/              # Example templates for testing
    ├── simple_extraction.j2
    ├── data_summarization.j2
    └── complex_analysis.j2
```

## Advanced Usage

### Custom Validators

The utility supports different JSON Schema validators:

```bash
# Using ajv-cli (default, most comprehensive)
./scripts/generate_and_validate_schema.sh my_template.j2

# Using Python jsonschema
./scripts/generate_and_validate_schema.sh -v jsonschema my_template.j2

# Using a custom validator
./scripts/generate_and_validate_schema.sh -v "/path/to/my/validator" my_template.j2
```

### Debugging and Troubleshooting

1. **Check Prerequisites**:
   ```bash
   ostruct --version
   jq --version
   ajv --help  # or your chosen validator
   ```

2. **Use Temporary Directory for Debugging**:
   ```bash
   mkdir debug_temp
   ./scripts/generate_and_validate_schema.sh -t debug_temp my_template.j2
   # Inspect files in debug_temp/ to see intermediate steps
   ```

3. **Increase Verbosity**:
   ```bash
   # The script shows colored status messages for each step
   # Failed validations will display the specific errors
   ```

## OpenAI Structured Outputs Compliance

Generated schemas automatically adhere to OpenAI's requirements:

- ✅ Root object type only
- ✅ `additionalProperties: false` on all objects
- ✅ All properties in `required` array
- ✅ Optional fields use union types (`["string", "null"]`)
- ✅ Supported types only (string, number, integer, boolean, array, object, null)
- ✅ Avoids unsupported keywords (`anyOf`, `oneOf`, `$ref`, etc.)

## Output Format

The utility generates comprehensive metadata along with the schema:

```json
{
  "generated_schema": "...",           // The actual JSON schema
  "input_template_digest": "...",      // SHA256 hash of your template
  "schema_generation_model_id": "...", // AI model used
  "generation_timestamp_utc": "...",   // When generated
  "identified_placeholders": [...],    // Found template variables
  "inferred_property_details": [...],  // Type inference details
  "schema_quality_assessment": {...},  // Quality and confidence metrics
  "best_practices_adherence_check": {...} // Compliance verification
}
```

## Troubleshooting

### Common Issues

1. **"Missing required dependencies"**
   - Follow the installation instructions shown in the error message
   - See the Prerequisites section above for detailed platform-specific instructions
   - Ensure all utilities are in your system PATH

2. **"ostruct command failed"**
   - Check that ostruct is installed: `ostruct --version`
   - Verify your template syntax is valid Jinja2
   - In development environments, ensure poetry dependencies are installed

3. **"JSON Schema validator not found"**
   - Install ajv-cli: `npm install -g ajv-cli` (recommended)
   - Or use alternative: `pip install jsonschema`
   - Or use custom validator: `--validator-cmd your-validator`

4. **"No SHA256 utility found"**
   - Usually pre-installed on most systems
   - Linux: `sudo apt install coreutils`
   - Windows: Use WSL, Git Bash, or install via package manager

5. **"Schema validation failed after X retries"**
   - Check the validation errors in the output
   - Simplify your template if it's too complex
   - Manually review and adjust if needed

### Getting Help

- Check template syntax with ostruct directly
- Examine intermediate files in the temp directory
- Review validation error messages for specific issues
- Consult the ostruct documentation for template best practices

## Contributing

This utility is part of the ostruct project. To contribute:

1. Test with various template types
2. Report issues with specific templates
3. Suggest improvements to the meta-prompts
4. Add support for additional validators

## License

This utility follows the same license as the ostruct project.
