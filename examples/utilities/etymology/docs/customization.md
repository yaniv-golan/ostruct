# Customizing Etymology Analysis

This guide explains how to customize the etymology analysis tool for your specific needs.

## Adding Custom Word Lists

1. Create a new text file in the `examples` directory:

   ```bash
   touch examples/your_category.txt
   ```

2. Add one word per line:

   ```
   word1
   word2
   word3
   ```

## Modifying Analysis Depth

The schema supports nested components through the `children` array. You can control analysis depth by:

1. Modifying the system prompt to specify desired depth
2. Adjusting the model's temperature setting
3. Using different word lists with varying complexity

## Extending the Schema

The schema in `schemas/etymology.json` can be extended with additional fields:

```json
{
  "properties": {
    "etymology": {
      "properties": {
        "yearFirstUsed": {
          "type": "integer",
          "description": "Year the word was first documented"
        },
        "alternativeMeanings": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "Alternative meanings in different contexts"
        }
      }
    }
  }
}
```

## Adding Language Support

To improve support for additional languages:

1. Update the system prompt with specific language expertise
2. Add language-specific example word lists
3. Include language-specific documentation in schema descriptions
4. Consider adding language-specific fields to the schema

## Performance Optimization

1. Batch Processing:

   ```bash
   # Process multiple words efficiently
   cat examples/your_list.txt | while read word; do
     ostruct run prompts/task.j2 schemas/etymology.json \
       --var word="$word" \
       --sys-file prompts/system.txt
   done > results.json
   ```

2. Caching Results:
   - Store results in a database
   - Implement a caching layer
   - Use pre-computed results for common words

## Error Handling

Add custom error handling by extending the schema:

```json
{
  "properties": {
    "error": {
      "type": "object",
      "properties": {
        "code": {
          "type": "string",
          "enum": ["UNKNOWN_WORD", "AMBIGUOUS_ORIGIN", "MULTIPLE_ETYMOLOGIES"]
        },
        "message": {
          "type": "string"
        }
      }
    }
  }
}
```
