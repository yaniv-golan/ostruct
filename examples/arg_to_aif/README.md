# Natural Language → AIF (Argument Interchange Format)

This example demonstrates converting natural language arguments into **AIFdb-compatible JSON** format.

## What is AIF?

The **Argument Interchange Format (AIF)** is a standard for representing argument structures in a machine-readable format. It consists of:

- **Nodes**: Information (I), Rule Application (RA), Conflict Application (CA), Preference Application (PA)
- **Edges**: Directed connections between nodes
- **AIFdb Format**: A specific JSON schema used by AIF tools and applications

## Key Features

✅ **AIFdb Compatible**: Generates JSON that follows AIFdb standards
✅ **OpenAI Structured Output**: Uses simplified schema for reliable generation
✅ **Real Text Extraction**: Extracts actual claims from input text, not placeholders
✅ **Multiple Output Formats**: Console display and direct file generation

## Files

- `prompt.j2` - Jinja2 template for AIF graph extraction with AIFdb specification
- `schema.json` - JSON Schema for AIFdb-compatible format (simplified for OpenAI structured output)
- `texts/` - Sample argumentative texts for analysis
- `Makefile` - Convenience commands for running examples

## Usage

### Basic Usage

```bash
# Run with default text (Paradox of the Court)
make run

# Run with specific text
make run TEXT=aint_i_a_woman_by.txt

# Generate AIF file directly
make generate

# Generate AIF file for specific text
make generate TEXT=yes_virgina_there_is_a_santa_claus.txt

# Generate AIF files for all texts
make generate-all
```

### Direct ostruct Usage

```bash
# Console output
ostruct run prompt.j2 schema.json --fta argument_text texts/paradox_of_the_court.txt

# Save to file
ostruct run prompt.j2 schema.json --fta argument_text texts/paradox_of_the_court.txt --output-file output.aif.json
```

### Available Texts

- **paradox_of_the_court.txt** - Classic logical paradox by Protagoras and Euathlus
- **aint_i_a_woman_by.txt** - Sojourner Truth's famous speech (1851)
- **yes_virgina_there_is_a_santa_claus.txt** - Francis Pharcellus Church's editorial (1897)
- **a_letter_to_a_royal_academy_about_farting.txt** - Benjamin Franklin's satirical essay (1781)

## Technical Implementation

### Schema Requirements

The schema follows OpenAI's structured output requirements:

- All properties must be in `required` arrays
- No advanced JSON Schema features (`oneOf`, `anyOf`, `$ref`, etc.)
- Simple type definitions only
- No optional fields (use empty strings instead)

### Output Format

Generated JSON includes:

```json
{
  "AIF": {
    "version": "1.0",
    "analyst": "AI Assistant",
    "created": "2024-01-01T00:00:00Z"
  },
  "nodes": [...],
  "edges": [...],
  "locutions": [],
  "participants": []
}
```

## Example Output

The Paradox of the Court generates an argument graph showing:

- **Protagoras' Argument**: Euathlus must pay regardless of case outcome
- **Euathlus' Counter-Argument**: He owes nothing regardless of case outcome
- **Conflict Node**: Representing the logical contradiction between both arguments

This demonstrates how AIF can represent complex argumentative structures with competing reasoning patterns.
