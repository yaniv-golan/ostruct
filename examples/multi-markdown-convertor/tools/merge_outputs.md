---
title: Merge Outputs
description: Merge text and media outputs into final markdown document
is_virtual_tool: true
base_command: bash
---

# Merge Outputs

A tool for intelligently merging extracted text content with media files to create a complete markdown document.

## When to Use

* After extracting text and images separately (e.g., with pdftotext + pdfimages)
* When you need to combine multiple extraction outputs into a single document
* To append extracted images to the end of a text document

## When NOT to Use

* When a single tool already produces complete output
* For merging complex structured data (use specialized tools instead)

## Basic Usage

```bash
bash $PROJECT_ROOT/scripts/merge_outputs.sh {{INPUT_FILE}} {{MEDIA_DIR}} {{OUTPUT_FILE}}
```

## Parameters

* `{{INPUT_FILE}}` - Text file to use as base content
* `{{MEDIA_DIR}}` - Directory containing extracted images
* `{{OUTPUT_FILE}}` - Final merged markdown output

## Examples

### Merge PDF text and images

```bash
# After extracting text and images separately
bash $PROJECT_ROOT/scripts/merge_outputs.sh $TEMP_DIR/extracted.txt $TEMP_DIR/images/ {{OUTPUT_FILE}}
```

## Output

Creates a markdown file with:

* Original text content
* Appended "## Extracted Images" section
* All images from media directory with proper markdown syntax

## Integration Notes

This tool is designed to work as the final step in multi-tool pipelines where content has been extracted by different tools and needs to be combined.
