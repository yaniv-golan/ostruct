# Migration Guide

This guide helps users migrate from the CLI bundled with `openai-structured` to the new standalone `ostruct-cli` package.

## Why the Split?

The CLI functionality has been moved to a separate package to:

- Reduce dependencies for users who only need the core library
- Allow independent versioning of the CLI and core library
- Enable faster development and deployment of CLI features
- Provide better documentation and examples focused on structured output

## Migration Steps

1. **Install the new package:**

   ```bash
   pip install ostruct-cli
   ```

2. **Update your commands:**
   - Old: `openai-structured --task ...`
   - New: `ostruct --task ...`

   The core arguments remain the same:

   ```bash
   # Old
   openai-structured --task "Analyze: {{ input }}" --schema schema.json --file input=data.txt

   # New
   ostruct --task "Analyze: {{ input }}" --schema schema.json --file input=data.txt
   ```

3. **Review your schema files:**
   - Ensure your JSON schema files are valid
   - Add descriptions to schema properties for better model guidance
   - Consider using enums for constrained values

   ```json
   {
     "type": "object",
     "properties": {
       "category": {
         "type": "string",
         "enum": ["feature", "bug", "improvement"],
         "description": "Type of the issue"
       }
     }
   }
   ```

4. **Update your templates:**
   - System prompts can now be included in templates using frontmatter:

     ```
     ---
     system_prompt: You are an expert code reviewer.
     ---
     Review this code: {{ code.content }}
     ```

   - Or use the `{% system_prompt %}` block:

     ```
     {% system_prompt %}
     You are an expert code reviewer.
     {% end_system_prompt %}

     Review this code: {{ code.content }}
     ```

## Version Compatibility

`ostruct-cli` requires `openai-structured>=0.9.1`. If you're using an older version:

```bash
pip install --upgrade openai-structured
```

## Model Changes

The default model is now `gpt-4o-2024-08-06`, which is optimized for structured output. This model:

- Understands and follows JSON schemas more reliably
- Provides better validation of structured responses
- Has improved context handling for large inputs

## Environment Variables

- `OPENAI_API_KEY` is still required and works the same way
- Cache-related environment variables are no longer used, as caching is now handled by the core library

## Breaking Changes

1. **Command Name:**
   - The command is now `ostruct` instead of `openai-structured`

2. **Default Model:**
   - Now uses `gpt-4o-2024-08-06` by default
   - Previous default models may not support structured output

3. **File Access:**
   - Stricter security by default
   - Must explicitly allow access to directories outside CWD using `--allowed-dir`

4. **Removed Features:**
   - Response caching (now handled by core library)
   - Direct JSON output validation (now requires schema)
   - Legacy command format

## Best Practices

1. **Always use schemas:**
   - Define clear, well-documented schemas
   - Include property descriptions
   - Use enums where appropriate

2. **Structure your prompts:**
   - Use system prompts for model behavior
   - Keep user prompts focused on the task
   - Reference schema fields in prompts

3. **Handle files safely:**
   - Use absolute paths with `--allowed-dir`
   - Keep sensitive files outside project directories
   - Use file lists for bulk operations
