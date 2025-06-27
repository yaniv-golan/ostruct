# Etymology Analysis

This use case demonstrates how to perform etymological analysis of words using the OpenAI Structured CLI. It breaks down words into their components, showing their origins, meanings, and hierarchical relationships.

## Features

- Detailed etymological breakdown of words
- Component-by-component analysis
- Origin language identification
- Hierarchical relationship mapping
- Support for complex word structures

## Directory Structure

```
.
├── README.md           # This file
├── prompts/           # AI prompts
│   ├── system.txt     # AI's role and expertise
│   └── task.j2        # Etymology analysis template
├── schemas/           # Output structure
│   └── etymology.json # Schema for etymology breakdown
├── examples/          # Sample words to analyze
│   ├── medical.txt    # Medical terminology
│   ├── scientific.txt # Scientific terms
│   └── compound.txt   # Compound words
└── docs/             # Documentation
    ├── customization.md  # How to customize
    └── schema.md        # Schema reference
```

## Usage

1. **Basic Usage**:

   ```bash
   ostruct run prompts/task.j2 schemas/etymology.json \
     --var word=automobile \
     --sys-file prompts/system.txt
   ```

2. **Analyze Multiple Words**:

   ```bash
   # Using a file with one word per line
   cat examples/medical.txt | while read word; do
     ostruct run prompts/task.j2 schemas/etymology.json \
       --var word="$word" \
       --sys-file prompts/system.txt
   done
   ```

3. **Output to File**:

   ```bash
   ostruct run prompts/task.j2 schemas/etymology.json \
     --var word=pneumonoultramicroscopicsilicovolcanoconiosis \
     --sys-file prompts/system.txt \
     --output-file etymology_result.json
   ```

## Example Outputs

1. **Simple Compound Word**:

   ```json
   {
     "word": "automobile",
     "etymology": {
       "component": "automobile",
       "originLanguage": "French",
       "meaning": "self-moving vehicle",
       "order": 1,
       "children": [
         {
           "component": "auto",
           "originLanguage": "Greek",
           "meaning": "self",
           "order": 1,
           "children": []
         },
         {
           "component": "mobile",
           "originLanguage": "Latin",
           "meaning": "moving",
           "order": 2,
           "children": []
         }
       ]
     }
   }
   ```

2. **Complex Medical Term**:

   ```json
   {
     "word": "microglia",
     "etymology": {
       "component": "microglia",
       "originLanguage": "Modern Latin",
       "meaning": "small glial cells in the central nervous system",
       "order": 1,
       "children": [
         {
           "component": "micro",
           "originLanguage": "Greek",
           "meaning": "small",
           "order": 1,
           "children": []
         },
         {
           "component": "glia",
           "originLanguage": "Greek",
           "meaning": "glue",
           "order": 2,
           "children": []
         }
       ]
     }
   }
   ```

## Customization

See `docs/customization.md` for detailed instructions on:

- Adding custom word lists
- Modifying analysis depth
- Extending the schema
- Adding language support

## Schema

The etymology analysis follows a structured schema defined in `schemas/etymology.json`. See `docs/schema.md` for:

- Complete schema documentation
- Field descriptions
- Example outputs

## Prerequisites

- OpenAI Structured CLI installed
- OpenAI API key configured
- Word or list of words to analyze

## Limitations

- Currently supports primarily words with Greek, Latin, and modern European language origins
- Maximum word length may be limited by model context window
- Accuracy depends on model's etymological knowledge
