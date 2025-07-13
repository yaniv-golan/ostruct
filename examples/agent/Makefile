# Sandboxed Agent Example
# Autonomous agent system with LLM-planned task execution

.PHONY: test-dry test-live run clean help

# Default target
help:
	@echo "Sandboxed Agent Example"
	@echo "Autonomous agent system with LLM-planned task execution"
	@echo ""
	@echo "Available targets:"
	@echo "  test-dry    - Validate templates and schemas (no API calls)"
	@echo "  test-live   - Run minimal live test with agent"
	@echo "  run         - Execute agent with default task"
	@echo "  clean       - Remove generated files"
	@echo "  help        - Show this help message"
	@echo ""
	@echo "Usage:"
	@echo "  make run"
	@echo "  make test-live"
	@echo ""
	@echo "For custom parameters, use runner.sh directly:"
	@echo "  ./runner.sh --num-plans 5 'Create a complex application'"
	@echo ""
	@echo "Features:"
	@echo "  - Autonomous task planning and execution"
	@echo "  - Sandboxed environment for safe execution"
	@echo "  - Multi-tool integration (jq, grep, sed, awk, curl, etc.)"
	@echo "  - State management and replanning"
	@echo "  - Critic system for step validation"

# Configuration
MODEL ?= gpt-4o

test-dry:
	@echo "🧪 Validating agent templates and schemas..."
	@echo "Running dry-run validation..."
	./runner.sh --dry-run "Create a file named hello.txt with the content 'Hello, World!'"

test-live:
	@echo "🤖 Running minimal live agent test..."
	./runner.sh "Create a simple test file"

run:
	@echo "🚀 Running sandboxed agent with default task..."
	./runner.sh "Create a file named hello.txt with the content 'Hello, World!'"

clean:
	@echo "🧹 Cleaning up generated files..."
	rm -f *.json *.log repomix-output.txt
	rm -rf workdir/sandbox_* logs/run_*.log sandbox_test/ benchmark_results/ test_results/
	@echo "✅ Cleanup completed"
