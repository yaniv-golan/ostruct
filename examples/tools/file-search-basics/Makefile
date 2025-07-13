# File Search Basics Example
# Demonstrates basic file search functionality with document Q&A

.PHONY: test-dry test-live run clean help

# Default target
help:
	@echo "File Search Basics Example"
	@echo "Demonstrates basic file search functionality with document Q&A"
	@echo ""
	@echo "Available targets:"
	@echo "  test-dry    - Validate templates and schemas (no API calls)"
	@echo "  test-live   - Run minimal live test with file search"
	@echo "  run         - Execute file search with company documents"
	@echo "  clean       - Remove generated files"
	@echo "  help        - Show this help message"
	@echo ""
	@echo "Usage:"
	@echo "  make run"
	@echo "  make test-live"
	@echo ""
	@echo "For custom files, use ostruct directly:"
	@echo "  ostruct run templates/main.j2 schemas/main.json --file fs:policies your_files/ --enable-tool file-search"
	@echo ""
	@echo "Features:"
	@echo "  - Upload multiple documents for search"
	@echo "  - Answer questions with citations"
	@echo "  - Demonstrate file search tool integration"

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
	rm -f *.json *.log
	@echo "✅ Cleanup completed"
