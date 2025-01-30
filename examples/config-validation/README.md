# Configuration Validation & Analysis

This use case demonstrates how to validate and analyze configuration files (JSON, YAML) across multiple environments and projects using the OpenAI Structured CLI. It goes beyond traditional schema validation by understanding semantic relationships between configs, suggesting improvements, and providing intelligent feedback.

## Features

- Multi-file configuration validation
- Cross-environment consistency checking
- Semantic understanding of config values
- Security and best practice recommendations
- Intelligent error messages and fix suggestions
- Support for JSON and YAML formats

## Directory Structure

```
.
├── README.md           # This file
├── run.sh             # Runner script
├── prompts/           # AI prompts
│   ├── system.txt     # AI's role and expertise
│   └── task.j2        # Validation request template
├── schemas/           # Output structure
│   └── validation_result.json
├── examples/          # Sample configurations to validate
│   ├── basic/        # Simple single-service configs
│   │   ├── dev.yaml       # Development environment
│   │   └── prod.yaml      # Production environment
│   ├── intermediate/ # Multi-service application
│   │   ├── app.yaml      # Application settings
│   │   ├── db.yaml       # Database configuration
│   │   └── cache.yaml    # Cache settings
│   └── advanced/     # Complex microservices setup
│       ├── services/     # Service-specific configs
│       └── shared/       # Shared configuration
└── docs/             # Documentation
    ├── customization.md  # How to customize
    └── schema.md        # Schema reference

```

## Usage

1. **Basic Usage**:

   ```bash
   # Validate configs in a directory
   bash run.sh path/to/config/dir
   ```

2. **With Environment**:

   ```bash
   # Validate specific environment configs
   bash run.sh --env production path/to/config/dir
   ```

3. **Cross-Environment Check**:

   ```bash
   # Compare configs across environments
   bash run.sh --cross-env-check path/to/config/dir
   ```

## Example Files

1. **Basic Configuration**
   - Simple environment configs (dev/prod)
   - Database connection settings
   - Basic application parameters

2. **Intermediate Setup**
   - Multi-service application
   - Environment-specific overrides
   - Shared configuration values

3. **Advanced Configuration**
   - Microservices architecture
   - Cross-service dependencies
   - Complex validation rules

## Integration

### GitHub Actions

```yaml
- name: Validate Configs
  run: |
    ostruct \
      --task @prompts/task.j2 \
      --schema schemas/validation_result.json \
      --system-prompt @prompts/system.txt \
      --dir configs=./configs \
      --ext yaml,yml,json \
      --recursive
```

### GitLab CI

```yaml
config_validation:
  script:
    - ostruct --task @prompts/task.j2 --schema schemas/validation_result.json --system-prompt @prompts/system.txt --dir configs=./configs
```

## Key Benefits Over Traditional Validators

1. **Semantic Understanding**
   - Understands the meaning and intent of configurations
   - Can detect logical inconsistencies even when syntax is valid

2. **Cross-File Analysis**
   - Validates relationships between different config files
   - Ensures consistency across environments

3. **Intelligent Feedback**
   - Provides human-readable explanations
   - Suggests specific fixes for issues
   - Recommends security improvements

4. **Best Practice Enforcement**
   - Identifies common anti-patterns
   - Suggests modern configuration approaches
   - Helps maintain security standards

## Prerequisites

- OpenAI Structured CLI installed
- OpenAI API key configured
- Configuration files to validate (YAML/JSON)

## Limitations

- Very large config files (>100KB) are processed in chunks
- Binary configuration formats not supported
- Some complex templating systems may need preprocessing
