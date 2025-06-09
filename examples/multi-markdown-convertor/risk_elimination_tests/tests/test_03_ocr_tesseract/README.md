# Test 03: OCR via Tesseract Quality Assessment

## Purpose

Tests whether OCR via Tesseract (integrated with PyMuPDF) provides acceptable text extraction quality on low-resolution scanned documents with mixed languages.

## Test Description

This test evaluates OCR quality by:

1. Processing scanned PDF pages with mixed Hebrew and English text
2. Using PyMuPDF's Tesseract integration for OCR
3. Comparing extracted text against expected ground truth
4. Calculating Word Error Rate (WER) and character-level accuracy

## Key Metrics

- **Word Error Rate (WER)**: Percentage of words incorrectly recognized
- **Character Accuracy**: Percentage of characters correctly extracted
- **Language Detection**: Ability to handle mixed Hebrew/English content

## Usage

```bash
python test_03.py
```

## Expected Output

JSON file with:

- Per-page OCR results
- WER and accuracy statistics
- Language-specific performance metrics
- Success/failure status based on quality thresholds

## Files Used

- Deskewing.pdf (skewed OCR pages, mixed rotation)
- sample-invoice.pdf (low-contrast tabular invoice)
- RAND_RR287z1.hebrew.pdf (Hebrew RTL with English acronyms)

## Success Criteria

- Word Error Rate (WER) < 10%
- Character accuracy > 90%
- Successful handling of mixed language content

## Dependencies

- PyMuPDF with Tesseract integration
- Tesseract OCR engine
- Language packs for Hebrew and English
