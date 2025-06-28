# File Search • Quick Start

> **Tools:** 📄 File Search
> **Cost (approx.):** <$0.02 with gpt-4o-mini

## 1. Description

Demonstrates basic File Search usage by uploading two documents and answering questions with citations. This example shows how to use ostruct's File Search tool to find relevant information across multiple documents and provide accurate citations.

## 2. Prerequisites

```bash
# No special dependencies required
```

## 3. Quick Start

```bash
# Fast validation (no API calls)
./run.sh --test-dry-run

# Live API test (minimal cost)
./run.sh --test-live

# Full execution
./run.sh

# With custom model
./run.sh --model gpt-4o
```

## 4. Files

| Path | Purpose |
|------|---------|
| `templates/main.j2` | Primary template that asks questions about the uploaded documents |
| `schemas/main.json` | Validates the response structure with answers and citations |
| `data/company_policy.txt` | Sample company policy document |
| `data/employee_handbook.txt` | Sample employee handbook |
| `data/test_doc.txt` | Minimal test document for quick validation |

## 5. Expected Output

The example produces:

- **Structured answers** to questions about the documents
- **Proper citations** showing which documents were referenced
- **Confidence scores** for each answer

Example output structure:

```json
{
  "answers": [
    {
      "question": "What is the vacation policy?",
      "answer": "Employees are entitled to 15 days of paid vacation per year...",
      "citations": ["company_policy.txt", "employee_handbook.txt"],
      "confidence": "high"
    }
  ]
}
```

## 6. Customization

- **Different documents**: Replace files in `data/` with your own documents
- **Custom questions**: Modify the template to ask different questions
- **Question types**: Add various question formats (factual, analytical, comparative)

## 7. Clean-Up

No cleanup required - File Search doesn't generate local files.
