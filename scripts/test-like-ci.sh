#!/bin/bash
# scripts/test-like-ci.sh
# Simulate CI environment locally to catch issues before they reach CI

set -e

echo "🔧 === Simulating CI Environment ==="

# Save current poetry config
ORIGINAL_VENV_CREATE=$(poetry config virtualenvs.create || echo "true")

# Configure Poetry like CI
echo "📦 Configuring Poetry to match CI..."
poetry config virtualenvs.create false

# Ensure dependencies are installed
echo "📥 Installing dependencies like CI..."
poetry install --no-interaction --with dev --extras "docs examples"

echo "🔍 === Environment Version Report ==="
echo "Python: $(python --version)"
echo "Poetry: $(poetry --version)"
echo "MyPy: $(poetry run mypy --version)"
echo "Black: $(poetry run black --version)"
echo "Ruff: $(poetry run ruff --version)"
echo "Pre-commit: $(poetry run pre-commit --version)"
echo "Pytest: $(poetry run pytest --version)"
echo "================================="

echo "🧹 === Running pre-commit checks ==="
poetry run pre-commit run --all-files

echo "🔬 === Running type checking with MyPy ==="
poetry run mypy --package ostruct

echo "🧪 === Running tests with CI flags ==="
# Run all tests except live tests, with verbose output and logging
poetry run pytest -m "not live" -vv -s --log-cli-level=DEBUG

echo "🎯 === Testing specific failing modules ==="
poetry run pytest tests/cli/test_files_commands.py tests/cli/test_files_upload.py tests/test_responses_api.py tests/test_template_rendering.py -v

echo "🚀 === Testing CLI help and basic commands ==="
# Test that basic CLI commands work
poetry run ostruct --help > /dev/null
poetry run ostruct --version || echo "Version command may not be implemented"

# Test dry-run functionality
echo '{"type": "object", "properties": {"message": {"type": "string"}}, "required": ["message"]}' > /tmp/test_schema.json
echo 'Test: {{ "hello" }}' > /tmp/test_template.j2
poetry run ostruct run /tmp/test_template.j2 /tmp/test_schema.json --dry-run
rm -f /tmp/test_schema.json /tmp/test_template.j2

echo "📚 === Building docs (HTML+linkcheck) ==="
cd docs
echo "Building documentation with warnings treated as errors..."
poetry run sphinx-build -W -b html source build/html
echo "Checking for broken links..."
poetry run sphinx-build -b linkcheck source build/linkcheck
echo "Documentation build completed successfully!"
cd ..

# Restore original poetry config
echo "🔄 Restoring original Poetry configuration..."
poetry config virtualenvs.create "$ORIGINAL_VENV_CREATE"

echo "✅ === All CI simulation checks passed! ==="
echo "🎉 Your changes should pass CI successfully."
