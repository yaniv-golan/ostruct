# Etymology Analysis Schema Documentation

This document provides detailed information about the etymology analysis schema.

## Schema Overview

The schema defines a structured format for etymological analysis of words, capturing:

- The complete word
- Its etymological breakdown
- Component relationships
- Origin languages
- Meanings

## Schema Structure

```json
{
  "type": "object",
  "properties": {
    "word": {
      "type": "string",
      "description": "The word being analyzed"
    },
    "etymology": {
      "type": "object",
      "description": "The etymological breakdown",
      "properties": {
        "component": "string",
        "originLanguage": "string",
        "meaning": "string",
        "order": "integer",
        "children": "array"
      }
    }
  }
}
```

## Field Descriptions

### Top Level

| Field     | Type   | Required | Description                    |
|-----------|--------|----------|--------------------------------|
| word      | string | Yes      | The word being analyzed        |
| etymology | object | Yes      | The etymological breakdown     |

### Etymology Object

| Field         | Type    | Required | Description                        |
|--------------|---------|----------|------------------------------------|
| component    | string  | Yes      | The word component                 |
| originLanguage| string  | Yes      | Language of origin                 |
| meaning      | string  | Yes      | Component meaning                  |
| order        | integer | Yes      | Position in word (1-based)         |
| children     | array   | Yes      | Sub-components (can be empty)      |

## Example Outputs

### Simple Word

```json
{
  "word": "biology",
  "etymology": {
    "component": "biology",
    "originLanguage": "Modern Latin",
    "meaning": "study of life",
    "order": 1,
    "children": [
      {
        "component": "bio",
        "originLanguage": "Greek",
        "meaning": "life",
        "order": 1,
        "children": []
      },
      {
        "component": "logy",
        "originLanguage": "Greek",
        "meaning": "study of",
        "order": 2,
        "children": []
      }
    ]
  }
}
```

### Complex Word

```json
{
  "word": "gastroenterology",
  "etymology": {
    "component": "gastroenterology",
    "originLanguage": "Modern Latin",
    "meaning": "study of stomach and intestines",
    "order": 1,
    "children": [
      {
        "component": "gastro",
        "originLanguage": "Greek",
        "meaning": "stomach",
        "order": 1,
        "children": []
      },
      {
        "component": "entero",
        "originLanguage": "Greek",
        "meaning": "intestine",
        "order": 2,
        "children": []
      },
      {
        "component": "logy",
        "originLanguage": "Greek",
        "meaning": "study of",
        "order": 3,
        "children": []
      }
    ]
  }
}
```

## Validation Rules

1. All required fields must be present
2. Order must be a positive integer
3. Children must follow the same schema
4. Component must be a non-empty string
5. OriginLanguage must be a recognized language
6. Meaning must be a non-empty string

## Best Practices

1. Keep meanings concise but clear
2. Use consistent language names
3. Order components left-to-right
4. Include all meaningful components
5. Use empty children arrays for atomic components
