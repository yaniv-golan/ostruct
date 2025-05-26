# Configuration Validation & Analysis

This use case demonstrates how to validate and analyze configuration files (JSON, YAML) across multiple environments and projects using ostruct CLI with both traditional and enhanced multi-tool capabilities. It goes beyond traditional schema validation by understanding semantic relationships between configs, suggesting improvements, and providing intelligent feedback.

## Problem This Solves

Configuration files are often complex, environment-specific, and prone to subtle errors that can cause production failures. This validation system goes beyond simple schema checking to understand semantic relationships, detect security issues, and provide intelligent recommendations. It helps ensure configuration consistency across environments and catches issues before deployment.

## Features

### Core Validation
- Multi-file configuration validation
- Cross-environment consistency checking
- Semantic understanding of config values
- Security and best practice recommendations
- Intelligent error messages and fix suggestions
- Support for JSON and YAML formats

### Enhanced Multi-Tool Integration
- **File Search**: Search documentation for configuration best practices
- **Code Interpreter**: Validate configuration logic and dependencies
- **MCP Servers**: Connect to external services for additional context
- **Explicit File Routing**: Optimize processing through targeted file routing

## Directory Structure

```
.
├── README.md           # This file
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

### Traditional Usage (Unchanged)

These commands work exactly as before:

1. **Basic Usage**:

   Generic pattern:

   ```bash
   ostruct run prompts/task.j2 schemas/validation_result.json \
     -d configs path/to/your/configs \
     -R \
     --sys-file prompts/system.txt \
     -V service_name=my-service \
     -V environment=dev \
     -V cross_env_check=false \
     -V strict_mode=false \
     -V ignore_patterns='[]'
   ```

   Ready to run example:

   ```bash
   ostruct run prompts/task.j2 schemas/validation_result.json \
     -d configs examples/basic \
     -R \
     --sys-file prompts/system.txt \
     -V service_name=basic-app \
     -V environment=dev \
     -V cross_env_check=false \
     -V strict_mode=false \
     -V ignore_patterns='[]'
   ```

2. **Environment-Specific Validation**:

   Generic pattern:

   ```bash
   ostruct run prompts/task.j2 schemas/validation_result.json \
     -d configs path/to/your/configs \
     -R \
     --sys-file prompts/system.txt \
     -V service_name=my-service \
     -V environment=prod \
     -V cross_env_check=true \
     -V strict_mode=false \
     -V ignore_patterns='[]'
   ```

   Ready to run example:

   ```bash
   ostruct run prompts/task.j2 schemas/validation_result.json \
     -d configs examples/intermediate \
     -R \
     --sys-file prompts/system.txt \
     -V service_name=multi-service \
     -V environment=prod \
     -V cross_env_check=true \
     -V strict_mode=false \
     -V ignore_patterns='[]'
   ```

3. **Strict Mode with Custom Ignore Patterns**:

   Generic pattern:

   ```bash
   ostruct run prompts/task.j2 schemas/validation_result.json \
     -d configs path/to/your/configs \
     -R \
     --sys-file prompts/system.txt \
     -V service_name=my-service \
     -V environment=dev \
     -V cross_env_check=false \
     -V strict_mode=true \
     -V ignore_patterns='["*.local.yaml", "test/*.yaml"]'
   ```

   Ready to run example:

   ```bash
   ostruct run prompts/task.j2 schemas/validation_result.json \
     -d configs examples/advanced/services \
     -R \
     --sys-file prompts/system.txt \
     -V service_name=microservices \
     -V environment=dev \
     -V cross_env_check=false \
     -V strict_mode=true \
     -V ignore_patterns='["*.local.yaml", "test/*.yaml"]'
   ```

4. **Output to File**:

   Generic pattern:

   ```bash
   ostruct run prompts/task.j2 schemas/validation_result.json \
     -d configs path/to/your/configs \
     -R \
     --sys-file prompts/system.txt \
     -V service_name=my-service \
     --output-file validation_results.json
   ```

   Ready to run example:

   ```bash
   ostruct run prompts/task.j2 schemas/validation_result.json \
     -d configs examples/basic \
     -R \
     --sys-file prompts/system.txt \
     -V service_name=basic-app \
     --output-file basic_validation.json
   ```

### Enhanced Multi-Tool Usage

#### Configuration Analysis with Documentation Context
Upload configuration files for analysis while searching documentation for best practices:

```bash
# Configuration analysis with documentation search
ostruct run prompts/task.j2 schemas/validation_result.json \
  -ft examples/basic/dev.yaml \
  -ft examples/basic/prod.yaml \
  -fs docs/ \
  --sys-file prompts/system.txt \
  -V service_name=basic-app \
  -V cross_env_check=true

# Multi-environment validation with explicit routing
ostruct run prompts/task.j2 schemas/validation_result.json \
  -ft examples/intermediate/ \
  -fs infrastructure_docs/ \
  --sys-file prompts/system.txt \
  -V environment=all \
  --output-file multi_env_validation.json
```

#### Code Interpreter for Logic Validation
Use Code Interpreter to validate configuration logic and dependencies:

```bash
# Configuration with dependency validation
ostruct run prompts/task.j2 schemas/validation_result.json \
  -fc examples/advanced/services/ \
  -ft examples/advanced/shared/ \
  --sys-file prompts/system.txt \
  -V service_name=microservices \
  -V strict_mode=true

# Complex configuration analysis
ostruct run prompts/task.j2 schemas/validation_result.json \
  -fc config_templates/ \
  -fc validation_scripts/ \
  -fs documentation/ \
  --sys-file prompts/system.txt \
  --output-file comprehensive_validation.json
```

#### MCP Server Integration for Repository Context
Connect to MCP servers to access repository documentation and standards:

```bash
# Configuration validation with repository context
ostruct run prompts/task.j2 schemas/validation_result.json \
  -ft examples/basic/ \
  --mcp-server deepwiki@https://mcp.deepwiki.com/sse \
  --sys-file prompts/system.txt \
  -V service_name=basic-app \
  -V repo_owner=your-org \
  -V repo_name=your-repo

# Multi-tool analysis with external documentation
ostruct run prompts/task.j2 schemas/validation_result.json \
  -fc config_files/ \
  -fs local_docs/ \
  --mcp-server deepwiki@https://mcp.deepwiki.com/sse \
  --sys-file prompts/system.txt \
  --output-file enhanced_validation.json
```

#### Configuration-Driven Workflows
Use persistent configuration for consistent validation:

```bash
# Create ostruct.yaml for config validation
cat > ostruct.yaml << EOF
models:
  default: gpt-4o
tools:
  file_search:
    max_results: 20
mcp:
  deepwiki: "https://mcp.deepwiki.com/sse"
operation:
  timeout_minutes: 15
limits:
  max_cost_per_run: 3.00
EOF

# Run with configuration
ostruct --config ostruct.yaml run prompts/task.j2 schemas/validation_result.json \
  -ft config/ \
  -fs docs/
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

## Template System Prompt Sharing

The ostruct template system supports sharing system prompts between templates using the `include_system:` feature. This allows you to maintain common system prompt content in shared files while adding template-specific instructions.

### Example: Shared System Prompt

Create a shared system prompt file:

```bash
# Create shared prompt
cat > prompts/shared_base.txt << EOF
You are an expert configuration analyst with deep knowledge of:
- YAML and JSON configuration formats
- Environment-specific deployment patterns
- Security best practices for configuration management
- Cross-service dependency validation

Always provide actionable recommendations and specific examples.
EOF
```

Then reference it in your template with additional context:

```yaml
---
model: gpt-4o
include_system: shared_base.txt
system_prompt: |
  For this configuration validation task, focus specifically on:
  - Database connection security
  - Environment variable management
  - Secret handling best practices

  Pay special attention to production vs development differences.
---

# Configuration Validation Task
Analyze the provided configuration files...
```

This approach allows teams to:
- **Share expertise**: Common system prompts across multiple templates
- **Maintain consistency**: Standardized instructions and tone
- **Add specificity**: Template-specific guidance while inheriting shared knowledge
- **Simplify maintenance**: Update shared prompts in one place

## Limitations

- Very large config files (>100KB) are processed in chunks
- Binary configuration formats not supported
- Some complex templating systems may need preprocessing
