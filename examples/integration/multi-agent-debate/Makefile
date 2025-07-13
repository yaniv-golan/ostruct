# Multi-Agent Debate Example
# Sophisticated multi-agent debate system with web search integration

.PHONY: test-dry test-live run clean help

# Default target
help:
	@echo "Multi-Agent Debate Example"
	@echo "Sophisticated multi-agent debate system with web search integration"
	@echo ""
	@echo "Available targets:"
	@echo "  test-dry    - Validate templates and schemas (no API calls)"
	@echo "  test-live   - Run minimal live test with debate"
	@echo "  run         - Execute debate with default topic (AI safety regulations, 2 rounds)"
	@echo "  clean       - Remove generated files"
	@echo "  help        - Show this help message"
	@echo ""
	@echo "Usage:"
	@echo "  make run"
	@echo "  make test-live"
	@echo ""
	@echo "For custom parameters, use run_debate.sh directly:"
	@echo "  ./run_debate.sh 5 'Universal basic income should be implemented'"
	@echo ""
	@echo "Features:"
	@echo "  - Multi-round debate between AI agents"
	@echo "  - Web search integration for current information"
	@echo "  - Automatic transcript generation"
	@echo "  - HTML and Mermaid visualization output"

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
	rm -f *.json *.log *.html *.svg *.mmd
	rm -rf output/
	@echo "✅ Cleanup completed"
