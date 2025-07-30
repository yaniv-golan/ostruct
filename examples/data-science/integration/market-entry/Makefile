# Market Entry Analysis - Multi-Tool Integration Example
# Demonstrates ostruct with Code Interpreter + File Search + Web Search

.PHONY: test-dry test-live run clean help

# Default target
help:
	@echo "Market Entry Analysis - Multi-Tool Integration"
	@echo "Demonstrates Code Interpreter + File Search + Web Search integration"
	@echo ""
	@echo "Available targets:"
	@echo "  test-dry    - Validate templates and schemas (no API calls)"
	@echo "  test-live   - Run with minimal web search (low cost ~$0.05)"
	@echo "  run         - Full multi-tool analysis (~$0.15-0.25)"
	@echo "  run-minimal - Analysis without web search (lower cost ~$0.08)"
	@echo "  clean       - Remove generated files"
	@echo "  help        - Show this help message"
	@echo ""
	@echo "Configuration:"
	@echo "  DATA_FILE   - Financial data file (default: data/financial_projections.csv)"
	@echo "  DOCS_DIR    - Documentation directory (default: docs/)"
	@echo "  WEB_QUERY   - Market research query (default: preset query)"
	@echo "  MODEL       - OpenAI model (default: gpt-4o)"
	@echo ""
	@echo "Examples:"
	@echo "  make run MODEL=gpt-4o-mini"
	@echo "  make run WEB_QUERY='European SaaS market analysis 2024'"
	@echo "  make run DATA_FILE=your_data.csv DOCS_DIR=your_docs/"

# Configuration
MODEL ?= gpt-4o
DATA_FILE ?= data/financial_projections.csv
DOCS_DIR ?= docs/
WEB_QUERY ?= European SaaS market entry analysis 2024 competitive landscape regulatory requirements
TEMPLATE = templates/market_entry_analysis.j2
SCHEMA = schemas/market_entry_schema.json
OUTPUT_FILE = market_entry_analysis_results.json

test-dry:
	@echo "🧪 Running dry-run validation..."
	ostruct run $(TEMPLATE) $(SCHEMA) \
		--file ci:financial_data $(DATA_FILE) \
		--file fs:regulatory_docs $(DOCS_DIR) \
		--enable-tool web-search \
		--model $(MODEL) \
		--dry-run
	@echo "✅ Dry-run validation completed"

test-live:
	@echo "🚀 Running minimal live test..."
	ostruct run $(TEMPLATE) $(SCHEMA) \
		--file ci:financial_data $(DATA_FILE) \
		--enable-tool web-search \
		--model gpt-4o-mini \
		--output-file test_results.json
	@echo "✅ Live test completed - check test_results.json"

run:
	@echo "🚀 Running full multi-tool market entry analysis..."
	@echo "📊 Data Source: $(DATA_FILE)"
	@echo "📚 Documents: $(DOCS_DIR)"
	@echo "🌐 Web Query: $(WEB_QUERY)"
	@echo "🤖 Model: $(MODEL)"
	@echo ""
	ostruct run $(TEMPLATE) $(SCHEMA) \
		--file ci:financial_data $(DATA_FILE) \
		--file fs:regulatory_docs $(DOCS_DIR) \
		--enable-tool web-search \
		--model $(MODEL) \
		--output-file $(OUTPUT_FILE)
	@echo ""
	@echo "✅ Analysis completed successfully!"
	@echo "📄 Results saved to: $(OUTPUT_FILE)"
	@echo "💡 Review the strategic recommendation and implementation roadmap"

run-minimal:
	@echo "🚀 Running analysis without web search (lower cost)..."
	ostruct run $(TEMPLATE) $(SCHEMA) \
		--file ci:financial_data $(DATA_FILE) \
		--file fs:regulatory_docs $(DOCS_DIR) \
		--model $(MODEL) \
		--output-file minimal_results.json
	@echo "✅ Minimal analysis completed - check minimal_results.json"

clean:
	@echo "🧹 Cleaning up generated files..."
	rm -f *.json *.log
	rm -rf downloads/
	@echo "✅ Cleanup completed"

# Development targets
validate-schema:
	@echo "🔍 Validating schema structure..."
	python3 -c "import json; json.load(open('$(SCHEMA)'))"
	@echo "✅ Schema validation passed"

show-config:
	@echo "Current Configuration:"
	@echo "  Template: $(TEMPLATE)"
	@echo "  Schema: $(SCHEMA)"
	@echo "  Data File: $(DATA_FILE)"
	@echo "  Docs Directory: $(DOCS_DIR)"
	@echo "  Web Query: $(WEB_QUERY)"
	@echo "  Model: $(MODEL)"
	@echo "  Output File: $(OUTPUT_FILE)"

# Debug targets
debug-financial:
	@echo "🔍 Testing financial data analysis only..."
	ostruct run $(TEMPLATE) $(SCHEMA) \
		--file ci:financial_data $(DATA_FILE) \
		--model $(MODEL) \
		--dry-run

debug-docs:
	@echo "🔍 Testing document search only..."
	ostruct run $(TEMPLATE) $(SCHEMA) \
		--file fs:regulatory_docs $(DOCS_DIR) \
		--model $(MODEL) \
		--dry-run

debug-web:
	@echo "🔍 Testing web search only..."
	ostruct run $(TEMPLATE) $(SCHEMA) \
		--enable-tool web-search \
		--web-query "$(WEB_QUERY)" \
		--model $(MODEL) \
		--dry-run
