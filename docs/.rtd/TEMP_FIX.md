# Temporary Read the Docs Configuration

## Added: 2025-01-29

### Current Setup

- Direct pip installation of required packages:
  - `sphinx-rtd-theme`
  - `myst-parser`
- Workaround for Poetry-RTD integration
- Using explicit pip installs after Poetry setup

### Technical Details

1. Current `.readthedocs.yaml` configuration:

   ```yaml
   post_install:
     - poetry install --with docs
     - pip install sphinx-rtd-theme
     - pip install myst-parser
   ```

2. Why this approach:
   - Ensures immediate documentation availability for first release
   - Simple, reliable solution that works
   - Avoids complex Poetry-RTD integration issues initially

### Remove When

1. Poetry installs docs dependencies correctly in RTD environment
2. Builds pass without explicit pip installs
3. A proper investigation of Poetry-RTD integration is completed

### Next Steps

1. Create GitHub issue to track proper integration
2. Investigate Poetry package installation in Read the Docs:
   - Enable verbose Poetry logs
   - Check Python paths
   - Test virtualenv configurations
3. Document findings and implement permanent solution

### References

- Issue tracking this fix: #1
- Read the Docs build logs showing successful build
- Poetry documentation on dependency groups
