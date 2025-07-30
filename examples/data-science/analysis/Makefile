# Code Interpreter Basics Example
# Demonstrates basic code interpreter functionality with CSV analysis and visualization

.PHONY: test-dry test-live run clean help

# Default target
help:
	@echo "Code Interpreter Basics Example"
	@echo "Demonstrates basic code interpreter functionality with CSV analysis and visualization"
	@echo ""
	@echo "Available targets:"
	@echo "  test-dry    - Validate templates and schemas (no API calls)"
	@echo "  test-live   - Run minimal live test with code interpreter"
	@echo "  run         - Execute analysis with sample CSV data"
	@echo "  clean       - Remove generated files"
	@echo "  help        - Show this help message"
	@echo ""
	@echo "Usage:"
	@echo "  make run"
	@echo "  make test-live"
	@echo ""
	@echo "For custom data files, use ostruct directly:"
	@echo "  ostruct run templates/main.j2 schemas/main.json --file ci:sales your_data.csv --enable-tool code-interpreter"
	@echo ""
	@echo "Features:"
	@echo "  - CSV data analysis and statistics"
	@echo "  - Automatic chart generation"
	@echo "  - File download capabilities"

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
	rm -f *.json *.log *.png *.csv
	rm -rf downloads/ output/
	@echo "✅ Cleanup completed"
