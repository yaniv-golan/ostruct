# Pitch Distiller Example
# Two-pass pitch deck analysis with core extraction and taxonomy classification

.PHONY: test-dry test-live run clean help

# Default target
help:
	@echo "Pitch Distiller Example"
	@echo "Two-pass pitch deck analysis with core extraction and taxonomy classification"
	@echo ""
	@echo "Available targets:"
	@echo "  test-dry    - Validate templates and schemas (no API calls)"
	@echo "  test-live   - Run minimal live test with pitch analysis"
	@echo "  run         - Execute two-pass analysis with default deck (Airbnb 2009)"
	@echo "  clean       - Remove generated files"
	@echo "  help        - Show this help message"
	@echo ""
	@echo "Usage:"
	@echo "  make run"
	@echo "  make test-live"
	@echo ""
	@echo "For custom decks, use ostruct directly with two-pass workflow"
	@echo ""
	@echo "Features:"
	@echo "  - Two-pass workflow: core extraction + taxonomy classification"
	@echo "  - PDF vision model support (user-data routing)"
	@echo "  - File search integration for taxonomy reference"
	@echo "  - Automatic result merging"

# Configuration
MODEL ?= gpt-4o
TMP_DIR := $(shell mktemp -d)

test-dry:
	./run.sh --test-dry-run

test-live:
	./run.sh --test-live

run:
	./run.sh

clean:
	@echo "🧹 Cleaning up generated files..."
	rm -f *.json *.log
	rm -rf downloads/ output/
	@echo "✅ Cleanup completed"
