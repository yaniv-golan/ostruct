---
title: Insert Content
description: Insert content at specific locations in a file for targeted fixes
is_virtual_tool: true
base_command: bash
---

# Insert Content

A precision tool for inserting content at specific locations within an existing file, perfect for surgical fixes during replanning.

## When to Use

* To fix missing tables, images, or sections identified during validation
* When you need to insert extracted content at a specific location
* For targeted repairs without reprocessing the entire document
* To merge partial conversion results at precise positions

## When NOT to Use

* For simple appending (use standard redirection instead)
* When the entire document needs reprocessing
* For complex multi-file merges

## Basic Usage

```bash
bash $PROJECT_ROOT/scripts/insert_content.sh {{TARGET_FILE}} {{CONTENT_FILE}} [options]
```

## Options

* `--after "pattern"` - Insert content after the first line matching pattern
* `--before "pattern"` - Insert content before the first line matching pattern
* `--line N` - Insert content at line number N
* `--append` - Append at end (default behavior)

## Examples

### Insert missing table after a section

```bash
bash $PROJECT_ROOT/scripts/insert_content.sh {{OUTPUT_FILE}} $TEMP_DIR/table.md --after "## Results"
```

### Insert image at specific line

```bash
bash $PROJECT_ROOT/scripts/insert_content.sh {{OUTPUT_FILE}} $TEMP_DIR/figure.md --line 150
```

### Fix missing content before conclusion

```bash
bash $PROJECT_ROOT/scripts/insert_content.sh {{OUTPUT_FILE}} $TEMP_DIR/missing_section.md --before "## Conclusion"
```

## Planner Guidance

This tool is ideal for replan scenarios where validation identified specific missing elements. Use pattern matching for robust insertion points that won't break if line numbers change.

## Output

Updates the target file in-place with the inserted content, adding appropriate spacing around the insertion.
