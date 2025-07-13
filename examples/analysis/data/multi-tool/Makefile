# Multi-Tool Data Analysis Example
# Comprehensive data analysis using Code Interpreter and File Search

.PHONY: test-dry test-live run clean help

# Default target
help:
	@echo "Multi-Tool Data Analysis Example"
	@echo "Comprehensive data analysis using Code Interpreter and File Search"
	@echo ""
	@echo "Available targets:"
	@echo "  test-dry    - Validate templates and schemas (no API calls)"
	@echo "  test-live   - Run minimal live test with data analysis"
	@echo "  run         - Execute comprehensive multi-tool data analysis"
	@echo "  clean       - Remove generated files"
	@echo "  help        - Show this help message"
	@echo ""
	@echo "Usage:"
	@echo "  make run"
	@echo "  make test-live"
	@echo ""
	@echo "For custom analysis types, use ostruct directly:"
	@echo "  ostruct run templates/main.j2 schemas/main.json -V analysis_type=detailed --file ci:sales_data data/sales_data.csv --enable-tool code-interpreter"
	@echo ""
	@echo "Features:"
	@echo "  - Multi-tool integration (Code Interpreter + File Search)"
	@echo "  - Sales and customer data analysis"
	@echo "  - Business context integration"
	@echo "  - Statistical analysis and visualizations"

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
