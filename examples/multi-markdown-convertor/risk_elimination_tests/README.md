# Risk-Elimination Test Inputs

This folder contains canonical input files used by our 30 smoke-tests.  
Where practical, a single asset exercises multiple tests to keep CI lean.

| ID | Local file | Format | Key structure / features | Useful for tests → |
|----|------------|--------|--------------------------|--------------------|
| **A** | [NIPS-2017-attention-is-all-you-need-Paper.pdf](./test-inputs/NIPS-2017-attention-is-all-you-need-Paper.pdf) | PDF | two-column research paper; small tables, equations, captions | **1**, 11, 21 |
| **B** | [World Bank Annual Report 2024.pdf](./test-inputs/World%20Bank%20Annual%20Report%202024.pdf) | PDF | 200+ pp, heavy tabular & chart content | **2**, 11, 12 |
| **C** | [Deskewing.pdf](./test-inputs/Deskewing.pdf) | PDF (scans) | skewed OCR pages, mixed rotation | **3**, 20 |
| **D** | [sample-invoice.pdf](./test-inputs/sample-invoice.pdf) | PDF (scan) | low-contrast tabular invoice, barcode | **3**, 20 |
| **E** | [f1040.pdf](./test-inputs/f1040.pdf) | PDF (form) | dense fillable fields, check-boxes | **11**, 12, 22 |
| **F** | [Financial Sample.xlsx](./test-inputs/Financial%20Sample.xlsx) | XLSX | formulas, two embedded charts | **9**, 10, 11 |
| **G** | [merged-cells.xlsx](./test-inputs/merged-cells.xlsx) | XLSX | many merged cells, defined names | **7** |
| **H** | [FFY-23-NGCDD-Annual-Report.doc](./test-inputs/FFY-23-NGCDD-Annual-Report.doc) | DOCX | 54 pp, hierarchical Heading 1-4 styles, mixed bullet + number lists, merged-cell tables | **4**, 6, 7, 11, 12, 18 |
| **I** | [example03.docx](./test-inputs/example03.docx) | DOCX | ordered list starts at 7; alt-text on images | **4**, 6 |
| **J** | [samplepptx.pptx](./test-inputs/samplepptx.pptx) | PPTX | nested (3-level) bullets, speaker notes | **5**, 8 |
| **K** | [2-1876-Hexagonal-Header-Blocks-PGO-4_3.pptx](./test-inputs/2-1876-Hexagonal-Header-Blocks-PGO-4_3.pptx) | PPTX | text boxes L/R, layout order challenge | **8**, 5 |
| **L** | [RAND_RR287z1.hebrew.pdf](./test-inputs/RAND_RR287z1.hebrew.pdf) | PDF (RTL) | full Hebrew RTL, mixed English acronyms | **21**, 27 |

### Legend

* **ID** – short handle used in discussions & scripts.  
* **Tests** – numbers correspond to the 30 smoke-tests listed in *risk-elimination-tests/README.md* (e.g. Test 1 = "multi-column PDF ordering", Test 24 = "parallel ostruct RPS throttling").  
