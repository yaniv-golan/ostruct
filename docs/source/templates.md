# Template Creation Guide

This guide provides information on how to create templates for use with `ostruct`.

## ostruct and Jinja2

`ostruct` templates are implemented using a customized instance of Jinja2. Jinja2 is a templating engine for Python. It allows you to combine static text with dynamic content using placeholders and logic. In `ostruct`, Jinja2 templates are used to define the prompts sent to the OpenAI API. This guide assumes no prior knowledge of Jinja2.

## Basic Syntax

### Variables

Variables in ostruct templates are enclosed in double curly braces: `{{ variable_name }}`. `ostruct` makes various pieces of information available to the template:

* **File Information**: When using `-f`, `-d`, or `-p` flags, file information is available through `FileInfo` objects
* **Custom Variables**: Values defined using `-V` or `-J` flags
* **System Variables**: Built-in variables and context provided by `ostruct`

#### File Information

When you map files using the input flags, you can access their contents and metadata through `FileInfo` objects:

* `-f NAME FILE`: Maps a single file to a variable. Access directly: `{{ name.content }}`
* `-d NAME DIR`: Maps a directory to a variable. Access with iteration: `{% for file in name %}`
* `-p NAME PATTERN`: Maps files matching a glob pattern. Access with iteration: `{% for file in name %}`

For example, mapping a single file (`-f`):

```jinja2
# Map a source file:
-f source input.py

# In template:
{{ source.content }}  # File contents
{{ source.path }}    # File path
```

For directories (`-d`) or patterns (`-p`):

```jinja2
# Map Python files:
-d python_files src/
# or
-p python_files "src/**/*.py"

# In template:
{% for file in python_files %}
  File: {{ file.path }}
  Content: {{ file.content }}
{% endfor %}
```

Each `FileInfo` object provides these attributes:

* `name`: File name
* `path`: Path relative to the base directory (set by `--base-dir` or defaults to current working directory)
* `abs_path`: Absolute filesystem path
* `content`: File contents
* `ext`: File extension
* `basename`: Base name without extension
* `dirname`: Directory name
* `exists`: Whether file exists
* `is_file`: Whether it's a file
* `is_dir`: Whether it's a directory
* `size`: File size
* `mtime`: Modification time
* `encoding`: File encoding
* `hash`: File hash
* `extension`: File extension (same as ext)
* `parent`: Parent directory
* `stem`: File name without extension
* `suffix`: File extension with dot
* `__html__`: HTML-safe string representation
* `__html_format__`: HTML formatting support

#### Custom Variables

Using the `-V` flag for string variables:

```jinja2
-V myvar=hello
{{ myvar }}  # Outputs: hello
```

Using the `-J` flag for JSON variables:

```jinja2
-J data='{"key1": "value1", "key2": "value2"}'
{{ data.key1 }}  # Outputs: value1
```

### Control Structures

Jinja2 provides control structures like `for` loops and `if` statements, enclosed in `{% ... %}` blocks.

#### For Loops

When processing multiple files (using `-d` or `-p`):

```jinja2
{% for file in content %}
File: {{ file.path }}
Content:
{{ file.content }}
{% endfor %}
```

#### If Statements

```jinja2
{% if content %}
  Content is available.
{% else %}
  No content provided.
{% endif %}

{% if myvar == 'hello' %}
  Variable equals hello.
{% endif %}
```

### Comments

Comments in Jinja2 are enclosed in `{# ... #}`. The `CommentExtension` in `ostruct` provides special handling:

```jinja2
{# This is a comment and will not be included in the output #}
```

The extension ensures that:

* Contents of comment blocks are completely ignored during parsing
* Variables inside comments are not validated or processed
* Comments are stripped from the output
* Comment validation is skipped during template processing

## Frontmatter

`ostruct` supports YAML frontmatter at the beginning of template files. Frontmatter is a block of YAML code at the top of a file, enclosed by triple dashes (`---`). It's used to define metadata or settings for the template.

The most common use is defining the `system_prompt`:

```jinja2
---
system_prompt: You are an expert code reviewer.
---
Review this code: {{ code.content }}
```

If no system prompt is provided in frontmatter:

* The default `ostruct` system prompt will be used
* Unless overridden by command line flags (`--sys-prompt` or `--sys-file`)

## Example Templates

### Code Review Template

```jinja2
---
system_prompt: You are an expert code reviewer. Focus on security vulnerabilities.
---
Review the following code and identify any security vulnerabilities:

{% for file in source_files %}
## File: {{ file.path }}

```python
{{ file.content }}
```

{% endfor %}

```

This template:
1. Sets a security-focused system prompt
2. Iterates through files in the `source_files` variable (mapped with `-d` or `-p`)
3. Formats each file's content within a code block

### Configuration Validation

```jinja2
---
system_prompt: You are an expert in configuration validation. Identify any issues or inconsistencies.
---
Validate the following configuration files:

{% for file in config_files %}
## Config: {{ file.path }}

```yaml
{{ file.content }}
```

{% endfor %}

```

This example processes multiple configuration files, presenting them in a clear format for validation.

### Advanced Example with Filters

```jinja2
---
system_prompt: "You are an expert summarizer."
---
Summarize these files:

{% for file in text_files %}
  {% if file.content | word_count > 10 %}
# File: {{ file.path }}
Word Count: {{ file.content | word_count }}
Token Estimate: {{ file.content | estimate_tokens }}

Content:
{{ file.content }}
  {% endif %}
{% endfor %}
```

This example:

* Filters files by word count
* Shows word count and token estimates
* Demonstrates filter usage

## Best Practices

1. **Use Frontmatter for System Prompts**
   * Define your `system_prompt` in frontmatter
   * Keep it focused and specific to the task

2. **Variable Naming**
   * Use descriptive names that indicate content type
   * Follow consistent naming conventions
   * Examples: `code`, `config`, `input_files`

3. **Content Placement**
   * Put file content last in the prompt
   * Use clear delimiters (like markdown or xml code blocks)
   * Models handle structured output better when content follows the prompt

4. **Use Filters Effectively**
   * Leverage built-in and custom filters for text processing
   * Chain filters for complex transformations
   * See the [Template Filters](template_filters.md) guide for details

5. **Testing and Debugging**
   * Use `--dry-run` to preview prompts
   * Use the `debug` global function for troubleshooting
   * Test with various input types and sizes

6. **Security Considerations**
   * Validate user input before processing
   * Use `strip_comments` when processing code
   * Be cautious with dynamic template content

7. **Performance**
   * Use control structures to filter content early
   * Estimate tokens to stay within limits
   * Consider chunking large files

## See Also

* [Template Filters](template_filters.md) - Detailed documentation of available filters
* [CLI Reference](cli.md) - Complete command-line interface documentation

### Filters

Filters modify variables. They are applied using the pipe symbol (`|`). `ostruct` provides additional custom filters beyond the standard Jinja2 filters, organized by category:

**Text Processing**

* `extract_keywords`: Extract keywords from text
* `word_count`: Count words in text
* `char_count`: Count characters in text
* `to_json`: Convert object to JSON string
* `from_json`: Parse JSON string into object
* `remove_comments`: Remove comments from text
* `wrap`: Wrap text to specified width
* `indent`: Indent text
* `dedent`: Remove common leading whitespace
* `normalize`: Normalize whitespace in text
* `strip_markdown`: Remove markdown formatting

**Data Processing**

* `sort_by`: Sort items by key
* `group_by`: Group items by key
* `filter_by`: Filter items by key-value pair
* `extract_field`: Extract specific field from items
* `unique`: Get unique items
* `frequency`: Compute frequency distribution
* `aggregate`: Calculate aggregate statistics (count, sum, avg, min, max)

**Table Formatting**

* `table`: Format data as table
* `align_table`: Align table columns
* `dict_to_table`: Convert dictionary to table
* `list_to_table`: Convert list to table
* `auto_table`: Automatically format as table

**Code Processing**

* `format_code`: Format code with syntax highlighting (supports 'terminal', 'html', and 'plain' output)
* `strip_comments`: Remove code comments (supports multiple languages)

**Special Character Handling**

* `escape_special`: Escape special characters

The `strip_comments` filter supports these languages:

* Python (`#`)
* JavaScript/TypeScript/Java/C/C++/Go/Rust/Swift/PHP (`//` and `/* */`)
* Ruby/Perl/Shell/Bash (`#`)
* PHP (`//` and `/* */`)

The `format_code` filter supports three output formats:

* `terminal`: Terminal-colored output (default)
* `html`: HTML-formatted output
* `plain`: Plain text output

### Global Functions

`ostruct` provides these global functions for use in templates:

* `estimate_tokens`: Estimate tokens using tiktoken's o200k_base encoding (falls back to word count)
* `format_json`: Format JSON with indentation
* `now`: Get current datetime
* `debug`: Print debug information during template rendering
* `type_of`: Get type name of object
* `dir_of`: List object attributes
* `len_of`: Get object length if available
* `validate_json`: Validate JSON against schema
* `format_error`: Format error messages
* `summarize`: Generate summary statistics for data
* `pivot_table`: Create pivot tables from data
* `auto_table`: Auto-format data as table
