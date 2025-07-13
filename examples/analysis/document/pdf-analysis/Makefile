# PDF Analysis Example
# Comprehensive document analysis using Code Interpreter and File Search

.PHONY: test-dry test-live run clean help

# Default target
help:
	@echo "PDF Analysis Example"
	@echo "Comprehensive document analysis using Code Interpreter and File Search"
	@echo ""
	@echo "Available targets:"
	@echo "  test-dry    - Validate templates and schemas (no API calls)"
	@echo "  test-live   - Run minimal live test with document analysis"
	@echo "  run         - Execute comprehensive document analysis"
	@echo "  clean       - Remove generated files"
	@echo "  help        - Show this help message"
	@echo ""
	@echo "Usage:"
	@echo "  make run"
	@echo "  make test-live"
	@echo ""
	@echo "For custom analysis types, use ostruct directly:"
	@echo "  ostruct run templates/main.j2 schemas/main.json -V analysis_type=detailed --file ci:documents data/ --enable-tool code-interpreter"
	@echo ""
	@echo "Features:"
	@echo "  - Multi-tool integration (Code Interpreter + File Search)"
	@echo "  - Document quality assessment"
	@echo "  - Content extraction and analysis"
	@echo "  - Actionable recommendations"

# Configuration
MODEL ?= gpt-4o-mini

test-dry:
	./run.sh --test-dry-run

test-live:
	./run.sh --test-live

run:
	./run.sh

clean:
	@echo "🧹 Cleaning up generated files..."
	rm -f *.json *.log *.pdf *.txt
	rm -rf downloads/ output/
	@echo "✅ Cleanup completed"
