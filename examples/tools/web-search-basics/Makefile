# Web Search Basics Example
# Demonstrates basic web search functionality with current information retrieval

.PHONY: test-dry test-live run clean help

# Default target
help:
	@echo "Web Search Basics Example"
	@echo "Demonstrates basic web search functionality with current information retrieval"
	@echo ""
	@echo "Available targets:"
	@echo "  test-dry    - Validate templates and schemas (no API calls)"
	@echo "  test-live   - Run minimal live test with web search"
	@echo "  run         - Execute web search with default topic (AI developments)"
	@echo "  clean       - Remove generated files"
	@echo "  help        - Show this help message"
	@echo ""
	@echo "Usage:"
	@echo "  make run"
	@echo "  make test-live"
	@echo ""
	@echo "For custom topics, use ostruct directly:"
	@echo "  ostruct run templates/main.j2 schemas/main.json -V question='your research topic' --enable-tool web-search"

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
