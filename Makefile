.PHONY: help build-install-script clean test test-unit test-integration test-docker test-dependencies lint format check-version

# Default target
help:
	@echo "Available targets:"
	@echo "  build-install-script  Generate install-macos.sh from template with current version"
	@echo "  clean                 Clean generated files"
	@echo "  test                  Run all tests"
	@echo "  test-unit             Run unit tests only"
	@echo "  test-integration      Run integration tests only"
	@echo "  test-docker           Run Docker tests only"
	@echo "  test-dependencies     Test dependency installation utilities"
	@echo "  lint                  Run linting"
	@echo "  format                Format code"
	@echo "  check-version         Show current version from pyproject.toml"

# Generate the installation script with current version
build-install-script:
	@echo "🔨 Building macOS installation script..."
	python3 scripts/build/build-install-script.py
	@echo "✅ Installation script built successfully"

# Clean generated files
clean:
	@echo "🧹 Cleaning generated files..."
	rm -f scripts/generated/install-macos.sh
	@echo "✅ Clean complete"

# Show current version
check-version:
	@echo "Current version:"
	@grep 'version = ' pyproject.toml | head -1

# Run all tests
test: test-unit test-integration test-dependencies

# Run unit tests
test-unit:
	@echo "🧪 Running unit tests..."
	@find scripts/test/unit -name "*.sh" -type f -exec {} \;
	@echo "✅ Unit tests complete"

# Run integration tests
test-integration:
	@echo "🔗 Running integration tests..."
	@find scripts/test/integration -name "*.sh" -type f -exec {} \;
	@echo "✅ Integration tests complete"

# Run Docker tests
test-docker:
	@echo "🐳 Running Docker tests..."
	@find scripts/test/docker -name "*.sh" -type f -exec {} \;
	@echo "✅ Docker tests complete"

# Test dependency utilities
test-dependencies:
	@echo "🔧 Testing dependency utilities..."
	@echo "Testing jq utility (dry-run)..."
	@OSTRUCT_SKIP_AUTO_INSTALL=1 scripts/install/dependencies/ensure_jq.sh || echo "jq test completed"
	@echo "Testing Mermaid utility (dry-run)..."
	@OSTRUCT_SKIP_AUTO_INSTALL=1 scripts/install/dependencies/ensure_mermaid.sh || echo "Mermaid test completed"
	@echo "✅ Dependency tests complete"

# Run Python tests
test-python:
	poetry run pytest

# Run linting
lint:
	poetry run flake8 src/ tests/
	poetry run mypy src/

# Format code
format:
	poetry run black src/ tests/
	poetry run ruff check --fix src/ tests/

# Build everything (useful for CI/CD)
build: build-install-script
	poetry build
