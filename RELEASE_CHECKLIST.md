# Release Readiness Checklist for ostruct

This checklist covers validation steps **after** you decide a version is ready.

For **branching and tagging rules** (what to do *before* you start coding, how to tag, how to hot-fix) see the full guide: `docs › contribute › release_workflow`_

.. _docs › contribute › release_workflow: <https://ostruct.readthedocs.io/en/latest/contribute/release_workflow.html>

## 🏷️ Dynamic Versioning & Release Process

**IMPORTANT**: This project uses `poetry-dynamic-versioning` - versions are determined by Git tags, NOT by `pyproject.toml`.

### Version Management

- ✅ **DO**: Create Git tags to set versions (`git tag v1.0.0-rc13`)
- ❌ **DON'T**: Run `poetry version X.Y.Z` (this will be ignored)
- ✅ **Verification**: Run `poetry run python -c "import ostruct; print(ostruct.__version__)"` to see current version

### Release Candidate (RC) Process

1. **Create RC tag:**

   ```bash
   git tag v1.0.0-rc13
   git push origin v1.0.0-rc13
   ```

2. **CI automatically handles:**
   - ✅ Building the package from the tagged commit
   - ✅ Publishing to TestPyPI (RC tags only)
   - ✅ Creating GitHub release with binaries

3. **Test RC from TestPyPI:**

   ```bash
   # IMPORTANT: Always pin exact RC version when final release exists
   pipx install --index-url https://test.pypi.org/simple/ \
     --pip-args "--extra-index-url https://pypi.org/simple/" \
     "ostruct-cli==1.0.0rc13"

   # NOTE: --pre flag alone is insufficient if final version exists
   # (pip prefers 1.0.0 over 1.0.0rc13 even with --pre due to PEP 440)
   ```

4. **Verify RC works:**

   ```bash
   ostruct --help          # Should work without errors
   ostruct run --help      # Test CLI functionality
   ```

### Final Release Process

1. **Create final tag:**

   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```

2. **CI automatically publishes to PyPI** (final releases only)

### Common Pitfalls to Avoid

- 🚫 **Don't manually edit version in pyproject.toml** - it's ignored due to dynamic versioning
- 🚫 **Don't manually publish to TestPyPI** - CI handles this automatically for RC tags
- 🚫 **Don't rely on --pre flag alone** - when final release exists, always pin exact RC version (PEP 440: `1.0.0 > 1.0.0rc13`)
- 🚫 **Don't assume TestPyPI install worked** - always test `ostruct --help` to verify correct version installed

## Pre-Release Testing Strategy

### 1. Automated Validation (REQUIRED)

Run the automated validation script:

```bash
# Full validation with clean installation tests
python scripts/build/validate-release.py

# Quick validation (skip slow clean install tests)
python scripts/build/validate-release.py --skip-clean-install
```

This script performs:

- ✅ Version consistency checks
- ✅ pyproject.toml validation
- ✅ Package building (wheel + sdist)
- ✅ Dependency resolution testing
- ✅ Test suite execution
- ✅ Documentation building
- ✅ Clean virtual environment installation testing

You can also run individual commands manually:

```bash
# Run tests and pre-commit hooks
poetry run pytest -m "not live" -v
poetry run pre-commit run --all-files
```

### 2. Manual Local Testing (RECOMMENDED)

#### Test in Fresh Virtual Environments

Create temporary virtual environments and test installation:

```bash
# Test Python 3.10
python3.10 -m venv test_env_310
source test_env_310/bin/activate
pip install dist/ostruct_cli-*.whl
ostruct --help
deactivate

# Test Python 3.11
python3.11 -m venv test_env_311
source test_env_311/bin/activate
pip install dist/ostruct_cli-*.whl
ostruct --help
deactivate

# Test Python 3.12
python3.12 -m venv test_env_312
source test_env_312/bin/activate
pip install dist/ostruct_cli-*.whl
ostruct --help
deactivate
```

This tests:

- Installation from built wheel across Python versions
- CLI functionality in clean environments
- Basic functionality works

### 3. Docker-based Clean Environment Testing (OPTIONAL but RECOMMENDED)

Create a simple Dockerfile to test installation in completely clean environments:

```dockerfile
FROM python:3.11-slim
COPY dist/ /tmp/dist/
RUN pip install /tmp/dist/*.whl
RUN ostruct --help
```

This provides the most realistic simulation of a clean laptop installation.

### 4. Test Installation from PyPI Test Server (BEFORE FINAL RELEASE)

**Note**: For RC releases, TestPyPI publishing is automated by CI when you push an RC tag.

1. **For RC testing** (automated upload via CI):

   ```bash
   # ALWAYS pin exact RC version (required when final release exists)
   pipx install --index-url https://test.pypi.org/simple/ \
     --pip-args "--extra-index-url https://pypi.org/simple/" \
     "ostruct-cli==1.0.0rc13"

   # NOTE: --pre flag alone won't work if 1.0.0 final already exists
   # (PEP 440: final versions always preferred over pre-releases)
   ```

2. **For manual testing** (if needed):

   ```bash
   poetry config repositories.test-pypi https://test.pypi.org/legacy/
   poetry publish -r test-pypi

   # Test installation
   pip install --index-url https://test.pypi.org/simple/ \
     --extra-index-url https://pypi.org/simple/ \
     ostruct-cli==<VERSION>
   ```

### 5. Platform-Specific Testing

#### Test on Multiple Operating Systems

- [ ] macOS (your current environment)
- [ ] Ubuntu/Linux (via Docker or CI)
- [ ] Windows (via Docker or CI)

#### Test on Multiple Python Versions

- [ ] Python 3.10
- [ ] Python 3.11
- [ ] Python 3.12

## Release Validation Checklist

### Package Metadata

- [ ] **Git tag created** for version (dynamic versioning - do NOT edit pyproject.toml)
- [ ] Dependencies are correctly specified with proper version bounds
- [ ] Entry points (CLI commands) are properly configured
- [ ] Python version requirement is correct (`>=3.10,<4.0`)

### Package Building

- [ ] `poetry build` succeeds without errors
- [ ] Both wheel (.whl) and source distribution (.tar.gz) are created
- [ ] Package size is reasonable (check `dist/` directory)

### Installation Testing

- [ ] Package installs cleanly in fresh virtual environments
- [ ] All dependencies can be resolved by pip
- [ ] CLI command `ostruct --help` works after installation
- [ ] Basic functionality works (template processing with `--dry-run`)

### Code Quality

- [ ] All tests pass (`poetry run pytest -m "not live"`)
- [ ] Pre-commit hooks pass (`poetry run pre-commit run --all-files`)
- [ ] Type checking passes (`poetry run mypy --package ostruct`)
- [ ] Documentation builds without errors

### Documentation

- [ ] README contains up-to-date installation instructions
- [ ] Documentation builds successfully (`cd docs && poetry run sphinx-build -W source build/html`)
- [ ] All links in documentation work

## GitHub Actions CI Validation

Ensure your GitHub Actions CI is passing:

- [ ] Tests pass on all supported Python versions
- [ ] Tests pass on all supported operating systems
- [ ] Documentation builds successfully
- [ ] Pre-commit hooks pass

## Final Steps Before Release

1. **Run comprehensive validation:**

   ```bash
   python scripts/build/validate-release.py
   ```

2. **Verify CI is green** on the main branch

3. **Test installation on a completely clean system** (if possible)

4. **Update CHANGELOG.md** with version changes

5. **Create git tag** (triggers automated CI release):

   ```bash
   git tag v<VERSION>
   git push origin v<VERSION>
   ```

6. **CI automatically publishes to PyPI** (no manual action needed)

## Post-Release Verification

After publishing to PyPI:

1. **Test installation from PyPI:**

   ```bash
   pip install ostruct-cli==<VERSION>
   ostruct --help
   ```

2. **Test in fresh environment:**

   ```bash
   python -m venv test_env
   source test_env/bin/activate  # or test_env\Scripts\activate on Windows
   pip install ostruct-cli==<VERSION>
   ostruct --help
   deactivate
   ```

## Troubleshooting

### Common Issues and Solutions

1. **Dependency conflicts:**
   - Check `poetry.lock` is up to date
   - Verify version bounds in `pyproject.toml`
   - Test with `pip-tools` or `pipdeptree`

2. **Missing files in package:**
   - Check `MANIFEST.in` includes necessary files
   - Verify `include` directives in `pyproject.toml`

3. **CLI not working after installation:**
   - Verify entry points in `pyproject.toml`
   - Check module import paths

4. **Platform-specific issues:**
   - Test on target platforms using Docker
   - Check for platform-specific dependencies

## Confidence Level

After completing all checks:

- ✅ **HIGH CONFIDENCE**: All automated and manual tests pass
- ⚠️ **MEDIUM CONFIDENCE**: Most tests pass, minor issues documented
- ❌ **LOW CONFIDENCE**: Significant issues found, DO NOT RELEASE

---

**Remember:** It's better to delay a release and fix issues than to publish a broken package that frustrates users!
