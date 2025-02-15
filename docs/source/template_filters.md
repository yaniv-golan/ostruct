# Template Filters

This document describes the template filters and globals available in the Jinja2 environment.

## Text Processing Filters

### `word_count`

Counts the number of words in a text string.

```jinja2
{% set count = text | word_count %}
```

### `char_count`

Counts the number of characters in a text string.

```jinja2
{% set count = text | char_count %}
```

### `to_json`

Converts an object to a JSON string.

```jinja2
{% set json_str = data | to_json %}
```

### `from_json`

Parses a JSON string into an object.

```jinja2
{% set obj = json_str | from_json %}
```

### `remove_comments`

Removes comments from text (supports #, //, and /**/ style comments).

```jinja2
{% set clean_text = code | remove_comments %}
```

### `normalize`

Normalizes whitespace in text.

```jinja2
{% set normalized = text | normalize %}
```

### `strip_markdown`

Removes markdown formatting characters.

```jinja2
{% set plain_text = markdown | strip_markdown %}
```

### `wrap`

Wraps text to a specified width.

```jinja2
{% set wrapped = text | wrap(width=80) %}
```

### `indent`

Indents text by a specified amount.

```jinja2
{% set indented = text | indent(4) %}
```

### `dedent`

Removes common leading whitespace from every line.

```jinja2
{% set dedented = text | dedent %}
```

## Data Processing Filters

### `sort_by`

Sorts a sequence of items by a specified key.

```jinja2
{% set sorted_items = items | sort_by('name') %}
```

### `group_by`

Groups items by a specified key.

```jinja2
{% set grouped = items | group_by('category') %}
```

### `filter_by`

Filters items by matching a key to a value.

```jinja2
{% set filtered = items | filter_by('status', 'active') %}
```

### `extract_field`

Extracts a specific field from each item in a sequence.

```jinja2
{% set names = items | extract_field('name') %}
```

### `unique`

Returns unique items from a sequence.

```jinja2
{% set unique_items = items | unique %}
```

### `frequency`

Computes frequency distribution of items.

```jinja2
{% set freq = items | frequency %}
```

### `aggregate`

Computes aggregate statistics (count, sum, avg, min, max) for numeric values.

```jinja2
{% set stats = numbers | aggregate %}
```

## Table Formatting Filters

### `table`

Formats data as a table.

```jinja2
{% set table = data | table %}
```

### `align_table`

Aligns columns in a table.

```jinja2
{% set aligned = table | align_table %}
```

### `dict_to_table`

Converts a dictionary to a table format.

```jinja2
{% set table = dict_data | dict_to_table %}
```

### `list_to_table`

Converts a list to a table format.

```jinja2
{% set table = list_data | list_to_table %}
```

### `auto_table`

Automatically formats data as a table based on its type.

```jinja2
{% set table = data | auto_table %}
```

## Code Processing Filters

### `format_code`

Formats code with syntax highlighting.

```jinja2
{% set formatted = code | format_code('python') %}
```

### `strip_comments`

Removes comments from code.

```jinja2
{% set clean_code = code | strip_comments %}
```

## Special Character Handling

### `escape_special`

Escapes special characters in text.

```jinja2
{% set escaped = text | escape_special %}
```

## Template Globals

### `estimate_tokens`

Estimates the number of tokens in text using model-specific encodings.

```jinja2
{% set token_count = estimate_tokens(text) %}
```

The function uses tiktoken with model-specific encodings:

- `o200k_base` for GPT-4o, O1, and O3 models
- `cl100k_base` for other models

It includes:

- Message formatting overhead (+4 tokens)
- Graceful fallback to word count if token estimation fails

### `format_json`

Formats JSON with indentation and proper string conversion.

```jinja2
{% set formatted = format_json(data) %}
```

### `now`

Returns the current datetime.

```jinja2
{% set current_time = now() %}
```

### `debug`

Prints debug information during template rendering.

```jinja2
{{ debug(variable) }}
```

### `type_of`

Returns the type name of an object.

```jinja2
{% set type_name = type_of(variable) %}
```

### `dir_of`

Returns a list of attributes for an object.

```jinja2
{% set attributes = dir_of(object) %}
```

### `len_of`

Returns the length of an object if available.

```jinja2
{% set length = len_of(sequence) %}
```

### `validate_json`

Validates JSON data against a schema.

```jinja2
{% set is_valid = validate_json(data, schema) %}
```

### `format_error`

Formats error messages consistently.

```jinja2
{% set error_msg = format_error(error) %}
```
