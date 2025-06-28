#!/bin/bash
set -e

echo "=== Local Environment Version Report ==="
echo "Python: $(python --version)"
echo "Poetry: $(poetry --version)"
echo "MyPy: $(poetry run mypy --version)"
echo "Black: $(poetry run black --version)"
echo "Ruff: $(poetry run ruff --version)"
echo "Pre-commit: $(poetry run pre-commit --version)"
echo "Pytest: $(poetry run pytest --version)"
echo "================================="

echo ""
echo "=== Expected Versions (from pyproject.toml) ==="
echo "MyPy: $(grep 'mypy = ' pyproject.toml | cut -d'"' -f2)"
echo "Black: $(grep 'black = ' pyproject.toml | cut -d'"' -f2)"
echo "================================="

echo ""
echo "=== Environment Health Check ==="

# Check if we're using the right mypy
MYPY_PATH=$(poetry run which mypy)
echo "MyPy path: $MYPY_PATH"

# Verify mypy works on our problematic file
echo "Testing mypy on mcp_integration.py..."
if poetry run mypy src/ostruct/cli/mcp_integration.py; then
    echo "✅ MyPy check passed"
else
    echo "❌ MyPy check failed"
    exit 1
fi

# Run pre-commit hooks
echo "Testing pre-commit hooks..."
if poetry run pre-commit run --all-files; then
    echo "✅ Pre-commit hooks passed"
else
    echo "❌ Pre-commit hooks failed"
    exit 1
fi

echo ""
echo "🎉 Environment verification completed successfully!"
