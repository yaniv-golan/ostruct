# Pitch Deck Distiller

Extract structured data from startup pitch decks including company basics, funding details, founder information, and industry classification.

## Overview

This example demonstrates a **two-pass approach** to handle complex data extraction with industry classification:

1. **Pass 1**: Extract core company data using direct PDF processing + structured output
2. **Pass 2**: Add industry taxonomy classification using extracted data + taxonomy reference

## Why Two Passes?

OpenAI's structured output mode has compatibility issues with File Search when using complex nested schemas. The two-pass approach solves this by:

- Using direct PDF processing for core data extraction (Pass 1) - supports both text and image-based PDFs
- Adding complex taxonomy classification using File Search for taxonomy reference (Pass 2)

## Features

- **Native PDF Support**: Direct PDF processing using OpenAI's vision capabilities
- **Text + Image PDFs**: Works with both text-based and image-based pitch decks
- **URL Support**: Can process PDFs from URLs with proper security validation
- **Two-Pass Architecture**: Separates core extraction from complex taxonomy classification
- **Structured Output**: Reliable JSON extraction with confidence scoring

## Usage

### Quick Start

```bash
# 1️⃣ CI-friendly validation (no API calls)
./run.sh --test-dry-run

# 2️⃣ Live Pass-1 extraction only (core fields)
./run.sh --test-live

# 3️⃣ Full two-pass extraction on sample text
./run.sh data/sample_pitch.txt

# 4️⃣ Full two-pass extraction on a PDF deck (Uber 2008)
./run.sh examples/uber-pitch-deck-2008.pdf

# 5️⃣ Process PDF from URL (with security validation)
./run.sh https://example.com/pitch-deck.pdf
```

### Manual Pass-by-Pass

If you want fine-grained control you can still run each pass yourself:

```bash
# Pass 1 – Core data extraction (direct PDF processing)
ostruct run templates/pass1_core.j2 schemas/pass1_core.json \
    --file user-data:deck examples/uber-pitch-deck-2008.pdf > pass1.json

# Pass 2 – Industry taxonomy classification
ostruct run templates/pass2_taxonomy.j2 schemas/pass2_taxonomy_simple.json \
    --enable-tool file-search \
    --file fs:taxonomy reference/taxonomy.md \
    --json-var core_data="$(cat pass1.json)" > pass2.json

# Merge results
jq -s '.[0] + {"industry_classification": .[1]}' pass1.json pass2.json
```

## Output Structure

The final JSON includes:

```json
{
  "company_name": "Nexus Biotech",
  "summary": "Company description...",
  "funding_ask": {
    "amount_usd": 25000000,
    "stage": "Series B",
    "use_of_funds": "R&D and Product Development..."
  },
  "founders": [...],
  "industry_classification": {
    "sector": "Healthcare",
    "industry_group": "Pharmaceuticals & Biotechnology",
    "industry": "Biotechnology",
    "vertical": "Digital Health",
    "emerging_spaces": ["AI-powered drug discovery", "Generative AI", ...]
  },
  "extraction_metadata": {
    "confidence_score": 0.98,
    "extraction_method": "pdf_text"
  }
}
```

## Files

- `run.sh` – Standards-compliant launcher (handles dry-run, live, full two-pass)
- `templates/pass1_core.j2` – Core data extraction template
- `templates/pass2_taxonomy.j2` – Taxonomy classification template
- `schemas/pass1_core.json` – Core data schema
- `schemas/pass2_taxonomy_simple.json` – Taxonomy classification schema
- `reference/taxonomy.md` – Complete industry taxonomy reference
- `data/sample_pitch.txt` – Sample pitch text
- **Example PDF decks** (text-based):
  - `examples/uber-pitch-deck-2008.pdf`
  - `examples/buffer-seedround-pitchdeck-2011.pdf`
  - `examples/airbnb-pitch-deck-2009.pdf`

## Requirements

- OpenAI API key configured (`OPENAI_API_KEY`)
- Vision-enabled model (gpt-4o, gpt-4o-mini, or gpt-4-turbo)
- File Search tool enabled (for Pass 2 taxonomy classification)
- `jq` installed for JSON merging

## Example Output

The system successfully extracts and classifies companies like:

- **Nexus Biotech**: Healthcare > Pharmaceuticals & Biotechnology > Biotechnology
- **Emerging spaces**: AI-powered drug discovery, Generative AI, CRISPR diagnostics

## Technical Notes

- **Pass 1**: Uses direct PDF processing with OpenAI's native vision capabilities
- **Pass 2**: Uses File Search for taxonomy reference lookup
- Handles both text-based and image-based PDFs natively
- URL processing with security validation (blocks private IPs by default)
- Flattened taxonomy schema avoids OpenAI structured output validation issues
- Confidence scoring and extraction metadata included
- Automatic model capability validation ensures vision support
