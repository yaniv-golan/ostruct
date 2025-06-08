# Test Data

This directory contains sample documents for testing the document conversion system.

## Available Test Documents

For comprehensive testing, use the documents available in:
`examples/multi-markdown-convertor/risk_elimination_tests/test-inputs/`

These include:

### PDF Documents

- `RAND_RR287z1.hebrew.pdf` (1.0MB) - Hebrew text, complex layout
- `World Bank Annual Report 2024.pdf` (11MB) - Large document, requires chunking
- `NIPS-2017-attention-is-all-you-need-Paper.pdf` (556KB) - Academic paper
- `f1040.pdf` (159KB) - Tax form with complex tables
- `sample-invoice.pdf` (373KB) - Business document

### Office Documents

- `FFY-23-NGCDD-Annual-Report.docx` (42KB) - Government report
- `example03.docx` (106KB) - Complex document
- `2-1876-Hexagonal-Header-Blocks-PGO-4_3.pptx` (134KB) - Technical presentation
- `samplepptx.pptx` (404KB) - Large presentation

### Spreadsheets

- `Financial Sample.xlsx` (81KB) - Financial data
- `merged-cells.xlsx` (2.6KB) - Complex cell merging

## Testing Commands

```bash
# Test with a simple PDF
../convert.sh ../risk_elimination_tests/test-inputs/f1040.pdf output/f1040.md

# Test analysis only
../convert.sh --analyze-only ../risk_elimination_tests/test-inputs/FFY-23-NGCDD-Annual-Report.docx

# Test dry run
../convert.sh --dry-run ../risk_elimination_tests/test-inputs/Financial\ Sample.xlsx output/financial.md

# Test large document (chunking)
../convert.sh ../risk_elimination_tests/test-inputs/World\ Bank\ Annual\ Report\ 2024.pdf output/world_bank.md
```

## Creating Your Own Test Files

You can add your own test documents to this directory. Recommended test cases:

1. **Simple text PDF** - Basic text extraction
2. **Complex layout PDF** - Tables, columns, images
3. **Scanned PDF** - OCR requirements
4. **DOCX with images** - Office document with media
5. **PowerPoint presentation** - Slide content extraction
6. **Excel spreadsheet** - Data table conversion

## Test Results

After running tests, check:

- Output quality in the `output/` directory
- Logs in `temp/logs/` for debugging
- Performance metrics in `temp/logs/performance.log`
- Security audit in `temp/logs/security.log`
