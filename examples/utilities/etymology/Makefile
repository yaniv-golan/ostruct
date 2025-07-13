# Etymology Analysis Example
# Demonstrates etymological analysis of words with detailed breakdown

.PHONY: test-dry test-live run clean help

# Default target
help:
	@echo "Etymology Analysis Example"
	@echo "Demonstrates etymological analysis of words with detailed breakdown"
	@echo ""
	@echo "Available targets:"
	@echo "  test-dry    - Validate templates and schemas (no API calls)"
	@echo "  test-live   - Run minimal live test with etymology analysis"
	@echo "  run         - Execute analysis with default word (automobile)"
	@echo "  clean       - Remove generated files"
	@echo "  help        - Show this help message"
	@echo ""
	@echo "Usage:"
	@echo "  make run"
	@echo "  make test-live"
	@echo ""
	@echo "For custom words, use ostruct directly:"
	@echo "  ostruct run templates/main.j2 schemas/main.json -V word=pneumonoultramicroscopicsilicovolcanoconiosis --sys-file templates/system.txt"
	@echo ""
	@echo "Features:"
	@echo "  - Component-by-component word analysis"
	@echo "  - Origin language identification"
	@echo "  - Hierarchical relationship mapping"

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
