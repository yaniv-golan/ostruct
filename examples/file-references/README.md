# File Reference Examples

This directory contains examples of ostruct's **optional** file reference system. File references provide automatic XML appendix generation, but you can always access files manually in templates if you prefer custom formatting.

## Two Approaches to File Access

### 1. Automatic File References (These Examples)

Uses `file_ref()` for automatic XML appendix:

```jinja2
Analyze the code in {{ file_ref("source") }}.
```

**Pros:** Clean template syntax, automatic XML formatting, files appear at end of prompt
**Cons:** Less control over file placement and formatting

### 2. Manual File Access (Alternative)

Access files directly with full control:

```jinja2
## Source Code Analysis

{% for file in source %}
### {{ file.name }}
```{{ file.name.split('.')[-1] }}
{{ file.content }}
```

{% endfor %}

```

**Pros:** Full control over formatting and placement, custom styling
**Cons:** More template code, manual file iteration

### 3. Mixed Approach

Combine both for maximum flexibility:

```jinja2
{# Quick analysis with manual formatting #}
## Key Configuration
The debug mode is: {{ config.content | from_yaml | attr('debug') }}

{# Supporting files via XML appendix #}
For complete reference, see {{ file_ref("source") }} and {{ file_ref("config") }}.
```

## File Placement Strategy

**Important:** LLMs pay more attention to content at the end of prompts. Choose your approach based on how the files should be processed:

- **Immediate analysis needed** → Manual inclusion where relevant
- **Reference/supporting material** → Automatic XML appendix at end
- **Both** → Mixed approach

## Examples in This Directory

### Automatic File Reference Examples

These examples use `file_ref()` for automatic XML appendix:

- **`security-audit.j2`** - Security analysis with file references
- **`code-review.j2`** - Code review using file references
- **`data-analysis.j2`** - Data analysis with multiple file types

### Manual File Access Example

- **`manual-code-review.j2`** - Code review using direct file access (no `file_ref()`)

Compare `code-review.j2` vs `manual-code-review.j2` to see the difference between automatic XML appendix and manual file formatting.

All automatic examples can be converted to manual file access by replacing `{{ file_ref("alias") }}` with direct file iteration.

## Overview

The `file_ref()` function allows you to cleanly reference file collections attached via CLI flags. Referenced files automatically appear in an XML appendix with structured content.

## Basic Usage

1. **Attach files with aliases:**

   ```bash
   ostruct run template.j2 schema.json \
     --dir source src/ \
     --file config config.yaml
   ```

2. **Reference in templates:**

   ```jinja2
   Review the code in {{ file_ref("source") }}.
   Check the config in {{ file_ref("config") }}.
   ```

3. **Get structured output:**
   - Template renders with `<source>` and `<config>` references
   - XML appendix contains actual file contents

## Examples

### Security Audit (`security-audit.j2`)

Demonstrates security analysis workflow:

```bash
# Run security audit
ostruct run security-audit.j2 security-audit-schema.json \
  --dir source /path/to/codebase \
  --dir config /path/to/configs
```

**Features:**

- Multi-section analysis structure
- Clear deliverables specification
- References to specific file collections

### Data Analysis

```jinja2
# Data Analysis Request

Analyze the datasets in {{ file_ref("data") }}.
Compare with reference data in {{ file_ref("baseline") }}.

## Analysis Tasks
1. Descriptive statistics for <data>
2. Comparison with <baseline>
3. Trend analysis and insights
```

```bash
# Run data analysis
ostruct run data-analysis.j2 analysis-schema.json \
  --collect data @dataset-files.txt \
  --file baseline reference.csv
```

### Code Review

```jinja2
# Code Review Request

Please review:
- Implementation: {{ file_ref("source") }}
- Tests: {{ file_ref("tests") }}
- Documentation: {{ file_ref("docs") }}

Focus on maintainability and best practices.
```

```bash
# Run code review
ostruct run code-review.j2 review-schema.json \
  --dir source src/ \
  --dir tests tests/ \
  --dir docs docs/
```

## Best Practices

1. **Use descriptive aliases**

   ```bash
   --dir user-service src/services/user/  # Good
   --dir src src/                         # Less clear
   ```

2. **Reference only what you need**

   ```jinja2
   # Only reference files mentioned in template
   {{ file_ref("source") }}  # ✓ Used in analysis
   # Don't reference unused aliases
   ```

3. **Structure your templates**

   ```jinja2
   # Clear sections help AI understand context
   ## Source Code Analysis
   Review {{ file_ref("source") }}.

   ## Configuration Review
   Check {{ file_ref("config") }}.
   ```

4. **Test with debug mode**

   ```bash
   ostruct run template.j2 schema.json --template-debug
   ```

## File Attachment Types

### Single Files (`--file`)

```bash
--file config config.yaml
```

- Creates `<file>` element in XML
- Use for individual configuration files

### Directories (`--dir`)

```bash
--dir source src/
```

- Creates `<dir>` element in XML
- Use for code directories, documentation folders

### Collections (`--collect`)

```bash
--collect datasets @file-list.txt
```

- Creates `<collection>` element in XML
- Use for curated file lists, related documents

## Troubleshooting

If file references aren't working:

- Check that file aliases match your CLI attachments
- Verify files exist and are accessible
- Use the exact alias names from your CLI commands

## Schema Files

Each example includes a corresponding JSON schema file for structured output. The schemas define the expected response format from the AI model.

Example schema structure:

```json
{
  "type": "object",
  "properties": {
    "summary": {"type": "string"},
    "findings": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "issue": {"type": "string"},
          "severity": {"type": "string"},
          "file_reference": {"type": "string"}
        }
      }
    }
  }
}
```
