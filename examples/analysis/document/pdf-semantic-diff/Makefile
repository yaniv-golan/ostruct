# PDF Semantic Diff Example
# Semantic comparison of PDF documents using Code Interpreter

.PHONY: test-dry test-live run clean help

# Default target
help:
	@echo "PDF Semantic Diff Example"
	@echo "Semantic comparison of PDF documents using Code Interpreter"
	@echo ""
	@echo "Available targets:"
	@echo "  test-dry    - Validate templates and schemas (no API calls)"
	@echo "  test-live   - Run minimal live test with PDF comparison"
	@echo "  run         - Execute semantic diff analysis with default PDFs"
	@echo "  clean       - Remove generated files"
	@echo "  help        - Show this help message"
	@echo ""
	@echo "Usage:"
	@echo "  make run"
	@echo "  make test-live"
	@echo ""
	@echo "For custom PDFs, use ostruct directly:"
	@echo "  ostruct run templates/pdf_semantic_diff.j2 schemas/semantic_diff.schema.json --file ci:old_pdf old.pdf --file ci:new_pdf new.pdf --enable-tool code-interpreter"
	@echo ""
	@echo "Features:"
	@echo "  - Semantic document comparison (not just text diff)"
	@echo "  - PDF processing with Code Interpreter"
	@echo "  - Structured change detection"
	@echo "  - Validation and quality checks"

# Configuration
MODEL ?= gpt-4o

# Check if test data exists
test-data-check:
	@if [ ! -f "data/contracts/v1.pdf" ] || [ ! -f "data/contracts/v2.pdf" ]; then \
		echo "❌ Error: PDF files not found"; \
		echo "💡 Run: cd data && python generate_pdfs.py"; \
		exit 1; \
	fi

test-dry:
	./scripts/dry_run.sh

test-live: test-data-check
	./scripts/run_example.sh

run: test-data-check
	./scripts/run_example.sh

clean:
	@echo "🧹 Cleaning up generated files..."
	rm -f *.json *.log
	rm -rf downloads/ output/
	@echo "✅ Cleanup completed"
