# Test 02: PyMuPDF Table Detection

## Purpose

Tests whether `page.find_tables()` in PyMuPDF can reliably detect tables across different PDF types with acceptable precision and recall rates.

## Test Description

This test evaluates PyMuPDF's table detection capabilities by:

1. Processing multiple PDFs with known table structures
2. Using `page.find_tables()` to detect tables automatically
3. Comparing detected tables against manually labeled ground truth
4. Calculating precision and recall metrics

## Key Metrics

- **Precision**: Percentage of detected tables that are actually tables
- **Recall**: Percentage of actual tables that were detected
- **F1 Score**: Harmonic mean of precision and recall

## Usage

```bash
python test_02.py
```

## Expected Output

JSON file with:

- Per-PDF detection results
- Overall precision/recall statistics
- Success/failure status based on 90% detection threshold

## Files Used

- World Bank Annual Report 2024.pdf (heavy tabular content)
- NIPS-2017-attention-is-all-you-need-Paper.pdf (research tables)
- f1040.pdf (form tables)

## Success Criteria

- Overall recall ≥ 90% for table detection
- Precision ≥ 80% to minimize false positives
