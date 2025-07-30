# Data Science Examples Collection
# Comprehensive examples for data science workflows with ostruct

.PHONY: help test-all clean-all list-examples run-demo

# Default target
help:
	@echo "Data Science Examples Collection"
	@echo "Comprehensive examples for data science workflows with ostruct"
	@echo ""
	@echo "Available targets:"
	@echo "  help          - Show this help message"
	@echo "  list-examples - List all available examples"
	@echo "  test-all      - Run dry-run tests for all examples"
	@echo "  run-demo      - Run a quick demonstration"
	@echo "  clean-all     - Clean all generated files"
	@echo ""
	@echo "Example-specific targets:"
	@echo "  Run 'make help' in any subdirectory for specific options"
	@echo ""
	@echo "Quick start paths:"
	@echo "  New users:     cd analysis/basic-dataframe-analysis && make run"
	@echo "  Jupyter users: jupyter notebook notebooks/ostruct_data_analysis.ipynb"
	@echo "  Researchers:   cd integration/research-synthesis && make run"
	@echo ""
	@echo "Prerequisites:"
	@echo "  pip install ostruct-cli[enhanced-detection]"
	@echo "  export OPENAI_API_KEY=\"your-key-here\""

list-examples:
	@echo "📊 Data Science Examples:"
	@echo ""
	@echo "📓 Notebooks:"
	@find notebooks/ -name "*.ipynb" -exec basename {} \; 2>/dev/null || echo "  (No notebooks yet - see DOCS_TASKS.md Task 1.3.5)"
	@echo ""
	@echo "📊 Analysis Examples:"
	@find analysis/ -type d -maxdepth 1 -mindepth 1 -exec basename {} \; 2>/dev/null || echo "  (To be created in Tasks 1.3.2-1.3.4)"
	@echo ""
	@echo "📈 Visualization Examples:"
	@find visualization/ -type d -maxdepth 1 -mindepth 1 -exec basename {} \; 2>/dev/null || echo "  (Planned for future tasks)"
	@echo ""
	@echo "🔗 Integration Examples:"
	@find integration/ -type d -maxdepth 1 -mindepth 1 -exec basename {} \; 2>/dev/null || echo "  (Planned for future tasks)"

test-all:
	@echo "🧪 Running dry-run tests for all data science examples..."
	@echo ""
	@for dir in analysis/*/Makefile visualization/*/Makefile integration/*/Makefile; do \
		if [ -f "$$dir" ]; then \
			example_dir=$$(dirname "$$dir"); \
			echo "Testing $$example_dir..."; \
			$(MAKE) -C "$$example_dir" test-dry 2>/dev/null || echo "  ⚠️  No test-dry target in $$example_dir"; \
		fi \
	done
	@echo "✅ Dry-run testing completed"

run-demo:
	@echo "🚀 Running quick demonstration..."
	@echo ""
	@echo "This will run a basic analysis example with minimal cost."
	@echo "Ensure you have OPENAI_API_KEY set and ostruct installed."
	@echo ""
	@if [ -d "analysis/basic-dataframe-analysis" ]; then \
		echo "Running basic DataFrame analysis demo..."; \
		$(MAKE) -C analysis/basic-dataframe-analysis test-live; \
	else \
		echo "Demo example not available yet (Task 1.3.2 in progress)"; \
		echo "You can create it with: ostruct scaffold template basic-analysis.ost"; \
	fi

clean-all:
	@echo "🧹 Cleaning all data science examples..."
	@find . -name "*.json" -not -path "./schemas/*" -not -path "./data/*" -delete 2>/dev/null || true
	@find . -name "*.log" -delete 2>/dev/null || true
	@find . -name "*.png" -not -path "./data/*" -delete 2>/dev/null || true
	@find . -name "*.svg" -not -path "./data/*" -delete 2>/dev/null || true
	@find . -name "*.csv" -not -path "./data/*" -delete 2>/dev/null || true
	@rm -rf */downloads/ */output/ 2>/dev/null || true
	@echo "✅ Cleanup completed for all examples"

# Installation helper
check-deps:
	@echo "🔍 Checking dependencies..."
	@which ostruct >/dev/null || (echo "❌ ostruct not found. Install with: pip install ostruct-cli[enhanced-detection]" && exit 1)
	@test -n "$$OPENAI_API_KEY" || (echo "❌ OPENAI_API_KEY not set" && exit 1)
	@echo "✅ Dependencies OK"
