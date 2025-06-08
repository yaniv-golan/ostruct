---
tool: ostruct-enhance
kind: semantic-enhancer
base_command: ostruct
is_virtual_tool: true
tool_min_version: "0.8.8"
tool_version_check: "ostruct --version"
recommended_output_format: markdown
---

# ostruct-enhance - AI-Powered Semantic Structure Enhancement

## Overview

ostruct-enhance uses AI to analyze plain text and enhance it with proper Markdown structure, including headers, lists, and formatting. It excels at understanding document semantics and converting flat text into well-structured Markdown.

**IMPORTANT**: This tool requires ostruct to be installed and configured with a valid API key. It uses AI models to understand and enhance document structure.

## Capabilities

- Identifies document titles, subtitles, and section headers
- Converts flat text to hierarchical Markdown structure
- Preserves all original content while adding semantic markup
- Detects lists, code blocks, and other structural elements
- Provides confidence scoring for structural decisions

## Common Usage Patterns

### Basic Semantic Enhancement

```bash
ostruct run prompts/enhance_structure.j2 schemas/enhance_structure.json \
  --fta text_content "{{INPUT_FILE}}" \
  --output-file "$TEMP_DIR/enhanced.json"
```

### With Document Metadata

```bash
ostruct run prompts/enhance_structure.j2 schemas/enhance_structure.json \
  -V "text_content=$(cat {{INPUT_FILE}})" \
  -V "document_metadata={\"format\":\"pdf\",\"pages\":10,\"type\":\"presentation\"}" \
  --output-file "$TEMP_DIR/enhanced.json"
```

### Extract Enhanced Markdown

```bash
jq -r '.enhanced_markdown' "$TEMP_DIR/enhanced.json" > "{{OUTPUT_FILE}}"
```

## Canonical command templates (planner-safe)

| id                    | description                                      | template |
|-----------------------|--------------------------------------------------|----------|
| `enhance_structure`   | Enhance plain text with semantic Markdown structure | `ostruct run prompts/enhance_structure.j2 schemas/enhance_structure.json -V "text_content=$(cat {{INPUT_FILE}})" --output-file "$TEMP_DIR/enhanced.json" && jq -r '.enhanced_markdown' "$TEMP_DIR/enhanced.json" > "{{OUTPUT_FILE}}"` |
| `enhance_with_meta`   | Enhance with document metadata for better context | `ostruct run prompts/enhance_structure.j2 schemas/enhance_structure.json -V "text_content=$(cat {{INPUT_FILE}})" -V "document_metadata={\"format\":\"{{FORMAT}}\",\"pages\":{{PAGES}}}" --output-file "$TEMP_DIR/enhanced.json" && jq -r '.enhanced_markdown' "$TEMP_DIR/enhanced.json" > "{{OUTPUT_FILE}}"` |

**Planner guidance**

- **Use after text extraction**: This tool works best on plain text extracted from PDFs, Word docs, etc.
- **Ideal for documents with poor structure**: When pdftotext or other extractors produce flat text without headers
- **Combine with extraction tools**: Use in a pipeline after pdftotext, markitdown, or other text extractors
- **Check confidence score**: The tool provides a confidence score (0-1) for its structural analysis
- **Best for**: Presentations, reports, articles with clear hierarchical structure
- **Not ideal for**: Dense technical documentation, code files, or highly formatted tables

## Integration Notes

- **Performance**: Processing time depends on text length and model used (typically 5-15 seconds)
- **Cost**: Uses AI API calls, so there's a per-request cost based on token usage
- **Quality**: Output quality depends on the clarity of the original document structure
- **Fallback**: If enhancement fails or confidence is low, use the original text

## Strengths / Limitations

| ✔︎ Strengths | ✖︎ Limitations |
|-------------|---------------|
| Understands semantic document structure | Requires API key and internet connection |
| Preserves all original content | Processing cost per document |
| Adds proper Markdown hierarchy | May misinterpret ambiguous structures |
| Works with any plain text input | Slower than rule-based converters |
| Provides structure analysis metadata | Quality varies with document complexity |

## Security Considerations

- ✅ Local processing with API calls
- ⚠️ Text is sent to AI API (consider for sensitive documents)
- ✅ No data retention by default (check API provider policies)
- ✅ Can be configured for local models if needed

## Performance

- **Speed**: 5-15 seconds per document depending on length
- **Memory**: Low memory usage locally
- **API Limits**: Subject to API rate limits and quotas
- **Token Usage**: Varies by document size (typically 1-5k tokens)

## Best Practices

1. **Use for post-processing**: Apply after initial text extraction for best results
2. **Provide metadata**: Include document type and format for better context
3. **Validate output**: Check the confidence score and structure summary
4. **Combine with validation**: Use the validation prompt to verify enhancement quality
5. **Cache results**: Save enhanced versions to avoid repeated API calls

## When to Use vs When NOT to Use

### When to Use

- PDF conversions where headers weren't preserved
- Extracted text that lacks proper structure
- Documents with clear hierarchical organization
- When semantic understanding is more important than speed
- Post-processing for better readability

### When NOT to Use

- Documents already well-structured in Markdown
- When processing sensitive/confidential content
- High-volume batch processing (due to cost)
- Technical documentation with complex formatting
- When offline processing is required

## Sample step emitted by planner

```bash
# id: semantic_enhancement
# After text extraction from PDF
ostruct run prompts/enhance_structure.j2 schemas/enhance_structure.json \
  -V "text_content=$(cat $TEMP_DIR/extracted.txt)" \
  -V "document_metadata={\"format\":\"pdf\",\"type\":\"presentation\"}" \
  --output-file "$TEMP_DIR/enhanced.json" && \
jq -r '.enhanced_markdown' "$TEMP_DIR/enhanced.json" > "{{OUTPUT_FILE}}"
```
